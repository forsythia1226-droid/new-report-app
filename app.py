"""
Naver News Report Builder - Streamlit App (entry point)

Sets up shared session state (keywords/subcategories, loaded once here) and
renders the single report-builder page. Settings live in a modal opened
from the page itself rather than a separate route.
"""

import streamlit as st

import _reload_guard
import app_common
import sheet_store

# Streamlit Cloud may keep a warm process across a deploy: this entry script
# and the page script are re-read from disk every rerun, but imported helper
# modules stay cached at their old version, which has broken the app after
# past deploys until someone hit "Reboot app". Reload just the ones whose
# source actually changed so a deploy heals itself on the next rerun.
_reload_guard.reload_changed()

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
# Single page, no sidebar nav: settings moved into a modal opened from the
# ⚙️ button beside the "검색 조건" panel title, so the whole screen stays
# focused on the report builder. `position="hidden"` keeps st.navigation's
# routing without rendering a nav menu.

main_page = st.Page("app_pages/main.py", title="뉴스 보고서 빌더", icon="📰", default=True)

pg = st.navigation([main_page], position="hidden")
pg.run()
