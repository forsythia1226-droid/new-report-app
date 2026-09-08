"""
Naver News Report Builder - Streamlit App (entry point)

Sets up shared session state (keywords/subcategories, loaded once here so
they exist no matter which page the user lands on first) and wires up the
multipage navigation: the main report-builder page plus a Settings page
for managing keyword subcategories.
"""

import streamlit as st

import app_common
import sheet_store

st.set_page_config(
    page_title="네이버 뉴스 보고서 빌더",
    page_icon="📰",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Shared session state
# ---------------------------------------------------------------------------

if "subcategories" not in st.session_state:
    # category -> [subcategory name, ...]. User-editable from the Settings
    # page. Try the persisted copy in Google Sheets first, else defaults.
    _saved_subs = sheet_store.load_subcategories()
    if _saved_subs:
        st.session_state.subcategories = {
            cat: list(
                _saved_subs.get(cat, app_common.DEFAULT_SUBCATEGORIES_BY_CATEGORY.get(cat, []))
            )
            for cat in app_common.CATEGORY_OPTIONS
        }
    else:
        st.session_state.subcategories = {
            cat: subs.copy()
            for cat, subs in app_common.DEFAULT_SUBCATEGORIES_BY_CATEGORY.items()
        }

if "keywords" not in st.session_state:
    # category -> {subcategory -> [keyword, ...]}. Try the persisted copy in
    # Google Sheets first (this is what makes keywords survive across
    # sessions / reopening the app); fall back to the built-in defaults.
    _saved_keywords = sheet_store.load_keywords()
    if _saved_keywords:
        st.session_state.keywords = {
            cat: dict(
                _saved_keywords.get(cat, app_common.DEFAULT_KEYWORDS_BY_CATEGORY.get(cat, {}))
            )
            for cat in app_common.CATEGORY_OPTIONS
        }
    else:
        st.session_state.keywords = {
            cat: {sub: kws.copy() for sub, kws in subs.items()}
            for cat, subs in app_common.DEFAULT_KEYWORDS_BY_CATEGORY.items()
        }

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

main_page = st.Page("app_pages/main.py", title="뉴스 보고서 빌더", icon="📰", default=True)
settings_page = st.Page("app_pages/settings.py", title="설정", icon="⚙️")

pg = st.navigation([main_page, settings_page])
pg.run()
