"""
Settings modal — manage the keyword subcategory dropdown options shown next
to each top-level category on the main page (e.g. "기업" / "산업" /
"해저케이블" / "기타" under 전선산업 주요 기사).

Opened from the ⚙️ button beside the "검색 조건" panel title. Rows can be
reordered by dragging their handle, renamed inline, or deleted. Keywords
filed under a renamed subcategory move with it; keywords under a deleted
subcategory move to another remaining subcategory (preferring "기타")
rather than being discarded.
"""

import streamlit as st

import sheet_store
from app_common import (
    CATEGORY_OPTIONS,
    DEFAULT_SUBCATEGORY_FALLBACK,
    is_reordering_of,
)

SHOW_SETTINGS_KEY = "show_settings_dialog"

# ---------------------------------------------------------------------------
# Draggable subcategory list (custom component, CCv2)
# ---------------------------------------------------------------------------

_SUBCATEGORY_DRAG_LIST_HTML = """
<div id="list" class="sc-draggable-list"></div>
<style>
  .sc-draggable-list { display: flex; flex-direction: column; gap: 6px; }
  .sc-row {
    display: flex; align-items: center; gap: 10px;
    background: #ffffff; color: #12172b;
    border: 1px solid #e6e8f0;
    border-radius: 10px; padding: 8px 12px;
    font-size: 14px; font-family: inherit;
    transition: border-color 0.12s ease, box-shadow 0.12s ease,
                opacity 0.12s ease, background 0.12s ease;
  }
  .sc-row:hover { border-color: #cfd6ea; box-shadow: 0 2px 8px rgba(16,24,40,0.06); }
  .sc-row.drag-over { border-color: #4361EE; border-style: dashed; background: #f4f7ff; }
  .sc-row.dragging { opacity: 0.4; }
  .sc-handle {
    cursor: grab; color: #9aa2b1; user-select: none;
    font-size: 15px; letter-spacing: -3px; padding-right: 2px;
  }
  .sc-handle:active { cursor: grabbing; }
  .sc-input {
    flex: 1; min-width: 0; border: none; outline: none;
    background: transparent; color: inherit;
    font-size: 14px; font-family: inherit; padding: 2px 4px;
    border-radius: 6px;
  }
  .sc-input:focus { background: #f4f7ff; outline: 1px solid #c7d2fe; }
  .sc-delete {
    cursor: pointer; color: #9aa2b1; font-size: 14px;
    padding: 0 2px; user-select: none;
  }
  .sc-delete:hover { color: #d1373f; }
</style>
"""

