import json

from engine_helpers import chart_from, mini_chart

from jev_mechanic import questions as q
from jev_mechanic.jev import answer_dict

REPORT = "The car clicks when I turn the key and does not start."


def _text(value) -> str:
    return json.dumps(value)


def _chain_chart(length: int):
    """Return a chart with one system and a chain of `length` yes or no nodes."""
    nodes = {}
    for i in range(length):
        nxt = f"n{i + 1}" if i + 1 < length else "d_a"
        nodes[f"n{i}"] = {
            "question": f"Question {i}?",
            "options": {"yes": {"text": "Yes", "next": nxt}, "no": {"text": "No", "next": "d_b"}},
        }
    return chart_from(
        {
            "systems": {"s": {"label": "S", "description": "System S", "entry": "n0"}},
            "diagnoses": {
                d: {"label": d, "description": d, "systems": ["s"], "prior": 0.5, "fix": ["a.", "b.", "c."]}
                for d in ("d_a", "d_b")
            },
            "nodes": nodes,
        }
    )


def test_triage_request_shape():
    chart = mini_chart()
    state, questions = q.triage_request(chart, REPORT)
    assert state == {"customer_report": REPORT}
    assert set(questions) == {"system", "pre_q_key_turn", "pre_q_headlights_dim", "pre_q_brake_noise"}
    assert set(questions["system"]["criteria"]) == {"no_start", "brakes", "none"}
    assert "`customer_report`" in _text(questions["system"]["instructions"])
    json.dumps(questions)


def test_pre_questions_have_node_options_and_not_stated():
    chart = mini_chart()
    _, questions = q.triage_request(chart, REPORT)
    pre = questions["pre_q_key_turn"]
    assert pre["type"] == "choice"
    assert set(pre["criteria"]) == {"click_only", "slow_crank", "not_stated"}
    assert "`customer_report`" in _text(pre["instructions"])
    assert set(questions["pre_q_brake_noise"]["criteria"]) == {"squeal", "none", "not_stated"}


def test_reserved_options_have_explicit_descriptions():
    chart = mini_chart()
    _, triage = q.triage_request(chart, REPORT)
    _, answer = q.answer_request(chart, REPORT, "q_key_turn", "clicks", ["q_headlights_dim"])
    _, independent = q.independent_request(chart, REPORT, [])
    described = [
        triage["system"]["criteria"]["none"],
        triage["pre_q_key_turn"]["criteria"]["not_stated"],
        answer["answer"]["criteria"]["unclear"],
        answer["answer"]["criteria"]["not_sure"],
        answer["extra_q_headlights_dim"]["criteria"]["not_stated"],
        independent["diagnosis"]["criteria"]["none"],
    ]
    for description in described:
        assert isinstance(description, dict) and description["what"]


def test_answer_request_shape():
    chart = mini_chart()
    state, questions = q.answer_request(chart, REPORT, "q_key_turn", "a few clicks", ["q_headlights_dim"])
    assert state == {
        "question": chart.nodes["q_key_turn"].question,
        "mechanic_answer": "a few clicks",
        "customer_report": REPORT,
    }
    assert set(questions) == {"answer", "extra_q_headlights_dim"}
    assert set(questions["answer"]["criteria"]) == {"click_only", "slow_crank", "not_sure", "unclear"}
    assert "`mechanic_answer`" in _text(questions["answer"]["instructions"])
    extra = questions["extra_q_headlights_dim"]
    assert set(extra["criteria"]) == {"yes", "no", "not_stated"}
    assert "`mechanic_answer`" in _text(extra["instructions"])


def test_answer_request_caps_extra_questions():
    chart = _chain_chart(12)
    extra = chart.reachable_nodes("n0")[1:]
    assert len(extra) == 11
    _, questions = q.answer_request(chart, REPORT, "n0", "yes", extra)
    assert sum(k.startswith("extra_") for k in questions) == q.MAX_EXTRA == 8


def test_independent_request_shape():
    chart = mini_chart()
    qa = [{"question": "What happens?", "answer": "clicks", "extra": "dropped"}]
    state, questions = q.independent_request(chart, REPORT, qa)
    assert state == {"customer_report": REPORT, "questions_and_answers": [{"question": "What happens?", "answer": "clicks"}]}
    assert set(questions) == {"diagnosis"}
    assert set(questions["diagnosis"]["criteria"]) == {*chart.diagnoses, "none"}
    assert "`questions_and_answers`" in _text(questions["diagnosis"]["instructions"])


def test_answer_dict_converts_sdk_answers():
    from typesafe_sdk import ChoiceAnswer, NoulAnswer

    choice = answer_dict(ChoiceAnswer(choice="a", confidence=0.9, probabilities={"a": 0.95, "b": 0.05}))
    assert choice == {"type": "choice", "choice": "a", "probabilities": {"a": 0.95, "b": 0.05}, "confidence": 0.9}
    assert answer_dict(NoulAnswer(noul=0.3)) == {"type": "noul", "noul": 0.3}
