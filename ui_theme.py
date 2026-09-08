"""
공용 UI 테마 — 뉴스 리포트 앱(`app.py`)과 동일한 톤앤매너.

흰색 카드 + 남색 좌측 패널 + 아이콘 섹션 헤더 구성을 재사용합니다.
스타일은 위젯의 `key=` 로 생성되는 클래스(`st-key-<key>`)를 노려서 적용하므로
Streamlit 내부 DOM 구조가 바뀌어도 비교적 안전합니다.
"""

import streamlit as st

ACCENT = "#2F5DF5"
NAVY = "#1E2A5A"
NAVY_DARK = "#111a3d"
SOFT_BLUE_BG = "#4361EE"


def inject_css() -> None:
    st.html(
        f"""
<style>
.block-container {{
    padding-top: 3.5rem;
    padding-bottom: 2rem;
}}

/* 상단 헤더 카드 */
div[class*="st-key-app_header"] {{
    background: #ffffff;
    border: 1px solid #e6e8f0;
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}}
.app-header-title {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {NAVY_DARK};
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
.app-header-caption {{
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 0.15rem;
}}

/* 헤더 우측 날짜 선택 — 알약 형태 배지 */
div[class*="st-key-header_date_picker"] {{
    display: flex;
    justify-content: flex-end;
}}
div[class*="st-key-header_date_picker"] [data-testid="stSelectbox"] {{
    width: auto;
    min-width: 180px;
}}
div[class*="st-key-header_date_picker"] [data-baseweb="select"] > div {{
    background: {NAVY} !important;
    border-color: {NAVY} !important;
    border-radius: 999px !important;
}}
div[class*="st-key-header_date_picker"] [data-baseweb="select"] p {{
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
}}
div[class*="st-key-header_date_picker"] [data-baseweb="select"] svg {{
    fill: #ffffff !important;
}}

/* 각 패널 상단 섹션 제목 */
.section-title {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    font-weight: 700;
    color: {NAVY_DARK};
    letter-spacing: 0.01em;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e6e8f0;
}}
.section-title .count-badge {{
    margin-left: auto;
    font-size: 0.72rem;
    font-weight: 700;
    color: {ACCENT};
    background: #eaf0ff;
    padding: 0.1rem 0.55rem;
    border-radius: 999px;
}}

/* 좌측 남색 패널 */
div[class*="st-key-org_panel"] {{
    background: {NAVY_DARK};
    border-radius: 16px;
    padding: 1.1rem 1rem;
}}
div[class*="st-key-org_panel"] .section-title {{
    color: #ffffff;
    border-bottom: 1px solid rgba(255,255,255,0.14);
}}
div[class*="st-key-org_panel"] .section-title .count-badge {{
    color: #cdd7ff;
    background: rgba(255,255,255,0.12);
}}
div[class*="st-key-org_panel"] label,
div[class*="st-key-org_panel"] .stCaption,
div[class*="st-key-org_panel"] p,
div[class*="st-key-org_panel"] summary {{
    color: #c6cad9 !important;
}}
div[class*="st-key-org_panel"] hr {{
    border-color: rgba(255,255,255,0.1);
}}
div[class*="st-key-org_panel"] [data-baseweb="select"] > div,
div[class*="st-key-org_panel"] input {{
    background: {NAVY} !important;
    border-color: rgba(255,255,255,0.16) !important;
    color: #ffffff !important;
}}
div[class*="st-key-org_panel"] [data-baseweb="select"] svg {{
    fill: #c6cad9 !important;
}}
div[class*="st-key-org_panel"] details {{
    border-color: rgba(255,255,255,0.16) !important;
    background: {NAVY} !important;
    border-radius: 10px;
}}

/* 남색 패널 안의 버튼 — 미선택은 배경에 녹아들고, 선택은 소프트 블루 */
div[class*="st-key-org_panel"] button[kind="secondary"] {{
    background: {NAVY} !important;
    border-color: rgba(255,255,255,0.16) !important;
}}
div[class*="st-key-org_panel"] button[kind="secondary"] p {{
    color: #c6cad9 !important;
    font-weight: 400 !important;
}}
div[class*="st-key-org_panel"] button[kind="secondary"]:hover {{
    background: rgba(255,255,255,0.08) !important;
}}
div[class*="st-key-org_panel"] button[kind="secondary"]:hover p {{
    color: #ffffff !important;
}}
div[class*="st-key-org_panel"] button[kind="primary"] {{
    background: {SOFT_BLUE_BG} !important;
    border-color: {SOFT_BLUE_BG} !important;
    box-shadow: none !important;
}}
div[class*="st-key-org_panel"] button[kind="primary"] p {{
    color: #ffffff !important;
    font-weight: 700 !important;
}}

/* 팀 목록 한 줄 — 라벨 왼쪽 정렬 */
div[class*="st-key-teamrow_"] button p {{
    text-align: left !important;
    width: 100%;
}}

/* 현안 카드 (가운데 열) */
div[class*="st-key-issuecard_"] {{
    background: #ffffff;
    border: 1px solid #edeff5;
    border-radius: 10px;
    padding: 0.8rem 1rem 0.6rem 1rem;
    margin-bottom: 0.55rem;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
div[class*="st-key-issuecard_"]:hover {{
    border-color: #cfd6ea;
    box-shadow: 0 2px 10px rgba(16, 24, 40, 0.06);
}}
.issue-meta {{
    font-size: 0.76rem;
    color: #8a93a6;
    margin-bottom: 0.3rem;
}}

/* 흰색 카드 패널 (가운데/우측 열) */
div[class*="st-key-panel_"] {{
    background: #ffffff;
    border: 1px solid #e6e8f0;
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}}

/* 부문 칩 */
.category-chip {{
    display: inline-block;
    font-size: 0.8rem;
    font-weight: 700;
    color: {ACCENT};
    background: #eaf0ff;
    padding: 0.3rem 0.7rem;
    border-radius: 8px;
    margin: 0.6rem 0 0.5rem 0;
}}

/* 보관 상태 배지 */
.badge-live, .badge-expired {{
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.12rem 0.5rem;
    border-radius: 999px;
}}
.badge-live {{ color: #1a8f4c; background: #e7f6ed; }}
.badge-expired {{ color: #d1373f; background: #fdeaea; }}

/* 비어 있을 때 자리표시 */
.empty-state {{
    text-align: center;
    color: #8a93a6;
    font-size: 0.88rem;
    padding: 2.2rem 1rem;
    border: 1px dashed #dfe3ee;
    border-radius: 12px;
    background: #fbfcfe;
}}
</style>
"""
    )


def section_title(emoji: str, text: str, count: int | None = None) -> None:
    badge = f'<span class="count-badge">{count}</span>' if count is not None else ""
    st.html(
        f'<div class="section-title">'
        f'<span style="font-size:1.1rem;">{emoji}</span>'
        f"{text}{badge}</div>"
    )


def empty_state(message: str) -> None:
    st.html(f'<div class="empty-state">{message}</div>')