_SUBCATEGORY_DRAG_LIST_JS = """
export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  const container = parentElement.querySelector('#list')
  if (!container) return

  const items = data.items || []

  container.innerHTML = ''
  let dragSrcIndex = null

  items.forEach((item, idx) => {
    const row = document.createElement('div')
    row.className = 'sc-row'
    // Only the handle starts a drag, so the rename input stays selectable.
    row.draggable = false

    const handle = document.createElement('span')
    handle.className = 'sc-handle'
    handle.textContent = '\\u22ee\\u22ee'
    handle.title = '\\ub4dc\\ub798\\uadf8\\ud558\\uc5ec \\uc21c\\uc11c \\ubcc0\\uacbd'
    handle.addEventListener('mousedown', () => { row.draggable = true })
    handle.addEventListener('mouseup', () => { row.draggable = false })

    const input = document.createElement('input')
    input.className = 'sc-input'
    input.type = 'text'
    input.value = item
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); input.blur() }
      if (e.key === 'Escape') { input.value = item; input.blur() }
    })
    input.addEventListener('blur', () => {
      const next = input.value.trim()
      if (next && next !== item) {
        setTriggerValue('renamed', { old: item, new: next })
      } else {
        input.value = item
      }
    })

    const del = document.createElement('span')
    del.className = 'sc-delete'
    del.textContent = '\\u2715'
    del.title = '\\uc0ad\\uc81c'
    del.onclick = (e) => {
      e.stopPropagation()
      setTriggerValue('deleted', item)
    }

    row.appendChild(handle)
    row.appendChild(input)
    row.appendChild(del)

    row.addEventListener('dragstart', () => {
      dragSrcIndex = idx
      row.classList.add('dragging')
    })
    row.addEventListener('dragend', () => {
      row.classList.remove('dragging')
      row.draggable = false
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

_SUBCATEGORY_DRAG_LIST = st.components.v2.component(
    "subcategory_drag_list",
    html=_SUBCATEGORY_DRAG_LIST_HTML,
    js=_SUBCATEGORY_DRAG_LIST_JS,
)


def subcategory_drag_list(items: list[str], key: str):
    """Render a drag-reorderable, inline-renameable subcategory list.
    Returns the CCv2 result with `.renamed` / `.deleted` (triggers) and
    `.order` (state)."""
    return _SUBCATEGORY_DRAG_LIST(
        key=key,
        data={"items": items},
        default={"order": None},
        on_order_change=lambda: None,
        on_renamed_change=lambda: None,
        on_deleted_change=lambda: None,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _persist():
    """Save both the subcategory list and the keyword tree, surfacing any
    failure instead of letting the change silently live only in memory."""
    if not sheet_store.is_configured():
        return
    for label, saver, payload in (
        ("세부 카테고리", sheet_store.save_subcategories, st.session_state.subcategories),
        ("키워드", sheet_store.save_keywords, st.session_state.keywords),
    ):
        ok, err = saver(payload)
        if not ok:
            st.toast(f"{label} 저장 실패: {err}", icon="⚠️")


def _close_settings():
    st.session_state[SHOW_SETTINGS_KEY] = False


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


@st.dialog("⚙️ 설정 · 키워드 세부 카테고리", width="large", on_dismiss=_close_settings)
def settings_dialog():
    st.caption(
        "세부 카테고리를 추가·수정·삭제할 수 있습니다. "
        "왼쪽 ⋮⋮ 핸들을 끌어 순서를 바꾸면 메인 화면 드롭다운에도 그대로 반영됩니다."
    )

    for category in CATEGORY_OPTIONS:
        st.markdown(f"**{category.replace('■ ', '')}**")

        subs = st.session_state.subcategories.setdefault(category, [])
        category_keywords = st.session_state.keywords.setdefault(category, {})

        if not subs:
            st.caption("등록된 세부 카테고리가 없습니다. 아래에서 추가해주세요.")
        else:
            result = subcategory_drag_list(subs, key=f"scdrag_{category}")

            # --- inline rename ---
            if result.renamed:
                old = (result.renamed or {}).get("old")
                new = (result.renamed or {}).get("new")
                if old in subs and new:
                    if new in subs:
                        st.toast("이미 있는 세부 카테고리입니다.", icon="⚠️")
                    else:
                        subs[subs.index(old)] = new
                        # Keywords filed under the old name move with it.
                        category_keywords[new] = category_keywords.pop(old, [])
                        _persist()
                        st.toast(f"'{old}' → '{new}'로 수정되었습니다.", icon="✅")
                st.rerun(scope="fragment")

            # --- delete ---
            if result.deleted:
                target = result.deleted
                if target in subs:
                    if len(subs) <= 1:
                        st.toast("최소 1개의 세부 카테고리는 남아있어야 합니다.", icon="⚠️")
                    else:
                        remaining = [s for s in subs if s != target]
                        fallback = (
                            DEFAULT_SUBCATEGORY_FALLBACK
                            if DEFAULT_SUBCATEGORY_FALLBACK in remaining
                            else remaining[0]
                        )
                        orphaned = category_keywords.pop(target, [])
                        if orphaned:
                            merged = category_keywords.setdefault(fallback, [])
                            for kw in orphaned:
                                if kw not in merged:
                                    merged.append(kw)
                        subs.remove(target)
                        _persist()
                        if orphaned:
                            st.toast(
                                f"'{target}' 삭제 · 키워드 {len(orphaned)}개는 "
                                f"'{fallback}'(으)로 이동되었습니다.",
                                icon="🗑️",
                            )
                        else:
                            st.toast(f"'{target}'이(가) 삭제되었습니다.", icon="🗑️")
                st.rerun(scope="fragment")

            # --- drag reorder (guarded against stale component state) ---
            if result.order and is_reordering_of(result.order, subs):
                subs[:] = result.order
                _persist()
                st.rerun(scope="fragment")

        with st.form(f"add_subcategory_form_{category}", clear_on_submit=True, border=False):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                new_sub = st.text_input(
                    "새 세부 카테고리",
                    placeholder="새 세부 카테고리 입력",
                    label_visibility="collapsed",
                )
                add_submitted = st.form_submit_button("추가", icon="➕", width="content")
            if add_submitted and new_sub.strip():
                cleaned = new_sub.strip()
                if cleaned in subs:
                    st.toast("이미 있는 세부 카테고리입니다.", icon="⚠️")
                else:
                    subs.append(cleaned)
                    _persist()
                    st.toast(f"'{cleaned}'이(가) 추가되었습니다.", icon="✅")
                st.rerun(scope="fragment")

        st.space("small")

    if not sheet_store.is_configured():
        st.caption(
            "ℹ️ Google Sheets 연동이 설정되지 않아 여기서의 변경 사항은 "
            "이 브라우저 세션에서만 유지되고, 앱을 다시 열면 초기화됩니다."
        )

    if st.button("닫기", width="stretch"):
        _close_settings()
        st.rerun()
