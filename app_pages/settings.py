"""
Settings page - manage the keyword subcategory dropdown options shown next
to each top-level category on the main page (e.g. "기업" / "산업" /
"해저케이블" / "기타" under 전선산업 주요 기사).

Add / rename / delete a subcategory here. Keywords already filed under a
renamed subcategory move with it; keywords under a deleted subcategory are
moved to another remaining subcategory (preferring "기타") rather than
being discarded.
"""

import streamlit as st

import sheet_store
import app_common
from app_common import CATEGORY_OPTIONS, DEFAULT_SUBCATEGORY_FALLBACK, section_title

app_common.inject_global_css()

with st.container(key="app_header"):
    st.html(
        '<div class="app-header-title">⚙️ 설정</div>'
        '<div class="app-header-caption">'
        "키워드 세부 카테고리(드롭박스 항목)를 추가·수정·삭제합니다. 변경 사항은 즉시 저장됩니다."
        "</div>"
    )

st.space("small")


def _persist():
    sheet_store.save_subcategories(st.session_state.subcategories)
    sheet_store.save_keywords(st.session_state.keywords)


for category in CATEGORY_OPTIONS:
    with st.container(border=True):
        section_title("🏷️", category.replace("■ ", ""))

        subs = st.session_state.subcategories.setdefault(category, [])
        category_keywords = st.session_state.keywords.setdefault(category, {})

        if not subs:
            st.caption("등록된 세부 카테고리가 없습니다. 아래에서 추가해주세요.")

        for i, sub in enumerate(subs):
            row = st.columns([3, 1, 1], vertical_alignment="bottom")
            with row[0]:
                new_name = st.text_input(
                    "이름",
                    value=sub,
                    key=f"sub_name_{category}_{i}",
                    label_visibility="collapsed",
                )
            with row[1]:
                if st.button("수정", key=f"sub_rename_{category}_{i}", width="stretch"):
                    cleaned = new_name.strip()
                    if not cleaned:
                        st.warning("이름을 입력해주세요.", icon="⚠️")
                    elif cleaned != sub and cleaned in subs:
                        st.warning("이미 있는 세부 카테고리입니다.", icon="⚠️")
                    elif cleaned != sub:
                        subs[i] = cleaned
                        # Keywords filed under the old name move with it.
                        category_keywords[cleaned] = category_keywords.pop(sub, [])
                        _persist()
                        st.toast(f"'{sub}' → '{cleaned}'로 수정되었습니다.", icon="✅")
                        st.rerun()
            with row[2]:
                if st.button("삭제", key=f"sub_delete_{category}_{i}", width="stretch"):
                    if len(subs) <= 1:
                        st.warning(
                            "최소 1개의 세부 카테고리는 남아있어야 합니다.", icon="⚠️"
                        )
                    else:
                        remaining = [s for s in subs if s != sub]
                        fallback = (
                            DEFAULT_SUBCATEGORY_FALLBACK
                            if DEFAULT_SUBCATEGORY_FALLBACK in remaining
                            else remaining[0]
                        )
                        orphaned_keywords = category_keywords.pop(sub, [])
                        if orphaned_keywords:
                            merged = category_keywords.setdefault(fallback, [])
                            for kw in orphaned_keywords:
                                if kw not in merged:
                                    merged.append(kw)
                        subs.remove(sub)
                        _persist()
                        if orphaned_keywords:
                            st.toast(
                                f"'{sub}' 삭제 · 키워드 {len(orphaned_keywords)}개는 "
                                f"'{fallback}'(으)로 이동되었습니다.",
                                icon="🗑️",
                            )
                        else:
                            st.toast(f"'{sub}'이(가) 삭제되었습니다.", icon="🗑️")
                        st.rerun()

        st.space("small")

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
                    st.warning("이미 있는 세부 카테고리입니다.", icon="⚠️")
                else:
                    subs.append(cleaned)
                    _persist()
                    st.toast(f"'{cleaned}'이(가) 추가되었습니다.", icon="✅")
                    st.rerun()

    st.space("small")

if not sheet_store.is_configured():
    st.caption(
        "ℹ️ Google Sheets 연동이 설정되지 않아 여기서의 변경 사항은 "
        "이 브라우저 세션에서만 유지되고, 앱을 다시 열면 초기화됩니다."
    )
