from v2_helpers import CASE_FILE, mini_model

from jev_mechanic import questions as v1
from jev_mechanic.v2 import questions as q
from jev_mechanic.v2.casefile import evidence_state

REPORT = "Slow to start, and the battery light comes on."


def test_evidence_request_has_a_noul_for_each_symptom_and_component():
    model = mini_model()
    state, questions = q.evidence_request(model, evidence_state("report", REPORT, None))
    assert state == {"customer_report": REPORT}
    assert set(questions) == {f"sym_{s}" for s in model.symptoms} | {f"comp_{c}" for c in model.components}
    for question in questions.values():
        assert question["type"] == "noul"
        assert set(question["criteria"]) == {"true", "false"}
        assert "`customer_report`" in question["instructions"]
        assert "`obd_codes`" not in question["instructions"]
    assert "Slow crank" in questions["sym_slow_crank"]["instructions"]
    assert "Alternator failure" in questions["comp_charge"]["instructions"]


def test_case_file_questions_name_each_source():
    model = mini_model()
    _, questions = q.evidence_request(model, evidence_state("case_file", REPORT, CASE_FILE))
    text = questions["sym_battery_light"]["instructions"]
    for field in ("customer_report", "obd_codes", "freeze_frame", "technician_notes"):
        assert f"`{field}`" in text


def test_branch_request_asks_the_nodes_of_one_component():
    model = mini_model()
    state, questions = q.branch_request(model, {"customer_report": REPORT}, "charge")
    assert state == {"customer_report": REPORT}
    assert set(questions) == {"pre_q_chg_running_voltage", "pre_q_chg_belt"}
    criteria = questions["pre_q_chg_belt"]["criteria"]
    assert set(criteria) == {"yes", "no", "not_stated"}
    assert questions["pre_q_chg_belt"]["type"] == "choice"


def test_answer_request_is_the_version_1_request():
    model = mini_model()
    got = q.answer_request(model, REPORT, "q_chg_running_voltage", "12.9 V", ["q_chg_belt"])
    assert got == v1.answer_request(model.chart, REPORT, "q_chg_running_voltage", "12.9 V", ["q_chg_belt"])
    assert set(got[1]) == {"answer", "extra_q_chg_belt"}


def test_independent_request_has_a_noul_for_each_diagnosis():
    model = mini_model()
    qa = [{"question": "What is the battery voltage at rest?", "answer": "11.9 V", "step": 1}]
    state, questions = q.independent_request(model, {"customer_report": REPORT}, qa)
    assert state["questions_and_answers"] == [{"question": "What is the battery voltage at rest?", "answer": "11.9 V"}]
    assert set(questions) == {f"diag_{d}" for d in model.diagnoses}
    for question in questions.values():
        assert question["type"] == "noul"
        assert "`questions_and_answers`" in question["instructions"]
        assert set(question["criteria"]) == {"true", "false"}
