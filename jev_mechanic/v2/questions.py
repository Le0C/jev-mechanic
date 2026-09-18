"""Build the version 2 Jev requests: E (evidence), A (branch), B (answer) and C (independent)."""

from __future__ import annotations

from .. import questions as v1
from ..questions import NOT_STATED, _qa_item
from .model import FaultModel

QA_FIELD = "questions_and_answers"

SOURCE_NOTES = {
    "customer_report": "`customer_report` is the text of the customer.",
    "obd_codes": "`obd_codes` lists the fault codes of the engine computer. The status `active` is a fault now. "
    "The status `pending` is a fault that the computer saw once. The status `history` or `cleared` is a past fault.",
    "freeze_frame": "`freeze_frame` has the sensor values that the computer stored at the time of a fault code.",
    "service_history": "`service_history` lists the past work on the car.",
    "technician_notes": "`technician_notes` has what the technician saw on the car.",
    "vehicle": "`vehicle` gives the make, the model, the year and the mileage.",
}


def _fields(state: dict) -> str:
    """Return the evidence field names of `state` as a backticked list."""
    names = [f"`{k}`" for k in state if k != QA_FIELD]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _notes(state: dict) -> list[str]:
    return [SOURCE_NOTES[k] for k in state if k in SOURCE_NOTES]


def _noul(instructions: str, true: str, false: str) -> dict:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


def symptom_question(model: FaultModel, symptom_id: str, state: dict) -> dict:
    """Ask if the evidence shows one symptom now."""
    symptom = model.symptoms[symptom_id]
    fields = _fields(state)
    return _noul(
        f"Does the evidence in {fields} show that the car has this symptom now: "
        f"\"{symptom.label}\"? {symptom.description.rstrip('.')}.",
        f"The evidence in {fields} states this symptom, or a direct sign of it, for the car now. "
        "A direct sign is an active or pending fault code, a sensor value or a note of the technician.",
        f"The evidence in {fields} does not mention this symptom, or says that the car does not have it, "
        "or shows it only as a past fault that a repair removed.",
    )


def component_question(model: FaultModel, component_id: str, state: dict) -> dict:
    """Ask if the evidence points to a fault in one component."""
    component = model.components[component_id]
    faults = ", ".join(model.diagnoses[d].label for d in model.diagnoses_of(component_id))
    fields = _fields(state)
    return _noul(
        f"Does the evidence in {fields} point to a fault in this part of the car now: "
        f"\"{component.label}\" ({component.description.rstrip('.')})? The faults of this part are: {faults}.",
        f"The evidence in {fields} gives a symptom, a fault code, a sensor value or a note "
        "that one of these faults can cause.",
        f"The evidence in {fields} gives no sign of a fault in this part, or the signs fit a different part only.",
    )


def evidence_request(model: FaultModel, state: dict) -> tuple[dict, dict]:
    """Return request E: a `sym_` Noul for each symptom and a `comp_` Noul for each component."""
    questions = {f"sym_{sid}": symptom_question(model, sid, state) for sid in model.symptoms}
    for cid in model.components:
        questions[f"comp_{cid}"] = component_question(model, cid, state)
    return dict(state), questions


def branch_nodes(model: FaultModel, component_id: str) -> list[str]:
    """Return the node ids of the branch of one component, the entry first."""
    return model.chart.reachable_nodes(model.components[component_id].entry)


def fact_question(node, state: dict) -> dict:
    """Ask which option of `node` the evidence states, with a `not_stated` option."""
    fields = _fields(state)
    criteria = v1._node_criteria(node)
    criteria[NOT_STATED] = {
        "what": f"The evidence in {fields} does not give this fact.",
        "covers": [
            f"The evidence in {fields} does not mention the subject of the question.",
            f"The evidence in {fields} mentions the subject, but does not say which option applies.",
            f"The evidence in {fields} gives two or more of the other options, for example at different times.",
        ],
    }
    return {
        "type": "choice",
        "instructions": {
            "question": node.question,
            "task": f"Select the option that the evidence in {fields} states. Use only the facts in these fields.",
            "sources": _notes(state),
            "rule": f"Select `{NOT_STATED}` when the evidence in {fields} does not state one option clearly.",
        },
        "criteria": criteria,
    }


def branch_request(model: FaultModel, state: dict, component_id: str) -> tuple[dict, dict]:
    """Return request A: a `pre_` Choice for each node of the branch of one component."""
    questions = {f"pre_{nid}": fact_question(model.chart.nodes[nid], state) for nid in branch_nodes(model, component_id)}
    return dict(state), questions


def answer_request(
    model: FaultModel, report: str, node_id: str, answer_text: str, extra_node_ids: list[str]
) -> tuple[dict, dict]:
    """Return request B, as version 1. The caller keeps `extra_node_ids` inside one branch."""
    return v1.answer_request(model.chart, report, node_id, answer_text, extra_node_ids)


def diagnosis_question(model: FaultModel, diagnosis_id: str, state: dict) -> dict:
    """Ask if the evidence and the answers of the mechanic show one fault."""
    diagnosis = model.diagnoses[diagnosis_id]
    parts = ", ".join(model.components[c].label for c in diagnosis.systems)
    fields = _fields(state)
    return _noul(
        f"Does the evidence in {fields} and `{QA_FIELD}` show that the car has this fault: \"{diagnosis.label}\" "
        f"({diagnosis.description.rstrip('.')}, in: {parts})? The car can have more than one fault. "
        "Examine this fault only. The `answer_reference` of an answer gives the meaning of each possible "
        "answer, such as the limit for a measured value.",
        f"The evidence fits this fault, and no answer in `{QA_FIELD}` rules it out.",
        f"The evidence does not point to this fault, or an answer in `{QA_FIELD}` rules it out.",
    )


def independent_request(model: FaultModel, state: dict, qa: list[dict]) -> tuple[dict, dict]:
    """Return request C: a `diag_` Noul for each diagnosis, over the evidence and the answers."""
    full = {k: v for k, v in state.items() if k != QA_FIELD}
    full[QA_FIELD] = [_qa_item(x) for x in qa]
    questions = {f"diag_{did}": diagnosis_question(model, did, full) for did in model.diagnoses}
    return full, questions
