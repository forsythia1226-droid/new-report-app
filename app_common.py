"""
Shared constants, theming, and small UI helpers used by every page of the
Naver News Report Builder (app_pages/main.py and app_pages/settings.py).
Keeping this separate from app.py (the st.navigation entry point) avoids
duplicating the CSS block and category/keyword defaults across pages.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Categories, keywords, subcategories
# ---------------------------------------------------------------------------

CATEGORY_OPTIONS = ["■ 전선산업 주요 기사", "■ 거시경제 및 기타 주요 기사"]
MAX_KEYWORDS_PER_SUBCATEGORY = 20
DEFAULT_SUBCATEGORY_FALLBACK = "기타"

# Every category's keyword list is now split into subcategories so a long
# list doesn't force endless scrolling in the sidebar — only the keywords
# for the selected (category, subcategory) pair are shown at once.
DEFAULT_SUBCATEGORIES_BY_CATEGORY = {
    "■ 전선산업 주요 기사": ["기업", "산업", "해저케이블", "기타"],
    "■ 거시경제 및 기타 주요 기사": ["원자재/환율", "경제", "국가", "기타"],
}

DEFAULT_KEYWORDS_BY_CATEGORY = {
    "■ 전선산업 주요 기사": {
        "기업": ["대한전선", "LS일렉트릭"],
        "산업": [],
        "해저케이블": [],
        "기타": ["한전"],
    },
    "■ 거시경제 및 기타 주요 기사": {
        "원자재/환율": ["환율"],
        "경제": ["거시경제"],
        "국가": [],
        "기타": ["금리"],
    },
}

# ---------------------------------------------------------------------------
# Theme colors (shared so Settings visually matches the main page)
# ---------------------------------------------------------------------------

ACCENT = "#2F5DF5"
NAVY = "#1E2A5A"
NAVY_DARK = "#111a3d"
SOFT_BLUE_BG = "#4361EE"
SOFT_BLUE = "#ffffff"


def inject_global_css():
    """Custom styling (explicitly requested) — targets elements via `key=`
    classes so it survives reruns without touching Streamlit's internal DOM
    structure. Call once near the top of every page."""
    st.html(f"""
<style>
/* Page-level breathing room */
.block-container {{
    padding-top: 3.5rem;
    padding-bottom: 2rem;
}}

/* Top enterprise-style header bar */
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
.app-header-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: {NAVY};
    color: #ffffff;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.45rem 0.9rem;
    border-radius: 999px;
    float: right;
}}

/* Date-picker dropdown in the header, styled like the old date badge */
div[class*="st-key-header_date_picker"] {{
    display: flex;
    justify-content: flex-end;
}}
div[class*="st-key-header_date_picker"] [data-testid="stSelectbox"] {{
    width: auto;
    min-width: 170px;
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

/* Section header used at the top of each panel */
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

/* Dark navy panel (left column) — selected items pop as soft-blue chips */
div[class*="st-key-sidebar_panel"] {{
    background: {NAVY_DARK};
    border-radius: 16px;
    padding: 1.1rem 1rem;
}}
div[class*="st-key-sidebar_panel"] .section-title {{
    color: #ffffff;
    border-bottom: 1px solid rgba(255,255,255,0.14);
}}
div[class*="st-key-sidebar_panel"] .section-title .count-badge {{
    color: #cdd7ff;
    background: rgba(255,255,255,0.12);
}}
div[class*="st-key-sidebar_panel"] label,
div[class*="st-key-sidebar_panel"] .stCaption,
div[class*="st-key-sidebar_panel"] p {{
    color: #c6cad9 !important;
}}
div[class*="st-key-sidebar_panel"] hr {{
    border-color: rgba(255,255,255,0.1);
}}

/* Segmented-control pills (period selector) — consistent soft-blue highlight,
   blend into the dark panel when unselected.
   IMPORTANT: the visible label text is not a direct child of the button element.
   Streamlit nests it several levels deep, ending in a markdown-rendered
   paragraph tag that carries its own theme color and beats simple
   inheritance. Every color/weight rule below must therefore also target
   that nested paragraph tag explicitly (selector: "button ... p"). */
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] {{
    justify-content: flex-start;
}}
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] button {{
    flex: 1 1 auto;
    background: {NAVY_DARK} !important;
    border-color: rgba(255,255,255,0.16) !important;
}}
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] button p {{
    color: #c6cad9 !important;
    font-weight: 400 !important;
}}
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] button:hover {{
    background: rgba(255,255,255,0.08) !important;
}}
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] button:hover p {{
    color: #ffffff !important;
}}
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] button[data-selected]:not([data-selected="false"]) {{
    background: {SOFT_BLUE_BG} !important;
    box-shadow: none !important;
}}
div[class*="st-key-sidebar_panel"] [data-testid="stButtonGroup"] button[data-selected]:not([data-selected="false"]) p {{
    color: #ffffff !important;
    font-weight: 700 !important;
}}

/* News result cards (center column) — calm, table-like row style */
div[class*="st-key-newscard_"] {{
    background: #ffffff;
    border: 1px solid #edeff5;
    border-bottom: 1px solid #e6e8f0;
    border-radius: 10px;
    padding: 0.8rem 1rem 0.6rem 1rem;
    margin-bottom: 0.55rem;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
div[class*="st-key-newscard_"]:hover {{
    border-color: #cfd6ea;
    box-shadow: 0 2px 10px rgba(16, 24, 40, 0.06);
}}

/* Category chip labels in the report preview */
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

/* Empty-state placeholder box */
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
""")


def section_title(emoji: str, text: str, count: int | None = None):
    badge = f'<span class="count-badge">{count}</span>' if count is not None else ""
    st.html(
        f'<div class="section-title">'
        f'<span style="font-size:1.1rem;">{emoji}</span>'
        f'{text}{badge}</div>'
    )
