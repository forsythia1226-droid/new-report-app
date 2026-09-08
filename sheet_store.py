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
from datetime import datetime, timedelta

import streamlit as st

WORKSHEET_NAME = "reports"
HEADER = ["date", "title", "items_json"]
RETENTION_DAYS = 180  # ~6 months


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


def purge_old_reports(retention_days: int = RETENTION_DAYS) -> tuple[int, str | None]:
    """Delete saved reports older than `retention_days` (default ~6 months),
    oldest first. Returns (deleted_count, error_message).

    Implementation note: this overwrites the *entire* previously-occupied
    range in a single `update()` call rather than `clear()` + `update()`.
    Two separate calls would leave a window where a crash/network drop
    between them wipes the sheet with nothing written back — a single call
    avoids that failure mode.
    """
    worksheet = _get_worksheet()
    if worksheet is None:
        return 0, None  # nothing to do if Sheets isn't configured

    try:
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return 0, None  # just the header, or empty

        header, rows = all_values[0], all_values[1:]
        cutoff = datetime.now().date() - timedelta(days=retention_days)

        kept = []
        expired = []
        for row in rows:
            date_str = row[0] if row else ""
            try:
                row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                kept.append(row)  # unparseable date: keep rather than risk data loss
                continue
            if row_date < cutoff:
                expired.append(row_date)
            else:
                kept.append(row)

        if not expired:
            return 0, None

        # Overwrite the whole previously-occupied range in one call: kept
        # rows first (oldest deletions leave the newer rows intact), then
        # blank out the now-unused trailing rows so no stale data lingers.
        blank_row = [""] * len(header)
        padded = kept + [blank_row] * (len(rows) - len(kept))
        worksheet.update("A1", [header] + padded)

        load_report_dates.clear()
        load_report_snapshot.clear()
        return len(expired), None
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


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
