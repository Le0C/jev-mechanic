"""A version 2 session: find 1 to 3 faults, one component branch for each loop."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date as Date

from .. import flowchart as fc
from .. import scoring
from .. import session as v1
from ..jev import JevClient, JevResult
from ..session import ASKING, CONFIRM, FLAGGED, REASK, SPECIALIST_STATUS, SessionError
from . import casefile
from .model import MAX_FAULTS, FaultModel
from .questions import branch_nodes, branch_request, evidence_request, independent_request

__all__ = ["Session", "SessionError", "ASKING", "CONFIRM", "REASK", "FLAGGED", "COMPLETE", "SPECIALIST_STATUS"]

COMPLETE = "complete"
PRESENT_THRESHOLD = 0.5

# P(symptom present | diagnosis) for the start of the branch scores.
EXPLAINED_LIKELIHOOD = 0.8
UNEXPLAINED_LIKELIHOOD = 0.2

TOP_BRANCH = 8
TOP_INDEPENDENT = 8

# The `state` of a component in the view.
OPEN = "open"
ACTIVE = "active"
FAULT = "fault"
NO_FAULT = "no_fault"


class Session(v1.Session):
    """Loop over the components until the found faults explain the symptoms."""

    def __init__(
        self,
        model: FaultModel,
        jev: JevClient,
        mode: str,
        report: str,
        case_file: dict | None = None,
        date: str | None = None,
        extra_questions: bool = True,
        independent_lane: bool = True,
    ):
        super().__init__(model.chart, jev, report, extra_questions, independent_lane)
        self.model = model
        self.mode = mode
        self.date = date or Date.today().isoformat()
        self.case_file: dict | None = None
        self.removed: list[dict] = []
        if mode == casefile.CASE_FILE:
            if case_file is None:
                raise ValueError("the mode case_file needs a case file")
            self.case_file, self.removed = casefile.filter_case_file(case_file, self.date)
        self.evidence = casefile.evidence_state(mode, report, self.case_file)
        self.symptom_probs: dict[str, float] = {}
        self.component_probs: dict[str, float] = {}
        self.component_state = {cid: OPEN for cid in model.components}
        self.explained: dict[str, str] = {}
        self.faults: list[dict] = []
        self.loop = 0
        self.active: str | None = None
        self._last_component: str | None = None

    # Jev calls

    def _ask_pair(self, flow: tuple[dict, dict], kind: str) -> dict:
        """Send request E, A or B. Send request C at the same time as E and B."""
        independent = None
        if self.independent_lane and kind != "A":
            independent = independent_request(self.model, self.evidence, self._qa())
        with ThreadPoolExecutor(max_workers=2) as pool:
            flow_future = pool.submit(self.jev.ask, *flow)
            ind_future = pool.submit(self.jev.ask, *independent) if independent else None
            flow_result: JevResult = flow_future.result()
            ind_result: JevResult | None = ind_future.result() if ind_future else None
        self.ledger.add(self._step, "flowchart", kind, flow_result)
        if ind_result is not None:
            self.ledger.add(self._step, "independent", "C", ind_result)
            self.independent = {
                did: _noul(ind_result.answers.get(f"diag_{did}")) for did in self.model.diagnoses
            }
        return flow_result.answers

    # Public actions

    def start(self) -> None:
        """Send request E (and C), then start the first loop."""
        with self._lock:
            if self.status is not None:
                raise SessionError("the session has started")
            answers = self._ask_pair(evidence_request(self.model, self.evidence), "E")
            self.symptom_probs = {s: _noul(answers.get(f"sym_{s}")) for s in self.model.symptoms}
            self.component_probs = {c: _noul(answers.get(f"comp_{c}")) for c in self.model.components}
            self._next_loop()

    def accept(self) -> None:
        """Accept the flagged diagnosis as a fault, and start the next loop."""
        with self._lock:
            if self.status != FLAGGED:
                raise SessionError(f"no flagged diagnosis (status {self.status})")
            fault = self.flag
            self.flag = None
            self._found(fault)
            self._next_loop()

    # The loop

    def present(self) -> list[str]:
        return [s for s, p in self.symptom_probs.items() if p > PRESENT_THRESHOLD]

    def unexplained(self) -> list[str]:
        return [s for s in self.present() if s not in self.explained]

    def component_score(self, component_id: str) -> float | None:
        """Return the selection score of a component, or None when the loop cannot select it."""
        if self.component_state[component_id] != OPEN:
            return None
        diagnoses = self.model.diagnoses_of(component_id)
        can = {s for d in diagnoses for s in self.model.explains[d]} & set(self.unexplained())
        if not can:
            return None
        score = self.component_probs.get(component_id, 0.0) * len(can)
        found = [f["id"] for f in self.faults]
        if any(cause in diagnoses for f in found for cause in self.model.caused_by(f)):
            score += 1.0
        return score

    def _select(self) -> str | None:
        best, best_score = None, None
        for cid in self.model.components:
            score = self.component_score(cid)
            if score is not None and (best_score is None or score > best_score):
                best, best_score = cid, score
        return best

    def _next_loop(self) -> None:
        """Select the next component and walk its branch, or end the case."""
        self.active = None
        self.current = None
        component = self._select() if len(self.faults) < MAX_FAULTS else None
        if component is None:
            self.status = COMPLETE if self.faults else SPECIALIST_STATUS
            return
        self.loop += 1
        self.active = self._last_component = component
        self.component_state[component] = ACTIVE
        self._step += 1
        answers = self._ask_pair(branch_request(self.model, self.evidence, component), "A")
        for nid in branch_nodes(self.model, component):
            self._remember(nid, answers.get(f"pre_{nid}"))
        self.scores = self._branch_prior(component)
        self._go_to(self.model.components[component].entry)
        self._apply_known()

    def _branch_prior(self, component_id: str) -> dict[str, float]:
        present = self.present()
        scores = {}
        for did in self.model.diagnoses_of(component_id):
            score = self.model.diagnoses[did].prior
            for s in present:
                explains = s in self.model.explains[did]
                score *= EXPLAINED_LIKELIHOOD if explains else UNEXPLAINED_LIKELIHOOD
            scores[did] = score
        total = sum(scores.values())
        if total <= 0:
            return {d: 1.0 / len(scores) for d in scores} if scores else {}
        return {d: s / total for d, s in scores.items()}

    def _found(self, diagnosis_id: str) -> None:
        """Record a fault, mark its symptoms as explained, and close the active component."""
        if all(f["id"] != diagnosis_id for f in self.faults):
            newly = [s for s in self.model.explains[diagnosis_id] if s in self.present() and s not in self.explained]
            for s in newly:
                self.explained[s] = diagnosis_id
            self.faults.append(
                {
                    "id": diagnosis_id,
                    "score": self.scores.get(diagnosis_id, 0.0),
                    "component": self.active,
                    "loop": self.loop,
                    "explains": newly,
                }
            )
        self.component_state[self.active] = FAULT

    def _finish(self, leaf: str) -> None:
        """Close the loop at a leaf, then start the next loop."""
        self.flag = None
        self.current = None
        if self.path:
            self.path.append(leaf)
        if leaf == fc.SPECIALIST:
            self.component_state[self.active] = NO_FAULT
        else:
            self._found(leaf)
        self._next_loop()

    def _record(self, node_id, text, source, option, probs, confidence, outcome) -> dict:
        step = super()._record(node_id, text, source, option, probs, confidence, outcome)
        step.update(loop=self.loop, component=self.active)
        return step

    # View

    def _scored(self, did: str, score: float) -> dict:
        return {"id": did, "label": self.model.diagnoses[did].label, "score": score}

    def _fix(self) -> list[dict]:
        seen: set[str] = set()
        fix = []
        for did in self.model.root_first([f["id"] for f in self.faults]):
            steps = [s for s in self.model.diagnoses[did].fix if s not in seen]
            seen.update(steps)
            fix.append({"diagnosis": did, "label": self.model.diagnoses[did].label, "steps": steps})
        return fix

    def _mermaid(self) -> str:
        """Draw the branch of the active component, or of the last component when none is active."""
        component = self.active or self._last_component
        if component is None:
            return ""
        chart = self.model.chart
        nodes = {nid: chart.nodes[nid] for nid in branch_nodes(self.model, component)}
        leaves = {o.next for n in nodes.values() for o in n.options.values() if o.next in chart.diagnoses}
        sub = fc.Flowchart(
            systems={component: chart.systems[component]},
            diagnoses={d: chart.diagnoses[d] for d in chart.diagnoses if d in leaves},
            nodes=nodes,
            raw={},
        )
        drawn = set(nodes) | leaves | {fc.SPECIALIST}
        loop_path = [n for n in self._loop_path(component) if n in drawn]
        current = self.current if self.current in nodes else None
        return sub.to_mermaid(path=loop_path, current=current)

    def _loop_path(self, component: str) -> list[str]:
        """Return the part of `path` that the walk of `component` added."""
        entry = self.model.components[component].entry
        starts = [i for i, n in enumerate(self.path) if n == entry]
        return self.path[starts[-1]:] if starts else []

    def view(self) -> dict:
        """Return the JSON view of the session for the UI and the CLI."""
        with self._lock:
            current = None
            if self.current is not None and self.status in (ASKING, CONFIRM, REASK, FLAGGED):
                node = self.chart.nodes[self.current]
                current = {
                    "node_id": node.id,
                    "question": node.question,
                    "options": [{"id": o.id, "text": o.text} for o in node.options.values()],
                    "yes_no": node.is_yes_no,
                }
            present = set(self.present())
            found = {f["id"] for f in self.faults}
            ind_ranked = scoring.top(self.independent, len(self.independent))
            return {
                "id": self.id,
                "version": 2,
                "mode": self.mode,
                "status": self.status,
                "evidence": {"report": self.report, "case_file": self.case_file, "removed": list(self.removed)},
                "symptoms": [
                    {
                        "id": s.id,
                        "label": s.label,
                        "probability": self.symptom_probs.get(s.id),
                        "present": s.id in present,
                        "explained_by": self.explained.get(s.id),
                    }
                    for s in self.model.symptoms.values()
                ],
                "components": [
                    {
                        "id": c.id,
                        "label": c.label,
                        "probability": self.component_probs.get(c.id),
                        "state": self.component_state[c.id],
                        "score": self.component_score(c.id),
                    }
                    for c in self.model.components.values()
                ],
                "loop": {"index": self.loop, "component": self.active},
                "current": current,
                "confirm_options": list(self._confirm) if self.status == CONFIRM else [],
                "steps": [dict(s) for s in self.steps],
                "branch_scores": [self._scored(d, s) for d, s in scoring.top(self.scores, TOP_BRANCH)]
                if self.active
                else [],
                "flag": self._scored(self.flag, self.scores[self.flag]) if self.status == FLAGGED else None,
                "faults": [
                    {
                        **self._scored(f["id"], f["score"]),
                        "component": f["component"],
                        "loop": f["loop"],
                        "explains": list(f["explains"]),
                        "caused_by_found": [c for c in self.model.caused_by(f["id"]) if c in found],
                    }
                    for f in self.faults
                ],
                "fix": self._fix(),
                "unexplained": [{"id": s, "label": self.model.symptoms[s].label} for s in self.unexplained()],
                "independent": {
                    "enabled": self.independent_lane,
                    "faults": [self._scored(d, p) for d, p in ind_ranked if p > PRESENT_THRESHOLD],
                    "top": [self._scored(d, p) for d, p in ind_ranked[:TOP_INDEPENDENT]],
                },
                "path": list(self.path),
                "mermaid": self._mermaid(),
                "ledger": self.ledger.to_dict(),
            }


def _noul(answer: dict | None) -> float:
    return float(answer["noul"]) if answer and "noul" in answer else 0.0
