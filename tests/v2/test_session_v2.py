import time

import pytest
from v2_helpers import CASE_FILE, mini_model, mini_raw, model_from, noul, script, sure

from jev_mechanic.jev import FakeJev, make_choice
from jev_mechanic.v2.session import Session, SessionError

REPORT = "Slow to start, and the battery light comes on."

VIEW_KEYS = {
    "id", "version", "mode", "status", "evidence", "symptoms", "components", "loop", "current",
    "confirm_options", "steps", "branch_scores", "flag", "faults", "fix", "unexplained",
    "independent", "path", "mermaid", "ledger",
}

CASCADE = dict(
    symptoms=("slow_crank", "battery_light", "dim_lights"),
    components={"battery": 0.9, "charge": 0.8},
)


def started(jev: FakeJev, model=None, mode="report", **kwargs) -> Session:
    session = Session(model or mini_model(), jev, mode, REPORT, **kwargs)
    session.start()
    return session


def kinds(session: Session) -> list[tuple[int, str]]:
    return [(r["step"], r["kind"]) for r in session.view()["ledger"]["rows"]]


def four_component_model():
    """Return the mini model with a fourth component, the brakes."""
    raw = mini_raw()
    raw["systems"]["brakes"] = {"label": "Brakes", "description": "Pads and discs", "entry": "q_brk_pads"}
    raw["symptoms"]["brake_noise"] = {"label": "Brake noise", "description": "A grind when the driver brakes"}
    raw["diagnoses"]["worn_pads"] = {
        "label": "Worn pads", "description": "The brake pads are worn", "systems": ["brakes"], "prior": 0.2,
        "explains": ["brake_noise"], "causes": [],
        "fix": ["Measure the pads.", "Replace the pads.", "Do a brake test."],
    }
    raw["nodes"]["q_brk_pads"] = {
        "question": "Are the pads less than 3 mm thick?",
        "options": {"yes": {"text": "Yes", "next": "worn_pads"}, "no": {"text": "No", "next": "specialist"}},
        "evidence": {"yes": {"worn_pads": 0.9}, "no": {"worn_pads": 0.1}},
    }
    return model_from(raw)


def test_start_selects_the_best_component_and_asks_its_entry():
    session = started(FakeJev(script(**CASCADE)))
    view = session.view()
    assert set(view) == VIEW_KEYS
    assert view["version"] == 2 and view["mode"] == "report"
    assert view["status"] == "asking"
    assert view["loop"] == {"index": 1, "component": "battery"}
    assert view["current"]["node_id"] == "q_bat_voltage"
    present = {s["id"] for s in view["symptoms"] if s["present"]}
    assert present == {"slow_crank", "battery_light", "dim_lights"}
    states = {c["id"]: c["state"] for c in view["components"]}
    assert states == {"battery": "active", "charge": "open", "cooling": "open"}
    scores = {c["id"]: c["score"] for c in view["components"]}
    assert scores["charge"] == pytest.approx(0.8 * 2)
    assert scores["cooling"] is None
    assert kinds(session) == [(0, "E"), (0, "C"), (1, "A")]


def test_two_fault_cascade_puts_the_alternator_first():
    jev = FakeJev(script(**CASCADE, answer=[sure("low"), sure("low"), sure("no")]))
    session = started(jev)
    session.answer("11.8 volts")
    view = session.view()
    assert view["loop"] == {"index": 2, "component": "charge"}
    charge = next(c for c in view["components"] if c["id"] == "charge")
    assert charge["state"] == "active"
    session.answer("12.9 V at 2000 rpm")
    session.answer("the belt is tight and quiet")
    view = session.view()
    assert view["status"] == "complete"
    assert [f["id"] for f in view["faults"]] == ["flat_battery", "alternator_failure"]
    assert view["faults"][0]["explains"] == ["slow_crank", "dim_lights"]
    assert view["faults"][0]["caused_by_found"] == ["alternator_failure"]
    assert view["faults"][1]["explains"] == ["battery_light"]
    assert [f["diagnosis"] for f in view["fix"]] == ["alternator_failure", "flat_battery"]
    assert view["fix"][0]["steps"][0] == "Measure the charge voltage."
    assert view["unexplained"] == []
    assert view["current"] is None
    explained = {s["id"]: s["explained_by"] for s in view["symptoms"] if s["present"]}
    assert explained == {"slow_crank": "flat_battery", "battery_light": "alternator_failure",
                         "dim_lights": "flat_battery"}
    assert kinds(session) == [(0, "E"), (0, "C"), (1, "A"), (2, "B"), (2, "C"), (3, "A"),
                              (4, "B"), (4, "C"), (5, "B"), (5, "C")]
    assert [(s["loop"], s["component"]) for s in view["steps"]] == [(1, "battery"), (2, "charge"), (2, "charge")]


