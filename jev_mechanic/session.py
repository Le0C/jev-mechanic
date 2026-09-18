"""One triage session: the flowchart walk, the confidence rules, the scores and the ledger."""

from __future__ import annotations

import secrets
import threading
from concurrent.futures import ThreadPoolExecutor

from . import scoring
from .flowchart import NEUTRAL_OPTIONS, SPECIALIST, Flowchart
from .jev import JevClient, JevResult
from .ledger import Ledger
from .questions import MAX_EXTRA, NONE, NOT_STATED, UNCLEAR, answer_request, independent_request, triage_request

# Request B: take the answer above ACCEPT_CONFIDENCE, confirm it from CONFIRM_CONFIDENCE.
ACCEPT_CONFIDENCE = 0.75
CONFIRM_CONFIDENCE = 0.5

# A `pre_` or `extra_` answer is a given answer only inside these limits.
REPORT_MAX_NOT_STATED = 0.2
REPORT_MIN_CONFIDENCE = 0.8

TOP_SCORES = 8
TOP_INDEPENDENT = 5

ASKING = "asking"
CONFIRM = "confirm"
REASK = "reask"
FLAGGED = "flagged"
DIAGNOSED = "diagnosed"
SPECIALIST_STATUS = "specialist"


class SessionError(ValueError):
    """The action does not apply to the status of the session."""


