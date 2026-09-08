"""
[대한전선] 일일현안 보고 — Streamlit 앱.

레이아웃은 같은 저장소의 뉴스 리포트 앱(`app.py`)과 같은 톤앤매너입니다:
상단 헤더 카드 + 좌측 남색 조직 패널 + 가운데 입력 + 우측 결과 카드.

- 각 팀 담당자: 좌측에서 대부문/팀 선택 후 현안 입력 → 저장소에 즉시 저장
- 경영기획팀: 오늘 데이터를 Claude 로 통합 가공 → 프리뷰 + 다운로드
- 보관 정책: 작성일시 기준 48시간 경과 행은 자동/수동 삭제

실행:
    streamlit run issue_app.py                    # 운영 (Google Sheets)
    DEMO_MODE=true streamlit run issue_app.py     # 시연 (로컬 JSON)
"""

from datetime import datetime, timedelta

import streamlit as st

import env_bootstrap

env_bootstrap.bootstrap()  # config 를 import 하기 전에 .env / Secrets 를 읽는다

import config  # noqa: E402
import demo_store  # noqa: E402
import issue_store  # noqa: E402
import org_store  # noqa: E402
import report_generator  # noqa: E402
import ui_theme  # noqa: E402
from sheets_core import parse_timestamp  # noqa: E402

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ui_theme.inject_css()

section_title = ui_theme.section_title


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------
def _flash(ok: bool, message: str, reset_selection: bool = False) -> None:
    """작업 결과를 다음 실행에 표시하고 화면을 새로 그린다."""
    st.session_state.org_flash = ("success" if ok else "error", message)
    if ok and reset_selection:
        # 삭제된 부문/팀이 선택 상태로 남아 있으면 안 되므로 초기화
        st.session_state.pop("selected_division", None)
        st.session_state.pop("selected_team", None)
    st.rerun()


def _remaining_label(timestamp: str) -> str:
    """작성일시로부터 남은 보관 시간을 사람이 읽는 문자열로."""
    written_at = parse_timestamp(timestamp)
    if written_at is None:
        return "판독 불가 (보존)"

    remaining = written_at + timedelta(hours=config.RETENTION_HOURS) - datetime.now()
    if remaining.total_seconds() <= 0:
        return "만료 (삭제 대상)"

    hours, seconds = divmod(int(remaining.total_seconds()), 3600)
    return f"{hours}시간 {seconds // 60}분 남음"


def _current_selection(organization: dict[str, list[str]]) -> tuple[str, str]:
    """세션에 저장된 대부문/팀 선택값을 조직도와 대조해 정리한 뒤 반환."""
    divisions = list(organization.keys())
    division = st.session_state.get("selected_division")
    if division not in organization:
        division = divisions[0] if divisions else ""
        st.session_state.selected_division = division

    teams = organization.get(division, [])
    team = st.session_state.get("selected_team")
    if team not in teams:
        team = teams[0] if teams else ""
        st.session_state.selected_team = team

    return division, team


# ---------------------------------------------------------------------------
# 헤더
# ---------------------------------------------------------------------------
def render_header(all_records: list[dict]) -> str:
    """헤더 카드를 그리고 선택된 조회 날짜를 반환."""
    today = datetime.now().strftime(config.DATE_FORMAT)

    with st.container(key="app_header"):
        col_title, col_date = st.columns([3, 1], vertical_alignment="center")
        with col_title:
            st.html(
                f'<div class="app-header-title">📋 {config.APP_TITLE}</div>'
                '<div class="app-header-caption">'
                "각 부문·팀이 일일 현안을 등록하면, 경영기획팀이 통합 보고서로 가공합니다."
                "</div>"
            )
        with col_date:
            with st.container(key="header_date_picker"):
                saved = {r.get("날짜", "") for r in all_records if r.get("날짜")}
                options = sorted({today, *saved}, reverse=True)

                def _format(d: str) -> str:
                    label = d.replace("-", ".")
                    return f"📅 {label} (오늘)" if d == today else f"📅 {label}"

                return st.selectbox(
                    "조회 날짜",
                    options,
                    key="viewing_date",
                    format_func=_format,
                    label_visibility="collapsed",
                )


