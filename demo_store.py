"""
데모 모드 백엔드 — Google Sheets 대신 로컬 JSON 파일을 사용.

배포 전 시연/기능 확인용입니다. 시트 백엔드(`sheets_core`)와 동일한
데이터 구조(config.HEADER)와 동일한 48시간 삭제 규칙을 그대로 따르므로,
데모에서 확인한 동작이 실제 배포 동작과 일치합니다.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import config
from sheets_core import parse_timestamp


def _path() -> str:
    return config.DEMO_DATA_FILE


def load_rows() -> list[dict]:
    if not os.path.exists(_path()):
        return []
    try:
        with open(_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(rows: list[dict]) -> None:
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def append_issue(division: str, team: str, author: str, content: str) -> str:
    now = datetime.now()
    timestamp = now.strftime(config.TIMESTAMP_FORMAT)
    rows = load_rows()
    rows.append(
        {
            "작성일시": timestamp,
            "날짜": now.strftime(config.DATE_FORMAT),
            "대부문": division,
            "팀명": team,
            "작성자": author,
            "일일현안내용": content,
        }
    )
    _save(rows)
    return timestamp


def purge_expired(retention_hours: int | None = None) -> int:
    """만료 행을 제거하고 삭제된 건수를 반환 (시트 백엔드와 동일 규칙)."""
    hours = config.RETENTION_HOURS if retention_hours is None else retention_hours
    cutoff = datetime.now() - timedelta(hours=hours)

    rows = load_rows()
    kept = []
    for row in rows:
        written_at = parse_timestamp(row.get("작성일시", ""))
        # 해석 불가한 행은 시트 백엔드와 마찬가지로 보존
        if written_at is not None and written_at < cutoff:
            continue
        kept.append(row)

    deleted = len(rows) - len(kept)
    if deleted:
        _save(kept)
    return deleted


def reset() -> None:
    """데모 데이터를 모두 비운다."""
    _save([])


def seed_sample_data() -> tuple[int, int]:
    """시연용 샘플 데이터를 채운다.

    반환값 (오늘 데이터 건수, 만료 예정(48시간 초과) 데이터 건수).
    만료 데이터를 일부러 섞어 두어 [수동 정리] 버튼과 자동 삭제 동작을
    바로 확인할 수 있습니다.
    """
    now = datetime.now()

    fresh = [
        (
            "에너지부문",
            "에너지영업팀",
            "김성한",
            "- 중동 A사 500MW 변전설비 입찰 제안서 제출 완료함\n"
            "- 견적 단가 3% 인하 요청 접수, 원가팀과 검토 필요함\n"
            "- 차주 화요일 고객사 실사 방문 예정임",
        ),
        (
            "에너지부문",
            "에너지설계팀",
            "박도현",
            "- B프로젝트 기본설계 도면 90% 완료함\n"
            "- 사양 변경(절연등급 상향)으로 일정 3일 지연 예상됨",
        ),
        (
            "해저부문",
            "해저시공팀",
            "이준서",
            "- 서남해 해상풍력 케이블 포설 12km 중 8km 완료함\n"
            "- 기상 악화로 3일간 작업 중단, 공정 만회 계획 수립 중임\n"
            "- 잠수 인력 2명 추가 투입 필요함",
        ),
        (
            "해저부문",
            "해저영업팀",
            "최유진",
            "- 대만 해상풍력 2단계 사업 RFI 접수함\n"
            "- 서남해 프로젝트 공정 지연 관련 발주처 설명회 요청 있었음",
        ),
        (
            "인더스트리부문",
            "인더스트리기술팀",
            "정민우",
            "- 반도체 고객사 클린룸 배전반 사양 협의 완료함\n"
            "- 신규 인증(KS C IEC) 취득 절차 착수함",
        ),
        (
            "생산/기술부문",
            "생산관리팀",
            "한지훈",
            "- 9월 1주차 생산 계획 대비 실적 96% 달성함\n"
            "- 2호기 압연설비 예방정비로 8시간 가동 중단 예정임\n"
            "- 원자재(전기동) 입고 지연으로 일부 라인 대기 발생함",
        ),
        (
            "생산/기술부문",
            "설비팀",
            "오세영",
            "- 2호기 압연설비 예방정비 일정 확정함(금주 토요일)\n"
            "- 노후 공조설비 교체 예산 승인 요청함",
        ),
        (
            "공통",
            "안전보건",
            "윤가람",
            "- 금주 무재해 유지 중임\n"
            "- 해저시공 현장 잠수 작업 안전점검 실시 예정임",
        ),
        (
            "경영부문",
            "재무팀",
            "송하늘",
            "- 3분기 자금수지 계획 대비 유동성 양호함\n"
            "- 전기동 가격 상승분 원가 반영 검토 필요함",
        ),
    ]

    expired = [
        (
            "에너지부문",
            "에너지영업팀",
            "김성한",
            "- (3일 전 데이터) 중동 A사 사전 미팅 진행함",
        ),
        (
            "해저부문",
            "해저설계팀",
            "이준서",
            "- (3일 전 데이터) 케이블 루트 설계 검토 완료함",
        ),
        (
            "경영부문",
            "인사팀",
            "송하늘",
            "- (3일 전 데이터) 하반기 채용 공고 게시함",
        ),
    ]

    rows = []
    for i, (division, team, author, content) in enumerate(fresh):
        written = now - timedelta(minutes=17 * (i + 1))
        rows.append(
            {
                "작성일시": written.strftime(config.TIMESTAMP_FORMAT),
                "날짜": written.strftime(config.DATE_FORMAT),
                "대부문": division,
                "팀명": team,
                "작성자": author,
                "일일현안내용": content,
            }
        )

    for i, (division, team, author, content) in enumerate(expired):
        written = now - timedelta(hours=config.RETENTION_HOURS + 24 + i)
        rows.append(
            {
                "작성일시": written.strftime(config.TIMESTAMP_FORMAT),
                "날짜": written.strftime(config.DATE_FORMAT),
                "대부문": division,
                "팀명": team,
                "작성자": author,
                "일일현안내용": content,
            }
        )

    _save(rows)
    return len(fresh), len(expired)
