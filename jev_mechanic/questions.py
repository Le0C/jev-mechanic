"""Build the Jev requests A (triage), B (answer interpretation) and C (independent lane)."""

from __future__ import annotations

from .flowchart import NEUTRAL_OPTIONS, Flowchart, Node

MAX_EXTRA = 8

NOT_STATED = "not_stated"
UNCLEAR = "unclear"
NONE = "none"


def _node_criteria(node: Node) -> dict:
    """Return the node options as criteria, without the neutral options of the node."""
    return {oid: option.text for oid, option in node.options.items() if oid not in NEUTRAL_OPTIONS}


def _fact_question(node: Node, field: str) -> dict:
    """Ask which option of `node` the text in `field` states, with a `not_stated` option."""
    criteria = _node_criteria(node)
    criteria[NOT_STATED] = {
        "what": f"`{field}` does not give this fact.",
        "covers": [
            f"`{field}` does not mention the subject of the question.",
            f"`{field}` mentions the subject, but does not say which option applies.",
            f"`{field}` gives two or more of the other options, for example at different times.",
        ],
    }
    return {
        "type": "choice",
        "instructions": {
            "question": node.question,
            "task": f"Select the option that `{field}` states. Use only the words in `{field}`.",
            "rule": f"Select `{NOT_STATED}` when `{field}` does not state one option clearly.",
        },
        "criteria": criteria,
    }


def triage_request(chart: Flowchart, report: str) -> tuple[dict, dict]:
    """Return request A: the vehicle system, and a `pre_` question for each flowchart node."""
    criteria: dict = {
        sid: {
            "system": system.label,
            "what": system.description,
            "faults": [d.label for d in chart.diagnoses.values() if sid in d.systems],
        }
        for sid, system in chart.systems.items()
    }
    criteria[NONE] = {
        "what": "`customer_report` describes no fault of the car, or a fault that fits none of the other options.",
        "examples": ["A question about the price of a service", "A fault in the radio or the air conditioning"],
    }
    questions = {
        "system": {
            "type": "choice",
            "instructions": {
                "question": "Which system of the car has the fault that `customer_report` describes?",
                "focus": "Classify the main fault in `customer_report`. Do not guess a fault that it does not describe.",
            },
            "criteria": criteria,
        }
    }
    for nid, node in chart.nodes.items():
        questions[f"pre_{nid}"] = _fact_question(node, "customer_report")
    return {"customer_report": report}, questions


def answer_request(
    chart: Flowchart, report: str, node_id: str, answer_text: str, extra_node_ids: list[str]
) -> tuple[dict, dict]:
    """Return request B: map `answer_text` onto the node options, plus `extra_` questions."""
    node = chart.nodes[node_id]
    criteria: dict = {}
    for oid, option in node.options.items():
        if oid == "not_sure":
            criteria[oid] = {
                "what": "`mechanic_answer` says that the mechanic does not know, or could not check.",
                "examples": ["Not sure", "I did not check that", "No idea"],
            }
        else:
            criteria[oid] = option.text
    criteria[UNCLEAR] = {
        "what": "`mechanic_answer` does not say which of the other options applies.",
        "covers": [
            "`mechanic_answer` is about a different subject.",
            "`mechanic_answer` fits two or more of the other options equally.",
            "`mechanic_answer` is empty or has no meaning.",
        ],
    }
    questions = {
        "answer": {
            "type": "choice",
            "instructions": {
                "question": "Which option matches `mechanic_answer`?",
                "context": "`mechanic_answer` is the reply of the mechanic to `question`.",
                "rule": "Use `customer_report` only to understand the words in `mechanic_answer`. "
                "Select from what `mechanic_answer` says.",
            },
            "criteria": criteria,
        }
    }
    for nid in extra_node_ids[:MAX_EXTRA]:
        questions[f"extra_{nid}"] = _fact_question(chart.nodes[nid], "mechanic_answer")
    state = {"question": node.question, "mechanic_answer": answer_text, "customer_report": report}
    return state, questions


def _qa_item(x: dict) -> dict:
    item = {"question": x["question"], "answer": x["answer"]}
    if x.get("answer_reference"):
        item["answer_reference"] = x["answer_reference"]
    return item


def independent_request(chart: Flowchart, report: str, qa: list[dict]) -> tuple[dict, dict]:
    """Return request C: the diagnosis from the whole case, with no flowchart evidence."""
    criteria: dict = {
        did: {
            "fault": diagnosis.label,
            "what": diagnosis.description,
            "system": [chart.systems[s].label for s in diagnosis.systems],
        }
        for did, diagnosis in chart.diagnoses.items()
    }
    criteria[NONE] = {
        "what": "The evidence does not identify one of the other faults.",
        "covers": [
            "The evidence fits two or more faults equally.",
            "The evidence describes a fault that is not in the other options.",
            "The evidence describes no fault.",
        ],
    }
    questions = {
        "diagnosis": {
            "type": "choice",
            "instructions": {
                "question": "Which fault of the car do `customer_report` and `questions_and_answers` show?",
                "rule": "The car has one fault only. Use the answers in `questions_and_answers` as facts "
                "that the mechanic found. The `answer_reference` of an item gives the meaning of each "
                "possible answer, such as the limit for a measured value.",
            },
            "criteria": criteria,
        }
    }
    state = {
        "customer_report": report,
        "questions_and_answers": [_qa_item(x) for x in qa],
    }
    return state, questions