# ---------------------------------------------------------------------------
# 좌측 — 조직 패널 (남색)
# ---------------------------------------------------------------------------
def render_org_panel(organization: dict[str, list[str]]) -> tuple[str, str]:
    with st.container(key="org_panel"):
        flash = st.session_state.pop("org_flash", None)
        if flash:
            level, message = flash
            (st.success if level == "success" else st.error)(message)

        section_title("🏢", "조직 선택")

        divisions = list(organization.keys())
        division = st.selectbox(
            "대부문",
            divisions,
            key="selected_division",
            label_visibility="visible",
        )

        teams = organization.get(division, [])
        section_title("👥", "팀 목록", len(teams))

        selected_team = st.session_state.get("selected_team")
        if selected_team not in teams:
            selected_team = teams[0] if teams else ""
            st.session_state.selected_team = selected_team

        for index, team in enumerate(teams):
            with st.container(key=f"teamrow_{division}_{index}"):
                col_name, col_delete = st.columns([5, 1], vertical_alignment="center")
                with col_name:
                    if st.button(
                        team,
                        key=f"pick_{division}_{index}",
                        width="stretch",
                        type="primary" if team == selected_team else "secondary",
                    ):
                        st.session_state.selected_team = team
                        st.rerun()
                with col_delete:
                    if st.button(
                        "🗑️",
                        key=f"del_{division}_{index}",
                        width="stretch",
                        help=f"'{team}' 삭제",
                    ):
                        ok, message = org_store.remove_team(division, team)
                        _flash(ok, message, reset_selection=True)

        if not teams:
            st.caption("등록된 팀이 없습니다. 아래에서 팀을 추가해 주세요.")

        col_input, col_add = st.columns([3, 1], vertical_alignment="bottom")
        with col_input:
            new_team = st.text_input(
                "새 팀 입력",
                key="new_team_name",
                placeholder="새 팀 입력",
                label_visibility="collapsed",
            )
        with col_add:
            if st.button("➕ 추가", key="btn_add_team", width="stretch"):
                ok, message = org_store.add_team(division, new_team)
                _flash(ok, message)

        st.divider()
        render_division_editor(organization)
        render_status_footer()

    return division, st.session_state.get("selected_team", "")


def render_division_editor(organization: dict[str, list[str]]) -> None:
    """대부문 자체를 추가·삭제하는 접이식 영역."""
    with st.expander("⚙️ 대부문 관리"):
        new_division = st.text_input(
            "새 대부문 입력",
            key="new_division_name",
            placeholder="새 대부문 입력",
            label_visibility="collapsed",
        )
        if st.button("➕ 대부문 추가", key="btn_add_div", width="stretch"):
            ok, message = org_store.add_division(new_division)
            _flash(ok, message)

        target = st.selectbox(
            "삭제할 대부문",
            list(organization.keys()),
            key="del_div_select",
            label_visibility="collapsed",
        )
        if st.button("🗑️ 대부문 삭제", key="btn_del_div", width="stretch"):
            ok, message = org_store.remove_division(target)
            _flash(ok, message, reset_selection=True)

        if st.button("↩️ 기본 조직도로 초기화", key="btn_reset_org", width="stretch"):
            org_store.reset_to_default()
            _flash(True, "기본 조직도로 되돌렸습니다.", reset_selection=True)

        st.caption("팀을 삭제해도 이미 제출된 과거 데이터는 사라지지 않습니다.")


def render_status_footer() -> None:
    st.divider()
    st.caption(
        f"🗑️ 보관 정책: 제출된 현안은 작성일시 기준 "
        f"{config.RETENTION_HOURS}시간 후 자동 삭제됩니다."
    )

    connected, message = issue_store.is_configured()
    if connected:
        st.success(message)
    else:
        st.error(message)

    if config.DEMO_MODE:
        st.divider()
        st.caption(f"🧪 시연 도구 · `{config.DEMO_DATA_FILE}`")
        if st.button("샘플 데이터 채우기", key="btn_seed", width="stretch"):
            fresh, expired = demo_store.seed_sample_data()
            issue_store.load_records.clear()
            _flash(True, f"오늘 {fresh}건 + 만료 {expired}건을 넣었습니다.")
        if st.button("데모 데이터 전체 삭제", key="btn_wipe", width="stretch"):
            demo_store.reset()
            issue_store.load_records.clear()
            st.session_state.pop("report_text", None)
            _flash(True, "데모 데이터를 비웠습니다.")


