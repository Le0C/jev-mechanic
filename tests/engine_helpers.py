"""Shared data for the engine tests: the mini flowchart and scripted Jev answers."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jev_mechanic import flowchart
from jev_mechanic.jev import make_choice

MINI_PATH = Path(__file__).parent / "fixtures" / "mini_flowchart.json"


def mini_raw() -> dict:
    return json.loads(MINI_PATH.read_text())


def mini_chart() -> flowchart.Flowchart:
    return flowchart.load(MINI_PATH)


def chart_from(raw: dict) -> flowchart.Flowchart:
    return flowchart.parse(copy.deepcopy(raw))


def choice(probabilities: dict[str, float], confidence: float) -> dict:
    return make_choice(probabilities, confidence)


NOT_STATED = choice({"not_stated": 1.0}, 1.0)
NO_START = choice({"no_start": 1.0, "brakes": 0.0, "none": 0.0}, 1.0)
UNKNOWN_DIAGNOSIS = choice({"none": 1.0}, 1.0)


def script(**answers) -> dict:
    """Return a FakeJev script. Unlisted `pre_` and `extra_` questions answer `not_stated`."""
    base = {"system": NO_START, "pre_*": NOT_STATED, "extra_*": NOT_STATED, "diagnosis": UNKNOWN_DIAGNOSIS}
    base.update(answers)
    return base
