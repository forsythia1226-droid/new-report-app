"""
Google Sheets-backed persistence for daily report snapshots, keywords, and
keyword subcategories. Three worksheets in the same spreadsheet:

    reports (date | title | items_json)
        One row per saved day's report. `items_json` is a JSON-encoded dict
        of {category: [{"title": ..., "url": ...}]}, matching the shape of
        st.session_state.report_items.

    keywords (category | subcategory | keywords_json)
        One row per (category, subcategory) pair. `keywords_json` is a
        JSON-encoded list of keyword strings.

    subcategories (category | subcategories_json)
        One row per category. `subcategories_json` is a JSON-encoded list
        of subcategory names, user-editable from the Settings page.

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

KEYWORDS_WORKSHEET_NAME = "keywords"
KEYWORDS_HEADER = ["category", "subcategory", "keywords_json"]
DEFAULT_SUBCATEGORY = "기타"

SUBCATEGORIES_WORKSHEET_NAME = "subcategories"
SUBCATEGORIES_HEADER = ["category", "subcategories_json"]


def _has_secrets() -> bool:
    """Whether the required secrets are present. `st.secrets` itself raises
    if no secrets.toml exists at all (local dev without one, e.g.), so this
    must be exception-safe rather than a plain `in` check."""
    try:
        return "gcp_service_account" in st.secrets and "REPORT_SHEET_ID" in st.secrets
    except Exception:
        return False


def _get_client():
    """Return an authorized gspread client, or None if unconfigured/failed."""
    if not _has_secrets():
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        return gspread.authorize(creds)
    except Exception:
        return None


def _get_or_create_worksheet(name: str, header: list[str]):
    """Return the named worksheet in the configured spreadsheet, creating it
    (with a header row) if it doesn't exist yet. None if unconfigured/failed.

    Also widens an existing worksheet that has fewer columns than `header`
    needs. Without this, a schema that gains a column (as `keywords` did when
    it grew a "subcategory" column) keeps failing to save against the
    narrower grid Google created the first time around.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        import gspread

        spreadsheet = client.open_by_key(st.secrets["REPORT_SHEET_ID"])
        try:
            worksheet = spreadsheet.worksheet(name)
            if worksheet.col_count < len(header):
                worksheet.resize(rows=worksheet.row_count, cols=len(header))
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=name, rows=100, cols=len(header))
            worksheet.append_row(header)
        return worksheet
    except Exception:
        return None


def _ensure_grid_size(worksheet, rows_needed: int, cols_needed: int) -> None:
    """Grow the worksheet if the write about to happen wouldn't fit.

    Google's API rejects (rather than silently truncating) writes that
    exceed the sheet's grid, so a sheet that starts small has to be widened
    or lengthened before a bigger payload can land."""
    new_rows = max(worksheet.row_count, rows_needed)
    new_cols = max(worksheet.col_count, cols_needed)
    if new_rows != worksheet.row_count or new_cols != worksheet.col_count:
        worksheet.resize(rows=new_rows, cols=new_cols)


def _get_worksheet():
    """Return the reports worksheet, or None if Sheets isn't configured."""
    return _get_or_create_worksheet(WORKSHEET_NAME, HEADER)


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
            _ensure_grid_size(worksheet, cell.row, len(HEADER))
            worksheet.update(
                [[date_str, title, items_json]], f"A{cell.row}:C{cell.row}"
            )
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
        payload = [header] + padded
        _ensure_grid_size(worksheet, len(payload), len(header))
        worksheet.update(payload, "A1")

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


def save_keywords(keywords: dict) -> tuple[bool, str | None]:
    """Persist the full category -> {subcategory -> [keyword, ...]} mapping.

    Overwrites the whole keywords sheet in a single update() call (same
    single-call rationale as `purge_old_reports`: no separate clear() step
    that could lose data if interrupted mid-way).
    """
    worksheet = _get_or_create_worksheet(KEYWORDS_WORKSHEET_NAME, KEYWORDS_HEADER)
    if worksheet is None:
        return False, "Google Sheets 연동이 설정되지 않았습니다."

    try:
        rows = []
        for category, subs in keywords.items():
            for subcategory, kw_list in subs.items():
                rows.append([category, subcategory, json.dumps(kw_list, ensure_ascii=False)])

        payload = [KEYWORDS_HEADER] + rows
        # Blank out any rows left over from a previous, longer save so
        # deleted subcategories don't linger in the sheet.
        existing_row_count = len(worksheet.get_all_values())
        if existing_row_count > len(payload):
            payload += [[""] * len(KEYWORDS_HEADER)] * (existing_row_count - len(payload))

        _ensure_grid_size(worksheet, len(payload), len(KEYWORDS_HEADER))
        worksheet.update(payload, "A1")
        load_keywords.clear()
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


@st.cache_data(ttl=60, show_spinner=False)
def load_keywords() -> dict | None:
    """Load the saved category -> {subcategory -> [keyword, ...]} mapping, or
    None if nothing has been saved yet (caller should fall back to defaults).

    Transparently migrates the older 2-column schema (category,
    keywords_json — a flat list with no subcategory) by bucketing those
    keywords under the catch-all `DEFAULT_SUBCATEGORY` ("기타").
    """
    worksheet = _get_or_create_worksheet(KEYWORDS_WORKSHEET_NAME, KEYWORDS_HEADER)
    if worksheet is None:
        return None

    try:
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return None  # only the header (or empty): nothing saved yet

        header, rows = all_values[0], all_values[1:]
        is_legacy_flat_schema = len(header) < 3

        result: dict = {}
        for row in rows:
            if not row or not row[0]:
                continue
            category = row[0]

            if is_legacy_flat_schema:
                subcategory = DEFAULT_SUBCATEGORY
                kw_json = row[1] if len(row) > 1 else "[]"
            else:
                subcategory = row[1] if len(row) > 1 and row[1] else DEFAULT_SUBCATEGORY
                kw_json = row[2] if len(row) > 2 else "[]"

            try:
                kw_list = json.loads(kw_json)
            except json.JSONDecodeError:
                kw_list = []

            result.setdefault(category, {})[subcategory] = kw_list

        return result or None
    except Exception:
        return None


def save_subcategories(subcategories: dict) -> tuple[bool, str | None]:
    """Persist the full category -> [subcategory, ...] mapping."""
    worksheet = _get_or_create_worksheet(SUBCATEGORIES_WORKSHEET_NAME, SUBCATEGORIES_HEADER)
    if worksheet is None:
        return False, "Google Sheets 연동이 설정되지 않았습니다."

    try:
        rows = [
            [category, json.dumps(subs, ensure_ascii=False)]
            for category, subs in subcategories.items()
        ]
        payload = [SUBCATEGORIES_HEADER] + rows
        _ensure_grid_size(worksheet, len(payload), len(SUBCATEGORIES_HEADER))
        worksheet.update(payload, "A1")
        load_subcategories.clear()
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


@st.cache_data(ttl=60, show_spinner=False)
def load_subcategories() -> dict | None:
    """Load the saved category -> [subcategory, ...] mapping, or None if
    nothing has been saved yet (caller should fall back to defaults)."""
    worksheet = _get_or_create_worksheet(SUBCATEGORIES_WORKSHEET_NAME, SUBCATEGORIES_HEADER)
    if worksheet is None:
        return None

    try:
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return None

        result = {}
        for row in all_values[1:]:
            if not row or not row[0]:
                continue
            category = row[0]
            subs_json = row[1] if len(row) > 1 else "[]"
            try:
                result[category] = json.loads(subs_json)
            except json.JSONDecodeError:
                result[category] = []
        return result or None
    except Exception:
        return None
