"""
Google Sheets-backed persistence for daily report snapshots.

Each row in the sheet represents one saved day's report:
    date (YYYY-MM-DD) | title | items_json

`items_json` is a JSON-encoded dict of {category: [{"title": ..., "url": ...}]},
matching the shape of st.session_state.report_items.

Reads credentials from Streamlit secrets:
    st.secrets["gcp_service_account"]  -> the service account JSON, as a dict
    st.secrets["REPORT_SHEET_ID"]      -> the target spreadsheet's ID
    (the spreadsheet can belong to any Google account — personal or a
    company Workspace account — as long as it's shared with the service
    account's client_email as an Editor)

If those secrets are missing, every function degrades gracefully (returns
empty/None) so the rest of the app keeps working without this feature.
"""

import json

import streamlit as st

WORKSHEET_NAME = "reports"
HEADER = ["date", "title", "items_json"]


def _has_secrets() -> bool:
    """Whether the required secrets are present. `st.secrets` itself raises
    if no secrets.toml exists at all (local dev without one, e.g.), so this
    must be exception-safe rather than a plain `in` check."""
    try:
        return "gcp_service_account" in st.secrets and "REPORT_SHEET_ID" in st.secrets
    except Exception:
        return False


def _get_worksheet():
    """Return the reports worksheet, or None if Sheets isn't configured."""
    if not _has_secrets():
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(st.secrets["REPORT_SHEET_ID"])

        try:
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=WORKSHEET_NAME, rows=100, cols=len(HEADER)
            )
            worksheet.append_row(HEADER)

        return worksheet
    except Exception:
        return None


def is_configured() -> bool:
    """Whether Google Sheets persistence is set up (secrets present)."""
    return _has_secrets()


def save_report_snapshot(date_str: str, title: str, report_items: dict) -> tuple[bool, str | None]:
    """Save (or overwrite) the report for `date_str`.

    Returns (success, error_message).
    """
    worksheet = _get_worksheet()
    if worksheet is None:
        return False, "Google Sheets 연동이 설정되지 않았습니다."

    try:
        items_json = json.dumps(report_items, ensure_ascii=False)
        cell = worksheet.find(date_str, in_column=1)
        if cell:
            worksheet.update(f"A{cell.row}:C{cell.row}", [[date_str, title, items_json]])
        else:
            worksheet.append_row([date_str, title, items_json])
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


@st.cache_data(ttl=60, show_spinner=False)
def load_report_dates() -> list[str]:
    """Return all saved dates, most recent first.

    Cached for 60s: this is read on every script rerun (it feeds the header
    date dropdown), and every rerun happens on almost every click — without
    caching, that's a Google Sheets API round-trip on every single
    interaction, which made the whole app feel sluggish. Cleared manually
    right after a successful save so the new date shows up immediately.
    """
    worksheet = _get_worksheet()
    if worksheet is None:
        return []

    try:
        records = worksheet.col_values(1)[1:]  # skip header
        return sorted({d for d in records if d}, reverse=True)
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def load_report_snapshot(date_str: str) -> tuple[str, dict] | None:
    """Load the saved (title, report_items) for `date_str`, or None.

    Cached for 60s for the same reason as `load_report_dates` — this is
    re-read on every rerun while viewing a past date.
    """
    worksheet = _get_worksheet()
    if worksheet is None:
        return None

    try:
        cell = worksheet.find(date_str, in_column=1)
        if not cell:
            return None
        row = worksheet.row_values(cell.row)
        title = row[1] if len(row) > 1 else ""
        items_json = row[2] if len(row) > 2 else "{}"
        return title, json.loads(items_json)
    except Exception:
        return None
