"""
Naver News Report Builder - Streamlit App
Search Naver news by keyword, filter by period, curate articles into a
categorized report with shortened (buly.kr) URLs.
"""

import re

import streamlit as st
from datetime import datetime, timedelta, date

from news_service import NaverNewsService, URLShortener

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

CATEGORY_OPTIONS = ["■ 전선산업 주요 기사", "■ 거시경제 및 기타 주요 기사"]

DEFAULT_KEYWORDS_BY_CATEGORY = {
    "■ 전선산업 주요 기사": ["대한전선", "LS일렉트릭", "한전"],
    "■ 거시경제 및 기타 주요 기사": ["거시경제", "환율", "금리"],
}

PERIOD_OPTIONS = ["최근 24시간 이내", "날짜 직접 지정"]

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

st.set_page_config(
    page_title="네이버 뉴스 보고서 빌더",
    page_icon="📰",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom styling (explicitly requested) — targets elements via `key=` classes
# so it survives reruns without touching Streamlit's internal DOM structure.
# ---------------------------------------------------------------------------

ACCENT = "#2F5DF5"
NAVY = "#1E2A5A"
NAVY_DARK = "#111a3d"
SOFT_BLUE_BG = "#4361EE"
SOFT_BLUE = "#ffffff"

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

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

if "keywords" not in st.session_state:
    # category -> list of keyword strings
    st.session_state.keywords = {
        cat: kws.copy() for cat, kws in DEFAULT_KEYWORDS_BY_CATEGORY.items()
    }

if "current_keyword" not in st.session_state:
    st.session_state.current_keyword = None

if "articles_cache" not in st.session_state:
    st.session_state.articles_cache = {}  # keyword -> list[article dict]

if "report_title" not in st.session_state:
    st.session_state.report_title = "[대한전선] 주요 기사 모음"

if "report_items" not in st.session_state:
    # category -> list of {"title": str, "url": str}
    st.session_state.report_items = {cat: [] for cat in CATEGORY_OPTIONS}


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

    - '최근 24시간 이내': keep articles published within the last 24 hours.
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

    # Default: 최근 24시간 이내
    cutoff = datetime.now() - timedelta(hours=24)
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


def build_report_text() -> str:
    lines = [st.session_state.report_title]

    for category in CATEGORY_OPTIONS:
        items = st.session_state.report_items.get(category, [])
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


def section_title(emoji: str, text: str, count: int | None = None):
    badge = f'<span class="count-badge">{count}</span>' if count is not None else ""
    st.html(
        f'<div class="section-title">'
        f'<span style="font-size:1.1rem;">{emoji}</span>'
        f'{text}{badge}</div>'
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

with st.container(key="app_header"):
    hcol1, hcol2 = st.columns([3, 1], vertical_alignment="center")
    with hcol1:
        st.html(
            '<div class="app-header-title">📰 [대한전선] 주요 기사 모음</div>'
            '<div class="app-header-caption">키워드로 뉴스를 검색하고, 카테고리별로 큐레이션해 공유용 보고서를 완성하세요.</div>'
        )
    with hcol2:
        st.html(
            '<span class="app-header-badge">'
            f'📅 {datetime.now().strftime("%Y.%m.%d")}</span>'
        )

left_col, center_col, right_col = st.columns([1, 2, 1.5])

# ---------------------------------------------------------------------------
# Left Column - Keyword & Period Filter (dark control-panel styling)
# ---------------------------------------------------------------------------

with left_col:
    with st.container(key="sidebar_panel"):
        section_title("⚙️", "검색 조건")

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

        kw_category = st.selectbox(
            "키워드 카테고리",
            CATEGORY_OPTIONS,
            key="kw_category",
            format_func=lambda cat: cat.replace("■ ", ""),
        )

        active_keywords = st.session_state.keywords.setdefault(kw_category, [])

        if active_keywords:
            drag_result = keyword_drag_list(
                active_keywords,
                st.session_state.current_keyword,
                key=f"kwdrag_{kw_category}",
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
                st.rerun()

            if drag_result.order and list(drag_result.order) != active_keywords:
                active_keywords[:] = drag_result.order
                st.rerun()
        else:
            st.caption("등록된 키워드가 없습니다.")

        st.space("small")

        with st.form(f"add_keyword_form_{kw_category}", clear_on_submit=True, border=False):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                new_keyword = st.text_input(
                    "새 키워드 추가",
                    placeholder="새 키워드 입력",
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    "추가", icon="➕", width="content"
                )
            if submitted and new_keyword.strip():
                if new_keyword.strip() not in active_keywords:
                    active_keywords.append(new_keyword.strip())
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

                cat_col, add_col = st.columns([2, 1], vertical_alignment="bottom")
                with cat_col:
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
                            with st.spinner("buly.kr 단축 URL 생성 중..."):
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

with right_col:
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

                if rp_result.order and list(rp_result.order) != items:
                    items[:] = rp_result.order
                    st.rerun()

    st.space("small")

    with st.container(border=True):
        section_title("📝", "최종 결과물")

        report_text = build_report_text()
        st.code(report_text, language=None, wrap_lines=True)
        st.caption("우측 상단 아이콘을 눌러 클립보드에 바로 복사할 수 있습니다.")

        dl_col, clear_col = st.columns(2)
        with dl_col:
            st.download_button(
                "텍스트 파일 다운로드",
                icon="📥",
                data=report_text,
                file_name=f"news_report_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                width="stretch",
            )
        with clear_col:
            if st.button(
                "보고서 초기화", icon="🔄", width="stretch"
            ):
                st.session_state.report_items = {cat: [] for cat in CATEGORY_OPTIONS}
                st.rerun()
