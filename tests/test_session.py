import re
import time

import pytest
from engine_helpers import NOT_STATED, chart_from, choice, mini_chart, mini_raw, script

from jev_mechanic.jev import FakeJev
from jev_mechanic.session import Session, SessionError

REPORT = "The car will not start this morning."

VIEW_KEYS = {
    "id", "report", "status", "triage", "current", "confirm_options", "steps", "scores",
    "flag", "independent", "diagnosis", "path", "mermaid", "ledger",
}


def sure(option: str, confidence: float = 0.95) -> dict:
    return choice({option: 0.97, "unclear": 0.03}, confidence)


def started(jev: FakeJev, chart=None, **kwargs) -> Session:
    session = Session(chart or mini_chart(), jev, REPORT, **kwargs)
    session.start()
    return session


def flag_chart():
    """Return the mini chart with a strong `click_only` and one more node after the headlights."""
    raw = mini_raw()
    key = raw["nodes"]["q_key_turn"]
    key["evidence"]["click_only"] = {"flat_battery": 0.9, "starter_motor": 0.05}
    raw["nodes"]["q_headlights_dim"]["options"]["yes"]["next"] = "q_interior"
    raw["nodes"]["q_interior"] = {
        "question": "Do the interior lights work?",
        "options": {"yes": {"text": "Yes", "next": "starter_motor"}, "no": {"text": "No", "next": "flat_battery"}},
    }
    return chart_from(raw)


def test_start_asks_the_entry_node():
    session = started(FakeJev(script()))
    view = session.view()
    assert set(view) == VIEW_KEYS
    assert view["status"] == "asking"
    assert view["current"]["node_id"] == "q_key_turn"
    assert view["current"]["yes_no"] is False
    assert view["path"] == ["q_key_turn"]
    assert view["triage"]["system"] == "no_start"
    assert view["scores"][0] == {"id": "flat_battery", "label": "Flat battery", "score": pytest.approx(0.6)}
    assert view["confirm_options"] == []
    assert view["flag"] is None and view["diagnosis"] is None
    assert re.fullmatch(r"s_[0-9a-f]{4}", view["id"])
    assert [(r["step"], r["kind"]) for r in view["ledger"]["rows"]] == [(0, "A"), (0, "C")]


def test_accepted_answer_reaches_a_diagnosis():
    session = started(FakeJev(script(answer=sure("slow_crank"))))
    session.answer("it turns over really slowly")
    view = session.view()
    assert view["status"] == "diagnosed"
    assert view["current"] is None
    assert view["diagnosis"]["id"] == "flat_battery"
    assert view["diagnosis"]["fix"][0] == "Measure the resting voltage."
    step = view["steps"][-1]
    assert (step["step"], step["source"], step["option"], step["outcome"]) == (1, "user", "slow_crank", "accepted")
    assert view["path"] == ["q_key_turn", "flat_battery"]


def test_confirm_then_choose():
    unsure = choice({"click_only": 0.6, "slow_crank": 0.35, "unclear": 0.05}, 0.6)
    session = started(FakeJev(script(answer=unsure)))
    before = dict(session.scores)
    session.answer("it sort of clicks")
    view = session.view()
    assert view["status"] == "confirm"
    assert [o["id"] for o in view["confirm_options"]] == ["click_only", "slow_crank"]
    assert view["confirm_options"][0]["probability"] == pytest.approx(0.6)
    assert view["steps"][-1]["outcome"] == "confirm"
    assert session.scores == before

    session.choose("click_only")
    view = session.view()
    assert view["status"] == "asking"
    assert view["current"]["node_id"] == "q_headlights_dim"
    assert view["current"]["yes_no"] is True
    assert view["confirm_options"] == []
    step = view["steps"][-1]
    assert (step["outcome"], step["option"], step["source"]) == ("chosen", "click_only", "user")
    assert session.scores != before