def test_a_cause_link_adds_one_to_the_component_score():
    jev = FakeJev(script(
        symptoms=("slow_crank", "battery_light", "overheat_traffic", "coolant_smell"),
        components={"battery": 0.95, "charge": 0.3, "cooling": 0.45},
        answer=sure("low"),
    ))
    session = started(jev)
    scores = {c["id"]: c["score"] for c in session.view()["components"]}
    assert scores["charge"] == pytest.approx(0.3) and scores["cooling"] == pytest.approx(0.9)
    session.answer("11.8 volts")
    # Charge: 0.3 for battery_light, plus 1 because it can cause the found flat_battery.
    assert session.faults[0]["id"] == "flat_battery"
    assert session.view()["loop"] == {"index": 2, "component": "charge"}


def test_an_explained_symptom_does_not_select_its_component_again():
    jev = FakeJev(script(symptoms=("slow_crank", "dim_lights"), components={"battery": 0.9, "charge": 0.9},
                         answer=sure("low")))
    session = started(jev)
    session.answer("11.8 volts")
    view = session.view()
    assert view["status"] == "complete"
    assert [f["id"] for f in view["faults"]] == ["flat_battery"]
    states = {c["id"]: c["state"] for c in view["components"]}
    assert states == {"battery": "fault", "charge": "open", "cooling": "open"}
    assert [k for k in kinds(session) if k[1] == "A"] == [(1, "A")]


def test_the_loop_stops_at_max_faults():
    jev = FakeJev(script(
        symptoms=("slow_crank", "battery_light", "overheat_traffic", "brake_noise"),
        components={"battery": 0.9, "charge": 0.8, "cooling": 0.7, "brakes": 0.6},
        answer=[sure("low"), sure("low"), sure("no"), sure("no")],
    ))
    session = started(jev, model=four_component_model())
    for text in ("11.8 V", "12.9 V", "belt is fine", "the fan does not run"):
        session.answer(text)
    view = session.view()
    assert view["status"] == "complete"
    assert [f["id"] for f in view["faults"]] == ["flat_battery", "alternator_failure", "fan_failure"]
    assert view["unexplained"] == [{"id": "brake_noise", "label": "Brake noise"}]
    assert {c["id"]: c["state"] for c in view["components"]}["brakes"] == "open"
    assert len([k for k in kinds(session) if k[1] == "A"]) == 3


def test_specialist_end_with_no_fault():
    jev = FakeJev(script(symptoms=("overheat_traffic",), components={"cooling": 0.9},
                         answer=[sure("yes"), sure("no")]))
    session = started(jev)
    session.answer("yes, the fan runs")
    assert session.view()["status"] == "flagged"
    session.keep_going()
    session.answer("no leak")
    view = session.view()
    assert view["status"] == "specialist"
    assert view["faults"] == [] and view["fix"] == []
    assert view["unexplained"] == [{"id": "overheat_traffic", "label": "Overheats in traffic"}]
    assert {c["id"]: c["state"] for c in view["components"]}["cooling"] == "no_fault"
    assert view["path"] == ["q_cool_fan", "q_cool_leak", "specialist"]


def test_no_present_symptom_ends_at_the_specialist():
    session = started(FakeJev(script()))
    view = session.view()
    assert view["status"] == "specialist"
    assert view["loop"] == {"index": 0, "component": None}
    assert view["mermaid"] == ""
    assert kinds(session) == [(0, "E"), (0, "C")]


def test_complete_with_unexplained_symptoms():
    jev = FakeJev(script(symptoms=("slow_crank", "overheat_traffic"), components={"battery": 0.9, "cooling": 0.5},
                         answer=[sure("low"), sure("yes"), sure("no")]))
    session = started(jev)
    session.answer("11.8 V")
    session.answer("the fan runs")
    session.keep_going()
    session.answer("no leak")
    view = session.view()
    assert view["status"] == "complete"
    assert [f["id"] for f in view["faults"]] == ["flat_battery"]
    assert view["unexplained"] == [{"id": "overheat_traffic", "label": "Overheats in traffic"}]


def test_accept_records_the_flagged_fault_and_continues_the_loop():
    jev = FakeJev(script(symptoms=("coolant_smell", "overheat_traffic", "slow_crank"),
                         components={"cooling": 0.9, "battery": 0.5}, answer=sure("yes")))
    session = started(jev)
    session.answer("yes it runs")
    view = session.view()
    assert view["status"] == "flagged"
    assert view["flag"]["id"] == "hose_leak"
    session.accept()
    view = session.view()
    assert view["faults"][0]["id"] == "hose_leak"
    assert view["loop"] == {"index": 2, "component": "battery"}
    assert view["status"] == "asking"
    with pytest.raises(SessionError):
        session.accept()


