"""
Google Sheets 접근 코어 — Streamlit 에 의존하지 않는 순수 로직.

Streamlit 앱(`issue_store.py`)과 스케줄러용 CLI(`purge_job.py`)가 모두
이 모듈을 사용합니다. 여기에 streamlit 을 import 하면 cron/서비스 환경에서
불필요한 런타임 경고와 의존성이 생기므로 절대 넣지 마세요.

인증 우선순위:
    1) config.SERVICE_ACCOUNT_FILE 경로의 JSON 키 파일
    2) 환경변수 GOOGLE_SERVICE_ACCOUNT_JSON (JSON 문자열 통째로 — CI/서버용)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsUnavailable(RuntimeError):
    """자격증명·시트 ID 누락 등으로 시트에 접근할 수 없을 때."""


# ---------------------------------------------------------------------------
# 연결
# ---------------------------------------------------------------------------


def load_credentials():
    """서비스 계정 자격증명을 반환. 없으면 None."""
    from google.oauth2.service_account import Credentials

    path = config.SERVICE_ACCOUNT_FILE
    if path and os.path.exists(path):
        return Credentials.from_service_account_file(path, scopes=SCOPES)

    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        return Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)

    return None


def open_worksheet(credentials=None, sheet_id: str | None = None):
    """현안 워크시트를 반환. 없으면 만들고 헤더를 채운다.

    실패 시 SheetsUnavailable 을 발생시킵니다.
    """
    import gspread

    credentials = credentials or load_credentials()
    if credentials is None:
        raise SheetsUnavailable(
            f"서비스 계정 키를 찾을 수 없습니다 (`{config.SERVICE_ACCOUNT_FILE}` "
            "또는 GOOGLE_SERVICE_ACCOUNT_JSON)."
        )

    sheet_id = sheet_id or config.SHEET_ID
    if not sheet_id:
        raise SheetsUnavailable("ISSUE_SHEET_ID 가 설정되지 않았습니다.")

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet(config.WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=config.WORKSHEET_NAME, rows=1000, cols=len(config.HEADER)
        )
        worksheet.append_row(config.HEADER)
        return worksheet

    if not worksheet.row_values(1):
        worksheet.update("A1", [config.HEADER])
    return worksheet


# ---------------------------------------------------------------------------
# 읽기 / 쓰기
# ---------------------------------------------------------------------------


def fetch_records(worksheet) -> list[dict]:
    """헤더를 제외한 전체 행을 dict 리스트로 반환."""
    values = worksheet.get_all_values()
    if len(values) < 2:
        return []

    records = []
    for row in values[1:]:
        if not any(cell.strip() for cell in row):
            continue
        padded = list(row) + [""] * (len(config.HEADER) - len(row))
        records.append(dict(zip(config.HEADER, padded)))
    return records


def append_issue(worksheet, division: str, team: str, author: str, content: str) -> str:
    """현안 한 건을 현재 시각과 함께 추가. 저장된 작성일시 문자열을 반환."""
    now = datetime.now()
    timestamp = now.strftime(config.TIMESTAMP_FORMAT)
    worksheet.append_row(
        [timestamp, now.strftime(config.DATE_FORMAT), division, team, author, content],
        value_input_option="USER_ENTERED",
    )
    return timestamp


# ---------------------------------------------------------------------------
# 보관 정책
# ---------------------------------------------------------------------------


def parse_timestamp(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in (config.TIMESTAMP_FORMAT, "%Y-%m-%d %H:%M", config.DATE_FORMAT):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def contiguous_ranges(rows: list[int]) -> list[tuple[int, int]]:
    """정렬된 행 번호 목록을 (start, end) 연속 구간으로 묶는다."""
    ranges: list[tuple[int, int]] = []
    for row in sorted(rows):
        if ranges and row == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], row)
        else:
            ranges.append((row, row))
    return ranges


def find_expired_rows(values: list[list[str]], cutoff: datetime) -> list[int]:
    """헤더 포함 전체 값에서 만료된 행의 시트 행 번호(1-base)를 반환.

    작성일시를 해석할 수 없는 행은 데이터 보호를 위해 대상에서 제외합니다.
    """
    expired: list[int] = []
    for idx, row in enumerate(values[1:], start=2):  # 1행은 헤더
        if not any(cell.strip() for cell in row):
            continue
        written_at = parse_timestamp(row[0] if row else "")
        if written_at is not None and written_at < cutoff:
            expired.append(idx)
    return expired


def purge_expired(worksheet, retention_hours: int | None = None, dry_run: bool = False) -> int:
    """보관 기한이 지난 행을 삭제하고 삭제된 행 수를 반환."""
    hours = config.RETENTION_HOURS if retention_hours is None else retention_hours
    cutoff = datetime.now() - timedelta(hours=hours)

    values = worksheet.get_all_values()
    if len(values) < 2:
        return 0

    expired = find_expired_rows(values, cutoff)
    if not expired or dry_run:
        return len(expired)

    # 아래에서 위로 삭제해야 남은 행 번호가 밀리지 않는다.
    for start, end in sorted(contiguous_ranges(expired), reverse=True):
        worksheet.delete_rows(start, end)
    return len(expired)
