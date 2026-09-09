"""
Naver News Report Builder - main page
Search Naver news by keyword, filter by period, curate articles into a
categorized report with shortened (TinyURL) URLs.
"""

import re

import streamlit as st
from datetime import datetime, timedelta, date

from news_service import NaverNewsService, URLShortener
import sheet_store
import app_common
from app_common import (
    CATEGORY_OPTIONS,
    MAX_KEYWORDS_PER_SUBCATEGORY,
    is_reordering_of,
    section_title,
)
from settings_dialog import SHOW_SETTINGS_KEY, settings_dialog

# ---------------------------------------------------------------------------
# Draggable keyword list (custom component, CCv2) — lets the user reorder
# keywords by mouse drag instead of up/down arrow buttons. Clicking a row
# selects it as the active keyword; the trash icon removes it.
# ---------------------------------------------------------------------------

_KEYWORD_DRAG_LIST_HTML = """
<div id="list" class="kw-draggable-list"></div>
<style>
  .kw-draggable-list { display: flex; flex-direction: column; gap: 6px; }
  .kw-row {
    display: flex; align-items: center; gap: 8px;
    background: #111a3d; color: #c6cad9;
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 8px; padding: 8px 10px;
    cursor: grab; font-size: 14px; font-family: inherit;
    user-select: none; transition: background 0.1s ease, border-color 0.1s ease;
  }
  .kw-row.active { background: #4361EE; color: #ffffff; font-weight: 700; }
  .kw-row.drag-over { border-color: #4361EE; border-style: dashed; }
  .kw-row.dragging { opacity: 0.45; }
  .kw-handle { opacity: 0.55; cursor: grab; }
  .kw-label { flex: 1; cursor: pointer; }
  .kw-delete { cursor: pointer; opacity: 0.8; }
  .kw-delete:hover { opacity: 1; }
</style>
"""

_KEYWORD_DRAG_LIST_JS = """
export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  const container = parentElement.querySelector('#list')
  if (!container) return

  const items = data.items || []
  const current = data.current

  container.innerHTML = ''
  let dragSrcIndex = null

  items.forEach((item, idx) => {
    const row = document.createElement('div')
    row.className = 'kw-row' + (item === current ? ' active' : '')
    row.draggable = true

    const handle = document.createElement('span')
    handle.className = 'kw-handle'
    handle.textContent = '\\u283f'
    handle.onclick = (e) => e.stopPropagation()

    const label = document.createElement('span')
    label.className = 'kw-label'
    label.textContent = item
    label.onclick = () => setTriggerValue('selected', item)

    const del = document.createElement('span')
    del.className = 'kw-delete'
    del.textContent = '\\ud83d\\uddd1\\ufe0f'
    del.onclick = (e) => {
      e.stopPropagation()
      setTriggerValue('deleted', item)
    }

    row.appendChild(handle)
    row.appendChild(label)
    row.appendChild(del)

    row.addEventListener('dragstart', () => {
      dragSrcIndex = idx
      row.classList.add('dragging')
    })
    row.addEventListener('dragend', () => {
      row.classList.remove('dragging')
    })
    row.addEventListener('dragover', (e) => {
      e.preventDefault()
      row.classList.add('drag-over')
    })
    row.addEventListener('dragleave', () => {
      row.classList.remove('drag-over')
    })
    row.addEventListener('drop', (e) => {
      e.preventDefault()
      row.classList.remove('drag-over')
      if (dragSrcIndex === null || dragSrcIndex === idx) return
      const newItems = items.slice()
      const [moved] = newItems.splice(dragSrcIndex, 1)
      newItems.splice(idx, 0, moved)
      setStateValue('order', newItems)
    })

    container.appendChild(row)
  })
}
"""

_KEYWORD_DRAG_LIST = st.components.v2.component(
    "keyword_drag_list",
    html=_KEYWORD_DRAG_LIST_HTML,
    js=_KEYWORD_DRAG_LIST_JS,
)