def test_confirm_and_choose():
    jev = FakeJev(script(**CASCADE, answer=make_choice({"low": 0.6, "ok": 0.35, "unclear": 0.05}, 0.6)))
    session = started(jev)
    session.answer("around twelve I think")
    view = session.view()
    assert view["status"] == "confirm"
    assert [o["id"] for o in view["confirm_options"]] == ["low", "ok"]
    session.choose("low")
    view = session.view()
    assert view["faults"][0]["id"] == "flat_battery"
    assert [s["outcome"] for s in view["steps"]] == ["confirm", "chosen"]


def test_reask():
    jev = FakeJev(script(**CASCADE, answer=make_choice({"unclear": 0.9, "low": 0.1}, 0.9)))
    session = started(jev)
    session.answer("the radio works")
    view = session.view()
    assert view["status"] == "reask"
    assert view["current"]["node_id"] == "q_bat_voltage"


def test_actions_that_do_not_apply_raise():
    session = Session(mini_model(), FakeJev(script()), "report", REPORT)
    session.start()
    assert session.status == "specialist"
    with pytest.raises(SessionError):
        session.answer("x")
    with pytest.raises(SessionError):
        session.start()
    with pytest.raises(SessionError):
        session.keep_going()


def test_known_answers_from_request_a_walk_the_branch():
    jev = FakeJev(script(**CASCADE, pre_q_bat_voltage=make_choice({"low": 0.98, "not_stated": 0.02}, 0.95)))
    session = started(jev, mode="case_file", case_file=CASE_FILE, date="2026-09-01")
    view = session.view()
    assert view["faults"][0]["id"] == "flat_battery"
    assert view["steps"][0]["source"] == "report" and view["steps"][0]["step"] == 1
    assert view["loop"]["component"] == "charge"


def test_case_file_mode_sends_the_filtered_case_file():
    jev = FakeJev(script(**CASCADE))
    session = started(jev, mode="case_file", case_file=CASE_FILE, date="2026-09-01")
    state, questions = jev.calls[0] if "sym_slow_crank" in jev.calls[0][1] else jev.calls[1]
    assert [c["code"] for c in state["obd_codes"]] == ["P0562", "P0300"]
    view = session.view()
    assert len(view["evidence"]["removed"]) == 3
    assert view["evidence"]["case_file"]["obd_codes"] == state["obd_codes"]


def test_extra_questions_stay_inside_the_component():
    jev = FakeJev(script(**CASCADE, answer=[sure("low"), sure("low")]))
    session = started(jev)
    session.answer("11.8 V")
    session.answer("12.9 V")
    b_questions = [q for _, q in jev.calls if "answer" in q]
    assert set(b_questions[1]) == {"answer", "extra_q_chg_belt"}


def test_mermaid_draws_the_active_branch_only():
    session = started(FakeJev(script(**CASCADE, answer=sure("low"))))
    session.answer("11.8 V")
    text = session.view()["mermaid"]
    assert "q_chg_belt" in text and "alternator_failure" in text
    assert "q_bat_voltage" not in text and "q_cool_fan" not in text
    assert "class q_chg_running_voltage current" in text


def test_independent_lane_reads_each_diagnosis_noul():
    jev = FakeJev(script(**CASCADE, diagnoses={"flat_battery": 0.9, "alternator_failure": 0.7}))
    view = started(jev).view()
    ind = view["independent"]
    assert ind["enabled"] is True
    assert [f["id"] for f in ind["faults"]] == ["flat_battery", "alternator_failure"]
    assert len(ind["top"]) == 5
    assert ind["top"][0] == {"id": "flat_battery", "label": "Flat battery", "score": 0.9}


def test_no_independent_lane_sends_no_request_c():
    session = started(FakeJev(script(**CASCADE)), independent_lane=False)
    assert kinds(session) == [(0, "E"), (1, "A")]
    assert session.view()["independent"]["top"] == []


def test_request_c_runs_at_the_same_time_as_request_e():
    jev = FakeJev(script(**CASCADE), delay=0.2)
    t0 = time.perf_counter()
    started(jev)
    elapsed = time.perf_counter() - t0
    # E and C together, then A: two delays, not three.
    assert elapsed < 0.55


def test_symptom_noul_threshold():
    jev = FakeJev(script(**CASCADE, sym_belt_squeal=noul(0.5)))
    view = started(jev).view()
    squeal = next(s for s in view["symptoms"] if s["id"] == "belt_squeal")
    assert squeal["probability"] == 0.5 and squeal["present"] is False
