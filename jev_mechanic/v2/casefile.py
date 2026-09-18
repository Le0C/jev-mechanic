"""Select the relevant entries of a case file, and build the evidence state for Jev."""

from __future__ import annotations

import calendar
import copy
from datetime import date as Date

CLEARED_MAX_KM = 5000
SERVICE_MAX_MONTHS = 24
SERVICE_KEEP_LAST = 3

REPORT = "report"
CASE_FILE = "case_file"
MODES = (REPORT, CASE_FILE)

CASE_FILE_SOURCES = ("obd_codes", "freeze_frame", "service_history", "technician_notes", "vehicle")


def _months_before(day: Date, months: int) -> Date:
    """Return the date `months` calendar months before `day`, clamped to the month end."""
    index = day.year * 12 + day.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    return Date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _months_between(earlier: Date, later: Date) -> int:
    months = (later.year - earlier.year) * 12 + later.month - earlier.month
    return months - 1 if later.day < earlier.day else months


def filter_case_file(case_file: dict, date: str) -> tuple[dict, list[dict]]:
    """Return the case file without its old entries, and a list of the removed entries.

    A cleared code more than 5,000 km before the current mileage goes. A service entry
    more than 24 months before `date` goes, but the last 3 service entries stay.
    """
    kept = copy.deepcopy(case_file)
    removed: list[dict] = []

    mileage = (case_file.get("vehicle") or {}).get("mileage_km")
    codes = []
    for code in kept.get("obd_codes") or []:
        at = code.get("mileage_km")
        if code.get("status") == "cleared" and mileage is not None and at is not None and mileage - at > CLEARED_MAX_KM:
            removed.append({"source": "obd_codes", "entry": code, "reason": f"cleared {mileage - at:,} km ago"})
        else:
            codes.append(code)
    if "obd_codes" in kept:
        kept["obd_codes"] = codes

    history = kept.get("service_history") or []
    newest = sorted(range(len(history)), key=lambda i: history[i].get("date", ""))[-SERVICE_KEEP_LAST:]
    case_day = Date.fromisoformat(date)
    cutoff = _months_before(case_day, SERVICE_MAX_MONTHS)
    entries = []
    for i, entry in enumerate(history):
        day = Date.fromisoformat(entry["date"]) if entry.get("date") else None
        if i not in newest and day is not None and day < cutoff:
            reason = f"{_months_between(day, case_day)} months before the case date"
            removed.append({"source": "service_history", "entry": entry, "reason": reason})
        else:
            entries.append(entry)
    if "service_history" in kept:
        kept["service_history"] = entries
    return kept, removed


def evidence_state(mode: str, report: str, case_file: dict | None) -> dict:
    """Return the Jev state: the report only, or the report plus the five case file sources."""
    if mode == REPORT:
        return {"customer_report": report}
    if mode != CASE_FILE:
        raise ValueError(f"unknown mode {mode!r}, use one of {', '.join(MODES)}")
    if case_file is None:
        raise ValueError("the mode case_file needs a case file")
    state: dict = {"customer_report": report}
    for source in CASE_FILE_SOURCES:
        empty: dict | list = {} if source in ("freeze_frame", "vehicle") else []
        state[source] = copy.deepcopy(case_file.get(source, empty))
    return state
