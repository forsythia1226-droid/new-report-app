"""
Streamlit 앱이 사용하는 저장소 레이어.

실제 로직은 두 백엔드에 위임합니다:
    - 운영: `sheets_core` (Google Sheets)
    - 시연: `demo_store` (로컬 JSON) — config.DEMO_MODE = True 일 때

이 모듈이 담당하는 것은 백엔드 선택과 Streamlit 캐싱뿐입니다.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

import config
import demo_store
import sheets_core


# ---------------------------------------------------------------------------
# 연결
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def _worksheet():
    """워크시트 핸들을 반환. 실패 시 None.

    `cache_resource` 로 커넥션을 재사용합니다 — rerun 마다 재인증하면
    Google API 왕복이 늘어 앱이 눈에 띄게 느려집니다.
    """
    try:
        return sheets_core.open_worksheet()
    except Exception:
        return None


def _credentials_message() -> str | None:
    """자격증명/설정 문제의 사람이 읽을 메시지. 문제 없으면 None."""
    try:
        if sheets_core.load_credentials() is None:
            return (
                f"서비스 계정 키(`{config.SERVICE_ACCOUNT_FILE}`)를 찾을 수 없습니다. "
                "`.env` 의 GOOGLE_SERVICE_ACCOUNT_FILE 경로를 확인하세요."
            )
    except Exception as e:
        return f"서비스 계정 키를 읽지 못했습니다: {type(e).__name__}: {e}"

    if not config.SHEET_ID:
        return "`.env` 에 ISSUE_SHEET_ID 를 설정해 주세요."
    return None


def is_configured() -> tuple[bool, str]:
    """(사용 가능 여부, 상태 메시지)."""
    if config.DEMO_MODE:
        return True, "데모 모드 (로컬 JSON 파일 사용)"

    message = _credentials_message()
    if message:
        return False, message
    if _worksheet() is None:
        return False, (
            "Google Sheets 에 연결하지 못했습니다. 스프레드시트가 서비스 계정의 "
            "client_email 에 '편집자'로 공유되어 있는지 확인하세요."
        )
    return True, "Google Sheets 연결됨"


# ---------------------------------------------------------------------------
# 쓰기
# ---------------------------------------------------------------------------


def submit_issue(division: str, team: str, author: str, content: str) -> tuple[bool, str | None]:
    """현안 한 건을 현재 시각과 함께 저장."""
    if config.DEMO_MODE:
        demo_store.append_issue(division, team, author, content)
        load_records.clear()
        return True, None

    worksheet = _worksheet()
    if worksheet is None:
        return False, is_configured()[1]

    try:
        sheets_core.append_issue(worksheet, division, team, author, content)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

    load_records.clear()
    return True, None


# ---------------------------------------------------------------------------
# 읽기
# ---------------------------------------------------------------------------


@st.cache_data(ttl=60, show_spinner=False)
def load_records() -> list[dict]:
    """전체 현안 행을 dict 리스트로 반환.

    60초 캐시: rerun 마다 호출되므로 캐시가 없으면 클릭할 때마다 Sheets API
    왕복이 발생합니다. 제출/삭제 직후에는 `.clear()` 로 직접 비웁니다.
    """
    if config.DEMO_MODE:
        return demo_store.load_rows()

    worksheet = _worksheet()
    if worksheet is None:
        return []
    try:
        return sheets_core.fetch_records(worksheet)
    except Exception:
        return []


def load_records_by_date(date_str: str) -> list[dict]:
    """특정 날짜(YYYY-MM-DD)의 현안만 반환."""
    return [r for r in load_records() if r.get("날짜") == date_str]


# ---------------------------------------------------------------------------
# 보관 정책
# ---------------------------------------------------------------------------


def purge_expired_rows(retention_hours: int | None = None) -> tuple[int, str | None]:
    """보관 기한이 지난 행을 삭제. 반환값 (삭제 건수, 오류 메시지)."""
    if config.DEMO_MODE:
        deleted = demo_store.purge_expired(retention_hours)
        load_records.clear()
        return deleted, None

    worksheet = _worksheet()
    if worksheet is None:
        return 0, is_configured()[1]

    try:
        deleted = sheets_core.purge_expired(worksheet, retention_hours)
    except Exception as e:
        load_records.clear()
        return 0, f"{type(e).__name__}: {e}"

    load_records.clear()
    return deleted, None


@st.cache_data(ttl=600, show_spinner=False)
def _auto_purge(_bucket: str) -> int:
    """앱 로드 시 실행되는 정리.

    `_bucket` 이 같은 동안 캐시가 반환되므로 실제 삭제는 10분에 한 번만
    수행됩니다 — rerun 마다 시트를 훑으면 API 쿼터가 금방 소진됩니다.
    접속과 무관한 정시 삭제는 `purge_job.py` 를 스케줄러에 등록하세요.
    """
    deleted, _err = purge_expired_rows()
    return deleted


def run_auto_purge() -> int:
    """10분 단위 버킷으로 자동 정리를 호출."""
    now = datetime.now()
    bucket = f"{now:%Y%m%d%H}-{now.minute // 10}"
    try:
        return _auto_purge(bucket)
    except Exception:
        return 0