# ---------------------------------------------------------------------------
# 가운데 — 현안 입력
# ---------------------------------------------------------------------------
def render_submit(division: str, team: str, viewing_date: str, records: list[dict]) -> None:
    today = datetime.now().strftime(config.DATE_FORMAT)

    with st.container(key="panel_submit"):
        section_title("📝", f"{division} › {team}" if team else division)

        if not team:
            ui_theme.empty_state(
                "좌측 패널에서 팀을 추가하거나 선택해 주세요."
            )
            return

        if viewing_date != today:
            st.info(
                f"과거 날짜({viewing_date})를 조회 중입니다. "
                "새 현안 입력은 오늘 날짜에서만 가능합니다.",
                icon="🔎",
            )
        else:
            with st.form("issue_form", clear_on_submit=True):
                author = st.text_input("작성자 이름", placeholder="예: 홍길동")
                content = st.text_area(
                    "일일 주요 현안 내용",
                    height=200,
                    placeholder="- 주요 진행 사항\n- 이슈 및 리스크\n- 지원 요청 사항",
                )
                submitted = st.form_submit_button("현안 제출", type="primary")

            if submitted:
                if not author.strip():
                    st.warning("작성자 이름을 입력해 주세요.")
                elif not content.strip():
                    st.warning("현안 내용을 입력해 주세요.")
                else:
                    with st.spinner("저장 중..."):
                        ok, err = issue_store.submit_issue(
                            division, team, author.strip(), content.strip()
                        )
                    if ok:
                        st.success(
                            f"제출 완료 — {config.RETENTION_HOURS}시간 후 자동 삭제됩니다."
                        )
                        st.rerun()
                    else:
                        st.error(f"저장 실패: {err}")

    team_records = [
        r
        for r in records
        if r.get("날짜") == viewing_date
        and r.get("대부문") == division
        and r.get("팀명") == team
    ]

    with st.container(key="panel_team_history"):
        section_title("🗂️", f"{team} 제출 내역", len(team_records))
        if not team_records:
            ui_theme.empty_state("아직 등록된 현안이 없습니다.")
            return

        for index, record in enumerate(team_records):
            with st.container(key=f"issuecard_{index}"):
                st.html(
                    '<div class="issue-meta">'
                    f"{record.get('작성일시', '')} · {record.get('작성자', '')}"
                    "</div>"
                )
                st.write(record.get("일일현안내용", ""))


# ---------------------------------------------------------------------------
# 우측 — 전사 현황 / 경영기획팀 보고서
# ---------------------------------------------------------------------------
def render_overview(viewing_date: str, records: list[dict]) -> None:
    day_records = [r for r in records if r.get("날짜") == viewing_date]

    with st.container(key="panel_overview"):
        section_title("📊", "전사 제출 현황", len(day_records))
        if not day_records:
            ui_theme.empty_state("해당 날짜에 등록된 현안이 없습니다.")
            return

        by_division: dict[str, list[str]] = {}
        for record in day_records:
            by_division.setdefault(record.get("대부문", "미분류"), []).append(
                record.get("팀명", "")
            )

        for division, teams in by_division.items():
            st.html(f'<span class="category-chip">{division} · {len(teams)}건</span>')
            st.caption(", ".join(sorted(set(t for t in teams if t))))


