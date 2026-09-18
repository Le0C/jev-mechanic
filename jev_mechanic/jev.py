"""Clients that send questions to Jev and return the answers in the HTTP API shape."""

from __future__ import annotations

import fnmatch
import json
import math
import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol

MODEL = "jev-latest"
FAKE_MODEL = "jev-fake"
FAKE_SECONDS = 0.05


@dataclass
class JevResult:
    answers: dict[str, dict]
    input_tokens: int
    output_tokens: int
    model: str
    seconds: float
    request_id: str | None = None


class JevClient(Protocol):
    def ask(self, state: dict | str, questions: dict[str, dict]) -> JevResult: ...


def answer_dict(answer) -> dict:
    """Convert one SDK answer object to the HTTP API answer dict."""
    if hasattr(answer, "choice"):
        return {
            "type": "choice",
            "choice": answer.choice,
            "probabilities": dict(answer.probabilities),
            "confidence": answer.confidence,
        }
    if hasattr(answer, "noul"):
        return {"type": "noul", "noul": answer.noul}
    if hasattr(answer, "score"):
        return {
            "type": "score",
            "score": answer.score,
            "probabilities": dict(answer.probabilities),
            "confidence": answer.confidence,
        }
    raise TypeError(f"unknown answer type {type(answer).__name__}")


class LiveJev:
    """Send questions to the TypeSafe API through the synchronous SDK client."""

    def __init__(self, model: str = MODEL, client=None):
        if client is None:
            from typesafe_sdk import TypeSafeClient

            client = TypeSafeClient(model=model)
        self._client = client

    def ask(self, state: dict | str, questions: dict[str, dict]) -> JevResult:
        started = time.perf_counter()
        response = self._client.system_one(state=state, questions=questions)
        seconds = time.perf_counter() - started
        return JevResult(
            answers={qid: answer_dict(a) for qid, a in response.answers.items()},
            input_tokens=response.usage.input_tokens or 0,
            output_tokens=response.usage.output_tokens or 0,
            model=response.model,
            seconds=seconds,
            request_id=getattr(response, "request_id", None),
        )


def spread_confidence(probabilities: dict[str, float]) -> float:
    """Return 1 minus the normalized entropy of a distribution."""
    values = [p for p in probabilities.values() if p > 0]
    if len(probabilities) < 2 or not values:
        return 1.0
    entropy = -sum(p * math.log(p) for p in values)
    return max(0.0, 1.0 - entropy / math.log(len(probabilities)))


def make_choice(probabilities: dict[str, float], confidence: float | None = None) -> dict:
    """Return a Choice answer dict. The top option is the choice."""
    total = sum(probabilities.values()) or 1.0
    probs = {k: v / total for k, v in probabilities.items()}
    choice = max(probs, key=probs.get)
    if confidence is None:
        confidence = spread_confidence(probs)
    return {"type": "choice", "choice": choice, "probabilities": probs, "confidence": confidence}


Scripted = dict | list | Callable[[dict | str, dict], dict]


class FakeJev:
    """Return scripted or random answers, with no network call.

    A script value is an answer dict, a list of answer dicts (one for each call, the
    last one repeats), or a function of `(state, question)`. A script key can be a
    shell pattern, such as `pre_*`. An exact key wins over a pattern.
    """

    def __init__(
        self, script: dict[str, Scripted] | None = None, seed: int | None = None, delay: float = 0.0
    ):
        self.script = dict(script or {})
        self.delay = delay
        self.calls: list[tuple[dict | str, dict[str, dict]]] = []
        self._uses: dict[str, int] = {}
        self._random = random.Random(seed)
        self._lock = threading.Lock()

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def ask(self, state: dict | str, questions: dict[str, dict]) -> JevResult:
        started = time.perf_counter()
        with self._lock:
            self.calls.append((state, questions))
            answers = {qid: self._answer(qid, state, q) for qid, q in questions.items()}
        if self.delay:
            time.sleep(self.delay)
            seconds = time.perf_counter() - started
        else:
            seconds = FAKE_SECONDS
        size = len(json.dumps({"state": state, "questions": questions}))
        return JevResult(
            answers=answers,
            input_tokens=size // 4,
            output_tokens=10 * len(questions),
            model=FAKE_MODEL,
            seconds=seconds,
            request_id=None,
        )

    def _lookup(self, qid: str) -> Scripted | None:
        if qid in self.script:
            return self.script[qid]
        for pattern, value in self.script.items():
            if fnmatch.fnmatchcase(qid, pattern):
                return value
        return None

    def _answer(self, qid: str, state: dict | str, question: dict) -> dict:
        value = self._lookup(qid)
        if value is None:
            return self._random_answer(question)
        if callable(value):
            value = value(state, question)
        elif isinstance(value, list):
            index = self._uses.get(qid, 0)
            self._uses[qid] = index + 1
            value = value[min(index, len(value) - 1)]
        return _complete(value)

    def _random_answer(self, question: dict) -> dict:
        if question.get("type") == "noul":
            return {"type": "noul", "noul": self._random.random()}
        options = list(question.get("criteria") or {"yes": None, "no": None})
        weights = {o: self._random.random() ** 3 for o in options}
        return make_choice(weights)


def _complete(answer: dict) -> dict:
    """Fill the `type`, `choice` and `confidence` of a partial scripted answer."""
    answer = dict(answer)
    if answer.get("type", "choice") == "noul" or "noul" in answer:
        return {"type": "noul", "noul": answer["noul"]}
    full = make_choice(answer["probabilities"], answer.get("confidence"))
    if "choice" in answer:
        full["choice"] = answer["choice"]
    return full