def keyword_drag_list(items: list[str], current: str | None, key: str):
    """Render a drag-reorderable keyword list. Returns the CCv2 result object
    with `.selected` (trigger), `.deleted` (trigger), and `.order` (state)."""
    return _KEYWORD_DRAG_LIST(
        key=key,
        data={"items": items, "current": current},
        default={"order": None},
        on_order_change=lambda: None,
        on_selected_change=lambda: None,
        on_deleted_change=lambda: None,
    )


# ---------------------------------------------------------------------------
# Draggable report-item list (custom component, CCv2) — lets the user
# reorder curated report entries by mouse drag instead of up/down buttons.
# ---------------------------------------------------------------------------

_REPORT_DRAG_LIST_HTML = """
<div id="list" class="rp-draggable-list"></div>
<style>
  .rp-draggable-list { display: flex; flex-direction: column; gap: 6px; }
  .rp-row {
    display: flex; align-items: flex-start; gap: 8px;
    background: #fbfcfe; color: #12172b;
    border: 1px solid #edf0f7;
    border-radius: 10px; padding: 8px 10px;
    cursor: grab; font-size: 14px; font-family: inherit;
    user-select: none; transition: border-color 0.1s ease, box-shadow 0.1s ease;
  }
  .rp-row.drag-over { border-color: #3182F6; border-style: dashed; }
  .rp-row.dragging { opacity: 0.45; }
  .rp-handle { opacity: 0.45; cursor: grab; padding-top: 2px; }
  .rp-body { flex: 1; min-width: 0; }
  .rp-title { font-weight: 700; word-break: break-word; }
  .rp-url { color: #8a93a6; font-size: 0.8rem; word-break: break-all; margin-top: 2px; }
  .rp-delete { cursor: pointer; opacity: 0.7; padding-top: 2px; }
  .rp-delete:hover { opacity: 1; }
</style>
"""

_REPORT_DRAG_LIST_JS = """
export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  const container = parentElement.querySelector('#list')
  if (!container) return

  const items = data.items || []

  container.innerHTML = ''
  let dragSrcIndex = null

  items.forEach((item, idx) => {
    const row = document.createElement('div')
    row.className = 'rp-row'
    row.draggable = true

    const handle = document.createElement('span')
    handle.className = 'rp-handle'
    handle.textContent = '\\u283f'

    const body = document.createElement('div')
    body.className = 'rp-body'
    const title = document.createElement('div')
    title.className = 'rp-title'
    title.textContent = item.title
    const url = document.createElement('div')
    url.className = 'rp-url'
    url.textContent = item.url
    body.appendChild(title)
    body.appendChild(url)

    const del = document.createElement('span')
    del.className = 'rp-delete'
    del.textContent = '\\u274c'
    del.onclick = (e) => {
      e.stopPropagation()
      setTriggerValue('deleted_index', idx)
    }

    row.appendChild(handle)
    row.appendChild(body)
    row.appendChild(del)

    row.addEventListener('dragstart', () => {
      dragSrcIndex = idx
      row.classList.add('dragging')
    })
    row.addEventListener('dragend', () => {
      row.classList.remove('dragging')
    })
    row.addEventListener('dragover', (e) => {
      e.preventDefault()
      row.classList.add('drag-over')
    })
    row.addEventListener('dragleave', () => {
      row.classList.remove('drag-over')
    })
    row.addEventListener('drop', (e) => {
      e.preventDefault()
      row.classList.remove('drag-over')
      if (dragSrcIndex === null || dragSrcIndex === idx) return
      const newItems = items.slice()
      const [moved] = newItems.splice(dragSrcIndex, 1)
      newItems.splice(idx, 0, moved)
      setStateValue('order', newItems)
    })

    container.appendChild(row)
  })
}
"""

_REPORT_DRAG_LIST = st.components.v2.component(
    "report_drag_list",
    html=_REPORT_DRAG_LIST_HTML,
    js=_REPORT_DRAG_LIST_JS,
)