@pytest.mark.parametrize(
    "answer",
    [
        choice({"unclear": 0.9, "click_only": 0.1}, 0.85),
        choice({"click_only": 0.45, "slow_crank": 0.4, "unclear": 0.15}, 0.3),
    ],
)
def test_reask_leaves_scores(answer):
    session = started(FakeJev(script(answer=answer)))
    before = dict(session.scores)
    session.answer("the weather was bad")
    view = session.view()
    assert view["status"] == "reask"
    assert view["current"]["node_id"] == "q_key_turn"
    assert view["steps"][-1]["outcome"] == "reask"
    assert session.scores == before


def test_accepted_unclear_share_does_not_move_scores():
    both = choice({"not_sure": 0.9, "unclear": 0.1}, 0.9)
    session = started(FakeJev(script(answer=both)))
    before = dict(session.scores)
    session.answer("I do not know")
    assert session.view()["steps"][-1]["outcome"] == "accepted"
    assert session.scores == pytest.approx(before)


def test_flag_then_accept():
    session = started(FakeJev(script(answer=sure("click_only"))), chart=flag_chart())
    session.answer("just a click")
    view = session.view()
    assert view["status"] == "flagged"
    assert view["flag"]["id"] == "flat_battery"
    assert view["flag"]["score"] > 0.9
    assert view["current"]["node_id"] == "q_headlights_dim"
    session.accept()
    view = session.view()
    assert view["status"] == "diagnosed"
    assert view["diagnosis"]["id"] == "flat_battery"
    assert view["flag"] is None
    assert view["current"] is None


def test_keep_going_does_not_flag_the_same_diagnosis_again():
    answers = [sure("click_only"), sure("yes")]
    session = started(FakeJev(script(answer=answers)), chart=flag_chart())
    session.answer("just a click")
    assert session.status == "flagged"
    session.keep_going()
    assert session.view()["status"] == "asking"
    session.answer("yes, they go dim")
    view = session.view()
    assert view["scores"][0]["id"] == "flat_battery"
    assert view["scores"][0]["score"] > 0.9
    assert view["status"] == "asking"
    assert view["current"]["node_id"] == "q_interior"
    assert view["flag"] is None


def test_triage_none_goes_to_specialist():
    session = started(FakeJev(script(system=choice({"none": 0.8, "no_start": 0.1, "brakes": 0.1}, 0.7))))
    view = session.view()
    assert view["status"] == "specialist"
    assert view["current"] is None
    assert view["diagnosis"] is None
    with pytest.raises(SessionError):
        session.answer("anything")


def test_specialist_leaf():
    answers = [sure("click_only"), sure("not_sure")]
    session = started(FakeJev(script(answer=answers)))
    session.answer("click")
    session.answer("not sure")
    view = session.view()
    assert view["status"] == "specialist"
    assert view["current"] is None
    assert view["path"][-1] == "specialist"


def test_pre_answers_apply_in_a_loop():
    jev = FakeJev(
        script(
            pre_q_key_turn=choice({"click_only": 0.95, "slow_crank": 0.03, "not_stated": 0.02}, 0.9),
            pre_q_headlights_dim=choice({"no": 0.9, "yes": 0.02, "not_stated": 0.08}, 0.85),
        )
    )
    session = started(jev)
    view = session.view()
    assert [s["source"] for s in view["steps"]] == ["report", "report"]
    assert [s["outcome"] for s in view["steps"]] == ["accepted", "accepted"]
    assert view["status"] == "diagnosed"
    assert view["diagnosis"]["id"] == "starter_motor"
    assert view["path"] == ["q_key_turn", "q_headlights_dim", "starter_motor"]


@pytest.mark.parametrize(
    "pre",
    [
        choice({"click_only": 0.75, "not_stated": 0.25}, 0.9),
        choice({"click_only": 0.9, "slow_crank": 0.1, "not_stated": 0.0}, 0.7),
    ],
)
def test_weak_pre_answer_is_ignored(pre):
    session = started(FakeJev(script(pre_q_key_turn=pre)))
    assert session.view()["steps"] == []
    assert session.status == "asking"


