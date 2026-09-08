"""
48시간 보관 정책 정시 삭제 잡 (스케줄러용, Streamlit 무관).

아무도 앱에 접속하지 않아도 이 스크립트가 정해진 시각에 실행되어
보관 기한이 지난 행을 삭제합니다.

사용:
    python purge_job.py                # 삭제 실행
    python purge_job.py --dry-run      # 삭제 대상만 계산 (실제 삭제 안 함)
    python purge_job.py --hours 24     # 보관 기간을 일시적으로 24시간으로
    python purge_job.py --log-file purge.log

종료 코드: 0 = 성공, 1 = 실패 (스케줄러가 실패를 감지할 수 있도록)
"""

from __future__ import annotations

import argparse
import logging
import sys

import env_bootstrap

env_bootstrap.bootstrap()  # config 를 import 하기 전에 .env 로드

import config  # noqa: E402
import sheets_core  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="48시간 경과 현안 데이터 삭제 잡")
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help=f"보관 시간 (기본값: config.RETENTION_HOURS = {config.RETENTION_HOURS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="삭제하지 않고 대상 행 수만 출력",
    )
    parser.add_argument("--log-file", default=None, help="로그를 파일에도 기록")
    return parser


def setup_logging(log_file: str | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(args.log_file)

    hours = args.hours if args.hours is not None else config.RETENTION_HOURS
    mode = "DRY-RUN" if args.dry_run else "DELETE"
    logging.info("보관 정책 잡 시작 (mode=%s, retention=%dh)", mode, hours)

    try:
        worksheet = sheets_core.open_worksheet()
    except sheets_core.SheetsUnavailable as e:
        logging.error("시트에 접근할 수 없습니다: %s", e)
        return 1
    except Exception as e:
        logging.error("시트 연결 실패: %s: %s", type(e).__name__, e)
        return 1

    try:
        count = sheets_core.purge_expired(worksheet, hours, dry_run=args.dry_run)
    except Exception as e:
        logging.error("삭제 중 오류: %s: %s", type(e).__name__, e)
        return 1

    if args.dry_run:
        logging.info("삭제 대상 %d개 행 (실제 삭제하지 않음)", count)
    else:
        logging.info("삭제 완료: %d개 행", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