def report_drag_list(items: list[dict], key: str):
    """Render a drag-reorderable report-item list. Returns the CCv2 result
    object with `.deleted_index` (trigger) and `.order` (state)."""
    return _REPORT_DRAG_LIST(
        key=key,
        data={"items": items},
        default={"order": None},
        on_order_change=lambda: None,
        on_deleted_index_change=lambda: None,
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERIOD_OPTIONS = ["최근 24시간 이내", "최근 3일 이내", "날짜 직접 지정"]
PERIOD_HOURS = {
    "최근 24시간 이내": 24,
    "최근 3일 이내": 24 * 3,
}

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

app_common.inject_global_css()

# ---------------------------------------------------------------------------
# Session state initialization (page-specific; keywords/subcategories are
# initialized once in app.py so they exist regardless of which page loads
# first)
# ---------------------------------------------------------------------------

if "current_keyword" not in st.session_state:
    st.session_state.current_keyword = None

if "articles_cache" not in st.session_state:
    st.session_state.articles_cache = {}  # keyword -> list[article dict]

if "report_title" not in st.session_state:
    st.session_state.report_title = "[대한전선] 주요 기사 모음"

if "report_items" not in st.session_state:
    # category -> list of {"title": str, "url": str}
    #
    # Restore today's saved report if there is one. Saved snapshots used to
    # be read back only when viewing a *past* date, so everything added via
    # "보고서에 추가" looked lost the moment the session restarted — even
    # right after pressing "보고서 저장".
    _saved_today = sheet_store.load_report_snapshot(date.today().strftime("%Y-%m-%d"))
    if _saved_today:
        _saved_title, _saved_items = _saved_today
        if _saved_title:
            st.session_state.report_title = _saved_title
        st.session_state.report_items = {
            cat: list(_saved_items.get(cat, [])) for cat in CATEGORY_OPTIONS
        }
    else:
        st.session_state.report_items = {cat: [] for cat in CATEGORY_OPTIONS}


def persist_keywords():
    """Save the keyword tree to Google Sheets, surfacing failures.

    This used to ignore the return value, so a failing write (e.g. the sheet
    grid being too narrow for a new column) looked like "keywords silently
    stop saving" — added keywords lived only in session state and vanished
    on the next reload."""
    if not sheet_store.is_configured():
        return
    ok, err = sheet_store.save_keywords(st.session_state.keywords)
    if not ok:
        st.toast(f"키워드 저장 실패: {err}", icon="⚠️")


def get_services():
    # Intentionally not cached: these objects are cheap to construct (they
    # just read a couple of config strings), and caching them with
    # st.cache_resource previously caused stale-object AttributeErrors after
    # a redeploy, since Streamlit Cloud can reuse a running process across
    # a git-push update rather than always restarting it fresh.
    news_service = NaverNewsService()
    shortener = URLShortener()
    return news_service, shortener


def fetch_articles(keyword: str):
    """Fetch (and cache) news articles for a keyword."""
    if keyword in st.session_state.articles_cache:
        return st.session_state.articles_cache[keyword]

    news_service, _ = get_services()
    try:
        articles = news_service.search_news(query=keyword, display=30, sort="sim")
    except Exception as e:
        st.error(f"뉴스 검색 중 오류가 발생했습니다: {e}", icon="❌")
        articles = []

    st.session_state.articles_cache[keyword] = articles
    return articles


def parse_pub_date(date_str: str):
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except (ValueError, TypeError):
        return None


def filter_by_period(articles, period_mode: str, custom_range=None):
    """Filter articles by pubDate.

    - '최근 24시간 이내' / '최근 3일 이내': keep articles within that rolling window.
    - '날짜 직접 지정': keep articles whose pubDate falls within [start_date, end_date].
    """
    if period_mode == "날짜 직접 지정":
        if not custom_range or len(custom_range) < 2:
            return articles
        start_date, end_date = custom_range[0], custom_range[1]
        filtered = []
        for article in articles:
            pub_dt = parse_pub_date(article.get("published_date", ""))
            if pub_dt is not None and start_date <= pub_dt.date() <= end_date:
                filtered.append(article)
        return filtered

    hours = PERIOD_HOURS.get(period_mode, 24)
    cutoff = datetime.now() - timedelta(hours=hours)
    filtered = []
    for article in articles:
        pub_dt = parse_pub_date(article.get("published_date", ""))
        if pub_dt is not None and pub_dt >= cutoff:
            filtered.append(article)
    return filtered


def _normalize_title_for_similarity(title: str) -> str:
    """Strip quotes/brackets and collapse whitespace so titles that only
    differ by punctuation or spacing compare as identical."""
    cleaned = re.sub(r'[\"\'“”‘’\[\]()【】<>·…]', "", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def group_similar_articles(articles: list[dict], threshold: float = 0.6) -> list[list[dict]]:
    """Cluster articles that report on the same story (near-duplicate titles),
    similar to Naver News' "관련뉴스" grouping. Preserves the original
    (relevance-sorted) order: the first article of each group is the
    representative shown as the main card."""
    from difflib import SequenceMatcher

    normalized = [_normalize_title_for_similarity(a["title"]) for a in articles]
    used = [False] * len(articles)
    groups: list[list[dict]] = []

    for i, article in enumerate(articles):
        if used[i]:
            continue
        group = [article]
        used[i] = True
        for j in range(i + 1, len(articles)):
            if used[j]:
                continue
            ratio = SequenceMatcher(None, normalized[i], normalized[j]).ratio()
            if ratio >= threshold:
                group.append(articles[j])
                used[j] = True
        groups.append(group)

    return groups


def highlight_keyword(text: str, keyword: str) -> str:
    """Wrap every occurrence of `keyword` in `text` with Streamlit's blue
    markdown color directive so it stands out in the article title."""
    if not keyword:
        return text
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(lambda m: f":blue[{m.group(0)}]", text)


def split_title_two_lines(title: str) -> list[str]:
    """Split a title into two lines at the whitespace closest to its midpoint."""
    words = title.split()
    if len(words) < 2:
        return [title]

    midpoint = len(title) / 2
    cumulative = 0
    best_split_idx = 1
    best_diff = None

    for i, word in enumerate(words[:-1], start=1):
        cumulative += len(word) + (1 if i > 1 else 0)
        diff = abs(cumulative - midpoint)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_split_idx = i

    line1 = " ".join(words[:best_split_idx])
    line2 = " ".join(words[best_split_idx:])
    return [line1, line2]


def build_report_text(title: str = None, report_items: dict = None) -> str:
    """Build the final report text. Defaults to the live (editable) report
    in session_state; pass `title`/`report_items` to render a read-only
    snapshot loaded from a past date instead."""
    if title is None:
        title = st.session_state.report_title
    if report_items is None:
        report_items = st.session_state.report_items

    lines = [title]

    for category in CATEGORY_OPTIONS:
        items = report_items.get(category, [])
        if not items:
            continue

        lines.append(category)
        lines.append("")

        for item in items:
            lines.extend(split_title_two_lines(item["title"]))
            lines.append(item["url"])
            lines.append("")

    # Drop the trailing blank line left after the last article.
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

TODAY_STR = date.today().strftime("%Y-%m-%d")

if "viewing_date" not in st.session_state:
    st.session_state.viewing_date = TODAY_STR

# Auto-purge reports older than ~6 months. Runs once per browser session
# (not on every rerun) since it's a full read+rewrite of the sheet — cheap
# for the sheet sizes this app expects, but no reason to pay for it on
# every click within the same session.
if "retention_purge_done" not in st.session_state:
    st.session_state.retention_purge_done = True
    deleted_count, purge_err = sheet_store.purge_old_reports()
    if deleted_count:
        st.toast(f"6개월 지난 보고서 {deleted_count}건이 자동 삭제되었습니다.", icon="🗑️")

with st.container(key="app_header"):
    hcol1, hcol2 = st.columns([3, 1], vertical_alignment="center")
    with hcol1:
        st.html(
            '<div class="app-header-title">📰 [대한전선] 주요 기사 모음</div>'
            '<div class="app-header-caption">키워드로 뉴스를 검색하고, 카테고리별로 큐레이션해 공유용 보고서를 완성하세요.</div>'
        )
    with hcol2:
        with st.container(key="header_date_picker"):
            saved_dates = sheet_store.load_report_dates()
            date_options = sorted({TODAY_STR, *saved_dates}, reverse=True)

            def _format_date_option(d: str) -> str:
                label = d.replace("-", ".")
                return f"📅 {label} (오늘)" if d == TODAY_STR else f"📅 {label}"

            st.selectbox(
                "조회 날짜",
                date_options,
                key="viewing_date",
                format_func=_format_date_option,
                label_visibility="collapsed",
            )

# Settings modal — kept open across app reruns by a session flag, since the
# dialog only renders on runs where its function is called.
if st.session_state.get(SHOW_SETTINGS_KEY):
    settings_dialog()

left_col, center_col, right_col = st.columns([1, 2, 1.5])

# ---------------------------------------------------------------------------
# Left Column - Keyword & Period Filter (dark control-panel styling)
# ---------------------------------------------------------------------------

with left_col:
    with st.container(key="sidebar_panel"):
        title_col, settings_col = st.columns([4, 1], vertical_alignment="center")
        with title_col:
            section_title("🔎", "검색 조건")
        with settings_col:
            with st.container(key="settings_button"):
                if st.button(
                    "",
                    icon="⚙️",
                    key="open_settings",
                    help="세부 카테고리 설정",
                    width="content",
                ):
                    st.session_state[SHOW_SETTINGS_KEY] = True
                    st.rerun()

        period = st.segmented_control(
            "검색 기간",
            PERIOD_OPTIONS,
            default=PERIOD_OPTIONS[0],
            key="period_filter",
        )
        if period is None:
            period = PERIOD_OPTIONS[0]

        custom_date_range = None
        if period == "날짜 직접 지정":
            custom_date_range = st.date_input(
                "조회 기간",
                value=(date.today() - timedelta(days=7), date.today()),
                key="custom_date_range",
            )

        st.space("small")
        section_title("🏷️", "키워드 항목")

        cat_col, sub_col = st.columns(2)
        with cat_col:
            kw_category = st.selectbox(
                "키워드 카테고리",
                CATEGORY_OPTIONS,
                key="kw_category",
                format_func=lambda cat: cat.replace("■ ", ""),
                label_visibility="collapsed",
            )
        with sub_col:
            available_subs = st.session_state.subcategories.get(kw_category) or ["기타"]

            # The stored selection for this category's subcategory dropdown
            # can go stale if subcategories were renamed/deleted on the
            # Settings page — reconcile it *before* instantiating the
            # widget with the same key, or Streamlit raises.
            sub_key = f"kw_subcategory_{kw_category}"
            if st.session_state.get(sub_key) not in available_subs:
                st.session_state[sub_key] = available_subs[0]

            kw_subcategory = st.selectbox(
                "세부 카테고리",
                available_subs,
                key=sub_key,
                label_visibility="collapsed",
            )

        category_keywords = st.session_state.keywords.setdefault(kw_category, {})
        active_keywords = category_keywords.setdefault(kw_subcategory, [])

        if active_keywords:
            drag_result = keyword_drag_list(
                active_keywords,
                st.session_state.current_keyword,
                key=f"kwdrag_{kw_category}_{kw_subcategory}",
            )

            if drag_result.selected:
                st.session_state.current_keyword = drag_result.selected
                st.rerun()

            if drag_result.deleted:
                if drag_result.deleted in active_keywords:
                    active_keywords.remove(drag_result.deleted)
                    st.session_state.articles_cache.pop(drag_result.deleted, None)
                    if st.session_state.current_keyword == drag_result.deleted:
                        st.session_state.current_keyword = None
                    persist_keywords()
                st.rerun()

            # `order` is component *state*, so it keeps holding the snapshot
            # from the last drag. Only honour it when it's a pure reordering
            # of what's currently in the list — otherwise adding or deleting
            # a keyword would get reverted to that stale snapshot.
            if drag_result.order and is_reordering_of(drag_result.order, active_keywords):
                active_keywords[:] = drag_result.order
                persist_keywords()
                st.rerun()
        else:
            st.caption("등록된 키워드가 없습니다.")

        st.caption(f"{len(active_keywords)} / {MAX_KEYWORDS_PER_SUBCATEGORY}")

        st.space("small")

        with st.form(
            f"add_keyword_form_{kw_category}_{kw_subcategory}",
            clear_on_submit=True,
            border=False,
        ):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                new_keyword = st.text_input(
                    "새 키워드 추가",
                    placeholder="새 키워드 입력",
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    "저장", icon="💾", width="content"
                )
            if submitted and new_keyword.strip():
                if len(active_keywords) >= MAX_KEYWORDS_PER_SUBCATEGORY:
                    st.warning(
                        f"세부 카테고리당 최대 {MAX_KEYWORDS_PER_SUBCATEGORY}개까지 등록할 수 있습니다.",
                        icon="⚠️",
                    )
                elif new_keyword.strip() not in active_keywords:
                    active_keywords.append(new_keyword.strip())
                    persist_keywords()
                    st.rerun()
                else:
                    st.warning("이미 등록된 키워드입니다.", icon="⚠️")

# ---------------------------------------------------------------------------
# Center Column - Search Results
# ---------------------------------------------------------------------------

with center_col:
    active_keyword = st.session_state.current_keyword

    all_articles = fetch_articles(active_keyword) if active_keyword else []
    filtered_articles = (
        filter_by_period(all_articles, period, custom_date_range) if active_keyword else []
    )

    if not active_keyword:
        section_title("🔍", "뉴스 검색 결과")
        st.caption("좌측에서 키워드를 선택해주세요")
    else:
        article_groups = group_similar_articles(filtered_articles)

        section_title(
            "🔍",
            f"'{active_keyword}' 검색 결과",
            count=len(article_groups),
        )

        for idx, group in enumerate(article_groups):
            article = group[0]
            related = group[1:]

            with st.container(key=f"newscard_{active_keyword}_{idx}"):
                highlighted_title = highlight_keyword(article["title"], active_keyword)
                st.markdown(f"**{highlighted_title}**")
                st.caption(
                    f"🏢 {article['source']}&nbsp;&nbsp;·&nbsp;&nbsp;"
                    f"🕒 {article['published_date']}&nbsp;&nbsp;·&nbsp;&nbsp;"
                    f"[🔗 원문 보기]({article['original_url']})"
                )

                if related:
                    with st.expander(f"관련뉴스 {len(related)}건 전체보기"):
                        for r_idx, r_article in enumerate(related):
                            r_title = highlight_keyword(r_article["title"], active_keyword)
                            st.markdown(f"{r_title}")
                            st.caption(
                                f"{r_article['source']} · {r_article['published_date']} · "
                                f"[원문 보기]({r_article['original_url']})"
                            )
                            if r_idx < len(related) - 1:
                                st.divider()

                cat_col2, add_col = st.columns([2, 1], vertical_alignment="bottom")
                with cat_col2:
                    selected_category = st.selectbox(
                        "카테고리",
                        CATEGORY_OPTIONS,
                        index=CATEGORY_OPTIONS.index(kw_category),
                        key=f"cat_{active_keyword}_{idx}",
                        label_visibility="collapsed",
                    )
                with add_col:
                    if st.button(
                        "보고서에 추가",
                        icon="➕",
                        key=f"add_{active_keyword}_{idx}",
                        width="stretch",
                    ):
                        _, shortener = get_services()
                        original_url = article["original_url"]

                        # Session-level cache: the same article can be added
                        # more than once (different category, re-search after
                        # a rerun); skip the network round-trip when we
                        # already have a shortened URL for this exact link.
                        url_cache = st.session_state.setdefault("short_url_cache", {})
                        error_reason = None
                        if original_url in url_cache:
                            short_url = url_cache[original_url]
                        else:
                            with st.spinner("TinyURL 단축 URL 생성 중..."):
                                short_url, error_reason = shortener.shorten_url_verbose(
                                    original_url, retries=2, timeout=10.0
                                )
                            if error_reason is None:
                                url_cache[original_url] = short_url

                        st.session_state.report_items[selected_category].append(
                            {"title": article["title"], "url": short_url}
                        )

                        if error_reason:
                            st.toast(
                                f"⚠️ 단축 URL 생성 실패 → 원본 URL 저장됨\n{error_reason}",
                                icon="⚠️",
                            )
                        else:
                            st.toast(
                                f"보고서에 추가되었습니다 · {article['title'][:24]}...",
                                icon="✅",
                            )
                        st.rerun()

# ---------------------------------------------------------------------------
# Right Column - Report Preview
# ---------------------------------------------------------------------------

is_viewing_today = st.session_state.viewing_date == TODAY_STR

with right_col:
    if not is_viewing_today:
        # ---- Read-only view of a past day's saved report ----
        snapshot = sheet_store.load_report_snapshot(st.session_state.viewing_date)

        with st.container(border=True):
            section_title("📖", f"{st.session_state.viewing_date} 기록 (읽기 전용)")

            if snapshot is None:
                st.caption("해당 날짜에 저장된 보고서가 없습니다.")
            else:
                snap_title, snap_items = snapshot
                st.markdown(f"**{snap_title}**")

                for category in CATEGORY_OPTIONS:
                    items = snap_items.get(category, [])
                    if not items:
                        continue
                    st.html(f'<div class="category-chip">{category}</div>')
                    for item in items:
                        st.markdown(f"**{item['title']}**")
                        st.caption(item["url"])

                if st.button(
                    "이 날짜를 불러와 오늘 보고서로 편집",
                    icon="✏️",
                    width="stretch",
                ):
                    st.session_state.report_title = snap_title
                    st.session_state.report_items = {
                        cat: list(snap_items.get(cat, [])) for cat in CATEGORY_OPTIONS
                    }
                    st.session_state.viewing_date = TODAY_STR
                    st.rerun()

        st.space("small")

        with st.container(border=True):
            section_title("📝", "최종 결과물")
            if snapshot is None:
                st.caption("표시할 내용이 없습니다.")
            else:
                snap_title, snap_items = snapshot
                st.code(build_report_text(snap_title, snap_items), language=None, wrap_lines=True)

    else:
        # ---- Live, editable report for today ----
        with st.container(border=True):
            section_title("📋", "보고서 미리보기")

            st.text_input("보고서 제목", key="report_title", label_visibility="collapsed")

            total_items = sum(len(v) for v in st.session_state.report_items.values())

            if total_items == 0:
                st.html(
                    '<div class="empty-state">'
                    '중앙에서 기사를 추가하면 이곳에 표시됩니다.'
                    '</div>'
                )
            else:
                for category in CATEGORY_OPTIONS:
                    items = st.session_state.report_items.get(category, [])
                    if not items:
                        continue

                    st.html(f'<div class="category-chip">{category}</div>')

                    rp_result = report_drag_list(items, key=f"rpdrag_{category}")

                    if rp_result.deleted_index is not None:
                        del_idx = rp_result.deleted_index
                        if 0 <= del_idx < len(items):
                            items.pop(del_idx)
                        st.rerun()

                    # Same stale-state guard as the keyword list: only apply
                    # a drag result that reorders exactly the current items.
                    if rp_result.order and is_reordering_of(rp_result.order, items):
                        items[:] = rp_result.order
                        st.rerun()

        st.space("small")

        with st.container(border=True):
            section_title("📝", "최종 결과물")

            report_text = build_report_text()
            st.code(report_text, language=None, wrap_lines=True)
            st.caption("우측 상단 아이콘을 눌러 클립보드에 바로 복사할 수 있습니다.")

            dl_col, save_col = st.columns(2)
            with dl_col:
                st.download_button(
                    "텍스트 파일 다운로드",
                    icon="📥",
                    data=report_text,
                    file_name=f"news_report_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    width="stretch",
                )
            with save_col:
                if sheet_store.is_configured():
                    if st.button(
                        "보고서 저장", icon="💾", width="stretch"
                    ):
                        saved_count = sum(
                            len(v) for v in st.session_state.report_items.values()
                        )
                        ok, err = sheet_store.save_report_snapshot(
                            TODAY_STR,
                            st.session_state.report_title,
                            st.session_state.report_items,
                        )
                        if ok:
                            st.toast(
                                f"오늘 보고서가 저장되었습니다 · 기사 {saved_count}건",
                                icon="✅",
                            )
                        else:
                            st.toast(f"저장 실패: {err}", icon="⚠️")
                else:
                    st.button(
                        "보고서 저장", icon="💾", width="stretch", disabled=True,
                        help="Google Sheets 연동이 설정되지 않았습니다.",
                    )
