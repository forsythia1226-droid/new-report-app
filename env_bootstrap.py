"""
환경변수 부트스트랩 — `config` 를 import 하기 전에 실행되어야 한다.

로컬에서는 `.env` 파일을, Streamlit Community Cloud 에서는 앱 설정의
Secrets 를 읽어 `os.environ` 에 채워 넣습니다. 덕분에 `config.py` 는
streamlit 에 의존하지 않고 `os.getenv` 만으로 동작할 수 있습니다
(스케줄러용 `purge_job.py` 가 streamlit 없이 돌아가야 하기 때문).

이미 설정된 환경변수는 덮어쓰지 않습니다 — 로컬 실행 시 터미널에서 준
값이 우선합니다.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# 문자열로 다룰 secrets 키 (dict 형태인 gcp_service_account 는 제외)
_SCALAR_KEYS = (
    "DEMO_MODE",
    "DEMO_DATA_FILE",
    "ISSUE_SHEET_ID",
    "ISSUE_WORKSHEET_NAME",
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "RETENTION_HOURS",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_MAX_TOKENS",
    "APP_TITLE",
    "ORG_FILE",
)


def bootstrap() -> None:
    load_dotenv()

    try:
        import streamlit as st

        # secrets.toml 이 아예 없으면 st.secrets 접근 자체가 예외를 던진다
        for key in _SCALAR_KEYS:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
    except Exception:
        # secrets 가 없는 환경(로컬 등)에서는 .env 만으로 충분하다
        pass