def test_extra_answer_applies_after_the_move():
    jev = FakeJev(
        script(
            answer=sure("click_only"),
            extra_q_headlights_dim=choice({"yes": 0.95, "no": 0.03, "not_stated": 0.02}, 0.9),
        )
    )
    session = started(jev)
    session.answer("it clicks and the headlights go dim")
    view = session.view()
    assert [(s["source"], s["node_id"]) for s in view["steps"]] == [("user", "q_key_turn"), ("report", "q_headlights_dim")]
    assert view["steps"][1]["step"] == 1
    assert view["status"] == "diagnosed"
    assert view["diagnosis"]["id"] == "flat_battery"
    b_questions = [qs for _, qs in jev.calls if "answer" in qs]
    assert "extra_q_headlights_dim" in b_questions[0]


def test_no_extra_questions_when_off():
    jev = FakeJev(script(answer=sure("click_only")))
    session = started(jev, extra_questions=False)
    session.answer("click")
    b_questions = [qs for _, qs in jev.calls if "answer" in qs]
    assert b_questions and all(set(qs) == {"answer"} for qs in b_questions)


def test_independent_lane_gets_the_answers():
    diag = choice({"flat_battery": 0.95, "starter_motor": 0.03, "none": 0.02}, 0.92)
    jev = FakeJev(script(answer=sure("click_only"), diagnosis=diag))
    session = started(jev)
    session.answer("a few rapid clicks")
    c_states = [state for state, qs in jev.calls if "diagnosis" in qs]
    assert len(c_states) == 2
    assert c_states[0]["questions_and_answers"] == []
    [item] = c_states[1]["questions_and_answers"]
    assert item["question"] == "What happens when the driver turns the key to start?"
    assert item["answer"] == "a few rapid clicks"
    assert "The engine turns slowly" in item["answer_reference"]
    assert all("not_sure" not in text for text in item["answer_reference"])
    ind = session.view()["independent"]
    assert ind["enabled"] is True
    assert ind["top"][0]["id"] == "flat_battery"
    assert all(t["id"] != "none" for t in ind["top"])
    assert ind["flag"]["id"] == "flat_battery"


def test_independent_lane_off():
    jev = FakeJev(script(answer=sure("click_only")))
    session = started(jev, independent_lane=False)
    session.answer("click")
    view = session.view()
    assert view["independent"] == {"enabled": False, "top": [], "flag": None}
    assert {r["lane"] for r in view["ledger"]["rows"]} == {"flowchart"}
    assert jev.call_count == 2


def test_b_and_c_run_at_the_same_time():
    delay = 0.3
    session = started(FakeJev(script(answer=sure("click_only")), delay=delay))
    started_at = time.perf_counter()
    session.answer("click")
    elapsed = time.perf_counter() - started_at
    rows = [r for r in session.view()["ledger"]["rows"] if r["step"] == 1]
    assert sorted(r["kind"] for r in rows) == ["B", "C"]
    total = sum(r["seconds"] for r in rows)
    wait = max(r["seconds"] for r in rows)
    assert total >= 2 * delay
    assert elapsed < total
    assert wait < total
    totals = session.ledger.totals()
    assert totals["wait_seconds"] < totals["compute_seconds"]


def test_wrong_status_actions_raise():
    session = started(FakeJev(script()))
    for action in (lambda: session.choose("click_only"), session.accept, session.keep_going, session.start):
        with pytest.raises(SessionError):
            action()


def test_session_ids_differ():
    ids = {Session(mini_chart(), FakeJev(), REPORT).id for _ in range(20)}
    assert len(ids) > 1


def test_random_fake_session_runs_to_an_end():
    session = started(FakeJev(seed=3))
    for _ in range(20):
        if session.status in ("diagnosed", "specialist"):
            break
        if session.status == "flagged":
            session.keep_going()
        elif session.status == "confirm":
            session.choose(session.view()["confirm_options"][0]["id"])
        else:
            session.answer("something")
    assert session.view()["ledger"]["totals"]["requests"] >= 2


def test_not_stated_is_a_valid_script_value():
    assert NOT_STATED["choice"] == "not_stated"