class Session:
    """Walk the flowchart for one customer report. Jev reads the text, code keeps control."""

    def __init__(
        self,
        chart: Flowchart,
        jev: JevClient,
        report: str,
        extra_questions: bool = True,
        independent_lane: bool = True,
    ):
        self.id = "s_" + secrets.token_hex(2)
        self.chart = chart
        self.jev = jev
        self.report = report
        self.extra_questions = extra_questions
        self.independent_lane = independent_lane
        self.ledger = Ledger()
        self.status: str | None = None
        self.triage: dict | None = None
        self.current: str | None = None
        self.path: list[str] = []
        self.steps: list[dict] = []
        self.scores: dict[str, float] = {}
        self.flag: str | None = None
        self.diagnosis: str | None = None
        self.independent: dict[str, float] = {}
        self._step = 0
        self._known: dict[str, dict] = {}
        self._dismissed: set[str] = set()
        self._confirm: list[dict] = []
        self._last_text = ""
        self._lock = threading.RLock()

    # Jev calls

    def _ask_pair(self, flow: tuple[dict, dict], kind: str) -> dict:
        """Send a flowchart request and, when enabled, request C at the same time."""
        independent = independent_request(self.chart, self.report, self._qa()) if self.independent_lane else None
        with ThreadPoolExecutor(max_workers=2) as pool:
            flow_future = pool.submit(self.jev.ask, *flow)
            ind_future = pool.submit(self.jev.ask, *independent) if independent else None
            flow_result: JevResult = flow_future.result()
            ind_result: JevResult | None = ind_future.result() if ind_future else None
        self.ledger.add(self._step, "flowchart", kind, flow_result)
        if ind_result is not None:
            self.ledger.add(self._step, "independent", "C", ind_result)
            probs = ind_result.answers["diagnosis"]["probabilities"]
            self.independent = {d: p for d, p in probs.items() if d in self.chart.diagnoses}
        return flow_result.answers

    def _qa(self) -> list[dict]:
        qa = []
        for s in self.steps:
            if s["source"] != "user":
                continue
            answer = s["answer_text"]
            if s["outcome"] == "chosen":
                answer = self.chart.nodes[s["node_id"]].options[s["option"]].text
            node = self.chart.nodes[s["node_id"]]
            reference = [o.text for o in node.options.values() if o.id not in NEUTRAL_OPTIONS]
            qa.append({"question": s["question"], "answer": answer, "answer_reference": reference})
        return qa

    # Public actions

    def start(self) -> None:
        """Send request A (and C), then apply the answers that the report gives."""
        with self._lock:
            if self.status is not None:
                raise SessionError("the session has started")
            answers = self._ask_pair(triage_request(self.chart, self.report), "A")
            system = answers["system"]
            self.triage = {
                "system": system["choice"],
                "probabilities": system["probabilities"],
                "confidence": system["confidence"],
            }
            self.scores = scoring.initial_scores(self.chart, system["probabilities"])
            if system["choice"] == NONE or system["choice"] not in self.chart.systems:
                self._finish(SPECIALIST)
                return
            for nid in self.chart.nodes:
                self._remember(nid, answers.get(f"pre_{nid}"))
            self._go_to(self.chart.systems[system["choice"]].entry)
            self._apply_known()

    def answer(self, text: str) -> None:
        """Send request B (and C) for the answer to the current node, then act on the confidence."""
        with self._lock:
            if self.status not in (ASKING, CONFIRM, REASK):
                raise SessionError(f"no question waits for an answer (status {self.status})")
            node = self.chart.nodes[self.current]
            self._step += 1
            step = self._record(node.id, text, "user", None, {}, 0.0, "")
            extra = self.chart.reachable_nodes(node.id)[1 : MAX_EXTRA + 1] if self.extra_questions else []
            try:
                answers = self._ask_pair(answer_request(self.chart, self.report, node.id, text, extra), "B")
            except Exception:
                self.steps.remove(step)
                self._step -= 1
                raise
            self._last_text = text
            self._confirm = []
            for nid in extra:
                self._remember(nid, answers.get(f"extra_{nid}"))

            result = answers["answer"]
            choice, confidence, probs = result["choice"], result["confidence"], result["probabilities"]
            step.update(option=choice, probabilities=probs, confidence=confidence)
            if choice == UNCLEAR or choice not in node.options or confidence < CONFIRM_CONFIDENCE:
                step["outcome"] = REASK
                self.status = REASK
            elif confidence > ACCEPT_CONFIDENCE:
                step["outcome"] = "accepted"
                self._take(node.id, choice, probs)
            else:
                step["outcome"] = CONFIRM
                ranked = sorted(
                    ((o, p) for o, p in probs.items() if o in node.options),
                    key=lambda item: item[1],
                    reverse=True,
                )[:2]
                self._confirm = [
                    {"id": o, "text": node.options[o].text, "probability": p} for o, p in ranked
                ]
                self.status = CONFIRM

    def choose(self, option_id: str) -> None:
        """Take the option that the user selected after a `confirm` status."""
        with self._lock:
            if self.status != CONFIRM:
                raise SessionError(f"nothing to confirm (status {self.status})")
            node = self.chart.nodes[self.current]
            if option_id not in node.options:
                raise SessionError(f"unknown option {option_id!r} for {node.id}")
            self._confirm = []
            self._record(node.id, self._last_text, "user", option_id, {option_id: 1.0}, 1.0, "chosen")
            self._take(node.id, option_id, {option_id: 1.0})

    def accept(self) -> None:
        """Accept the flagged diagnosis and show its fix steps."""
        with self._lock:
            if self.status != FLAGGED:
                raise SessionError(f"no flagged diagnosis (status {self.status})")
            self.diagnosis = self.flag
            self.flag = None
            self.current = None
            self.status = DIAGNOSED

    def keep_going(self) -> None:
        """Continue the flowchart after a flag. The same diagnosis does not flag again."""
        with self._lock:
            if self.status != FLAGGED:
                raise SessionError(f"no flagged diagnosis (status {self.status})")
            self._dismissed.add(self.flag)
            self.flag = None
            self.status = ASKING
            self._apply_known()

    # Flowchart walk

    def _record(self, node_id, text, source, option, probs, confidence, outcome) -> dict:
        step = {
            "step": self._step,
            "node_id": node_id,
            "question": self.chart.nodes[node_id].question,
            "answer_text": text,
            "source": source,
            "option": option,
            "probabilities": probs,
            "confidence": confidence,
            "outcome": outcome,
        }
        self.steps.append(step)
        return step

    def _remember(self, node_id: str, answer: dict | None) -> None:
        """Keep a `pre_` or `extra_` answer when it passes the report limits."""
        if not answer or answer.get("type", "choice") != "choice":
            return
        choice = answer["choice"]
        if (
            answer["probabilities"].get(NOT_STATED, 0.0) < REPORT_MAX_NOT_STATED
            and answer["confidence"] > REPORT_MIN_CONFIDENCE
            and choice in self.chart.nodes[node_id].options
            and choice not in NEUTRAL_OPTIONS
        ):
            self._known[node_id] = answer

    def _apply_known(self) -> None:
        """Apply the known answers, one node after the next, until a node has none."""
        while self.status == ASKING and self.current in self._known:
            answer = self._known.pop(self.current)
            node = self.chart.nodes[self.current]
            self._record(
                node.id,
                node.options[answer["choice"]].text,
                "report",
                answer["choice"],
                answer["probabilities"],
                answer["confidence"],
                "accepted",
            )
            self._take(node.id, answer["choice"], answer["probabilities"], apply_known=False)

    def _take(self, node_id: str, option_id: str, probs: dict[str, float], apply_known: bool = True) -> None:
        """Update the scores with an answer, move along its edge, and check the flag."""
        self.scores = scoring.update(self.chart, self.scores, node_id, probs)
        target = self.chart.nodes[node_id].options[option_id].next
        if self.chart.is_leaf(target):
            self._finish(target)
            return
        self._go_to(target)
        best, score = scoring.top(self.scores, 1)[0]
        if score > scoring.FLAG_THRESHOLD and best not in self._dismissed:
            self.flag = best
            self.status = FLAGGED
            return
        if apply_known:
            self._apply_known()

    def _go_to(self, node_id: str) -> None:
        self.current = node_id
        self.path.append(node_id)
        self.status = ASKING

    def _finish(self, leaf: str) -> None:
        self.current = None
        self.flag = None
        if leaf == SPECIALIST:
            self.status = SPECIALIST_STATUS
        else:
            self.diagnosis = leaf
            self.status = DIAGNOSED
        if self.path:
            self.path.append(leaf)

    # View

    def _scored(self, did: str, score: float) -> dict:
        return {"id": did, "label": self.chart.diagnoses[did].label, "score": score}

    def view(self) -> dict:
        """Return the JSON view of the session for the UI and the CLI."""
        with self._lock:
            current = None
            if self.current is not None and self.status not in (DIAGNOSED, SPECIALIST_STATUS):
                node = self.chart.nodes[self.current]
                current = {
                    "node_id": node.id,
                    "question": node.question,
                    "options": [{"id": o.id, "text": o.text} for o in node.options.values()],
                    "yes_no": node.is_yes_no,
                }
            diagnosis = None
            if self.status == DIAGNOSED and self.diagnosis:
                d = self.chart.diagnoses[self.diagnosis]
                diagnosis = {"id": d.id, "label": d.label, "description": d.description, "fix": list(d.fix)}
            ind_top = scoring.top(self.independent, TOP_INDEPENDENT)
            ind_flag = None
            if ind_top and ind_top[0][1] > scoring.FLAG_THRESHOLD:
                ind_flag = self._scored(*ind_top[0])
            return {
                "id": self.id,
                "report": self.report,
                "status": self.status,
                "triage": self.triage,
                "current": current,
                "confirm_options": list(self._confirm) if self.status == CONFIRM else [],
                "steps": [dict(s) for s in self.steps],
                "scores": [self._scored(d, s) for d, s in scoring.top(self.scores, TOP_SCORES)],
                "flag": self._scored(self.flag, self.scores[self.flag]) if self.status == FLAGGED else None,
                "independent": {
                    "enabled": self.independent_lane,
                    "top": [self._scored(d, s) for d, s in ind_top],
                    "flag": ind_flag,
                },
                "diagnosis": diagnosis,
                "path": list(self.path),
                "mermaid": self.chart.to_mermaid(path=self.path, current=self.current),
                "ledger": self.ledger.to_dict(),
            }
