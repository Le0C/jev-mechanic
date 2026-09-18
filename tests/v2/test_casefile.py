import copy

import pytest
from v2_helpers import CASE_FILE

from jev_mechanic.v2.casefile import evidence_state, filter_case_file

DATE = "2026-09-01"


def test_filter_removes_an_old_cleared_code_only():
    kept, removed = filter_case_file(CASE_FILE, DATE)
    codes = [c["code"] for c in kept["obd_codes"]]
    assert codes == ["P0562", "P0300"]
    old = [r for r in removed if r["source"] == "obd_codes"]
    assert old == [{"source": "obd_codes", "entry": CASE_FILE["obd_codes"][1], "reason": "cleared 12,000 km ago"}]


def test_filter_keeps_the_last_three_service_entries():
    kept, removed = filter_case_file(CASE_FILE, DATE)
    assert [e["date"] for e in kept["service_history"]] == ["2021-05-20", "2023-06-11", "2025-11-02"]
    gone = [r for r in removed if r["source"] == "service_history"]
    assert [r["entry"]["date"] for r in gone] == ["2019-03-10", "2020-04-02"]
    assert gone[0]["reason"] == "89 months before the case date"


def test_filter_keeps_a_recent_service_entry_that_is_not_in_the_last_three():
    history = [
        {"date": "2025-01-10", "work": "Tyres"},
        {"date": "2025-03-10", "work": "Wipers"},
        {"date": "2025-06-10", "work": "Oil"},
        {"date": "2026-01-10", "work": "Oil"},
        {"date": "2019-01-10", "work": "Oil"},
    ]
    kept, removed = filter_case_file({"service_history": history}, DATE)
    assert len(kept["service_history"]) == 4
    assert [r["entry"]["date"] for r in removed] == ["2019-01-10"]


def test_filter_does_not_change_its_input():
    before = copy.deepcopy(CASE_FILE)
    filter_case_file(CASE_FILE, DATE)
    assert CASE_FILE == before


def test_evidence_state_report_mode():
    assert evidence_state("report", "It will not start.", CASE_FILE) == {"customer_report": "It will not start."}


def test_evidence_state_case_file_mode():
    state = evidence_state("case_file", "It will not start.", CASE_FILE)
    assert list(state) == [
        "customer_report", "obd_codes", "freeze_frame", "service_history", "technician_notes", "vehicle",
    ]
    assert state["freeze_frame"] == CASE_FILE["freeze_frame"]


def test_evidence_state_rejects_a_bad_mode():
    with pytest.raises(ValueError):
        evidence_state("logs", "x", None)
    with pytest.raises(ValueError):
        evidence_state("case_file", "x", None)