def render_report_panel(viewing_date: str, records: list[dict]) -> None:
    today = datetime.now().strftime(config.DATE_FORMAT)
    day_records = [r for r in records if r.get("날짜") == viewing_date]

    with st.container(key="panel_report"):
        section_title("📋", "통합 보고서", len(day_records))

        if st.button(
            f"📄 {viewing_date} 통합 보고서 생성",
            type="primary",
            width="stretch",
        ):
            if not day_records:
                st.warning("해당 날짜에 제출된 현안이 없습니다.")
            else:
                with st.spinner("Claude 가 보고서를 작성하는 중입니다..."):
                    report, err = report_generator.generate_report(
                        day_records, viewing_date
                    )
                if err:
                    st.error(err)
                else:
                    st.session_state.report_text = report
                    st.session_state.report_date = viewing_date
                    st.rerun()

        report = st.session_state.get("report_text")
        if not report:
            ui_theme.empty_state("보고서를 생성하면 이곳에 표시됩니다.")
            return

        report_date = st.session_state.get("report_date", today)
        with st.container(height=380, border=True):
            st.markdown(report)

        col_md, col_txt = st.columns(2)
        with col_md:
            st.download_button(
                "⬇️ .md 저장",
                data=report,
                file_name=f"일일현안보고서_{report_date}.md",
                mime="text/markdown",
                width="stretch",
            )
        with col_txt:
            st.download_button(
                "⬇️ .txt 저장",
                data=report,
                file_name=f"일일현안보고서_{report_date}.txt",
                mime="text/plain",
                width="stretch",
            )


def render_retention_panel(records: list[dict]) -> None:
    rows = [
        {
            "작성일시": r.get("작성일시", ""),
            "대부문": r.get("대부문", ""),
            "팀명": r.get("팀명", ""),
            "작성자": r.get("작성자", ""),
            "보관 상태": _remaining_label(r.get("작성일시", "")),
        }
        for r in sorted(records, key=lambda r: r.get("작성일시", ""), reverse=True)
    ]
    expired_count = sum(1 for r in rows if r["보관 상태"].startswith("만료"))

    with st.container(key="panel_retention"):
        section_title("🗑️", "데이터 보관 현황")

        col_total, col_expired = st.columns(2)
        col_total.metric("전체 보관 행", f"{len(records)}행")
        col_expired.metric("삭제 대상", f"{expired_count}행")

        if st.button(
            f"{config.RETENTION_HOURS}시간 경과 데이터 수동 정리",
            width="stretch",
        ):
            with st.spinner("정리 중..."):
                deleted, err = issue_store.purge_expired_rows()
            if err:
                st.error(f"정리 실패: {err}")
            elif deleted:
                st.success(f"{deleted}개 행을 삭제했습니다.")
                st.rerun()
            else:
                st.info("삭제할 만료 데이터가 없습니다.")

        if rows:
            st.dataframe(rows, width="stretch", hide_index=True, height=240)

        st.caption(
            "접속과 무관한 정시 삭제는 `purge_job.py` 를 스케줄러에 등록하면 됩니다."
        )


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    # 앱 로드 시 만료 데이터 정리 (10분 버킷 캐시로 호출 빈도 제한)
    purged = issue_store.run_auto_purge()

    organization = org_store.load_organization()
    _current_selection(organization)
    records = issue_store.load_records()

    viewing_date = render_header(records)
    if purged:
        st.toast(f"보관 기한이 지난 {purged}개 행을 자동 삭제했습니다.")
    if config.DEMO_MODE:
        st.info(
            "🧪 **데모 모드** — Google Sheets 대신 로컬 파일을 사용합니다. "
            "삭제 정책과 화면 흐름은 운영과 동일합니다.",
            icon="🧪",
        )

    left_col, center_col, right_col = st.columns([1, 2, 1.5])

    with left_col:
        division, team = render_org_panel(organization)

    with center_col:
        render_submit(division, team, viewing_date, records)

    with right_col:
        is_admin = team == config.ADMIN_TEAM and division == config.ADMIN_DIVISION
        if is_admin:
            render_report_panel(viewing_date, records)
            render_retention_panel(records)
        else:
            render_overview(viewing_date, records)
            st.caption(
                f"통합 보고서 생성은 {config.ADMIN_DIVISION} › {config.ADMIN_TEAM} "
                "선택 시 이용할 수 있습니다."
            )


if __name__ == "__main__":
    main()
