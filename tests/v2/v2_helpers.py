"""Shared data for the version 2 engine tests: the mini fault model and scripted Jev answers."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jev_mechanic.jev import make_choice
from jev_mechanic.v2 import model

MINI_V2_PATH = Path(__file__).parent / "fixtures" / "mini_v2.json"

NOT_STATED = make_choice({"not_stated": 1.0}, 1.0)


def mini_raw() -> dict:
    return json.loads(MINI_V2_PATH.read_text())


def mini_model() -> model.FaultModel:
    return model.load(MINI_V2_PATH)


def model_from(raw: dict) -> model.FaultModel:
    return model.parse(copy.deepcopy(raw))


def sure(option: str, confidence: float = 0.95) -> dict:
    return make_choice({option: 0.97, "unclear": 0.03}, confidence)


def noul(value: float) -> dict:
    return {"type": "noul", "noul": value}


def script(symptoms=(), components=None, diagnoses=None, **answers) -> dict:
    """Return a FakeJev script.

    The listed symptoms get a Noul of 0.95, the others 0.05. `components` and
    `diagnoses` map an id to a Noul. `pre_` and `extra_` questions answer `not_stated`.
    """
    base: dict = {"sym_*": noul(0.05), "comp_*": noul(0.1), "diag_*": noul(0.1),
                  "pre_*": NOT_STATED, "extra_*": NOT_STATED}
    for sid in symptoms:
        base[f"sym_{sid}"] = noul(0.95)
    for cid, value in (components or {}).items():
        base[f"comp_{cid}"] = noul(value)
    for did, value in (diagnoses or {}).items():
        base[f"diag_{did}"] = noul(value)
    base.update(answers)
    return base


CASE_FILE = {
    "vehicle": {"make": "VW", "model": "Golf", "year": 2014, "mileage_km": 128400},
    "obd_codes": [
        {"code": "P0562", "description": "System voltage low", "status": "active", "mileage_km": 128350},
        {"code": "P0128", "description": "Coolant temperature below thermostat range", "status": "cleared",
         "mileage_km": 116400},
        {"code": "P0300", "description": "Random misfire", "status": "cleared", "mileage_km": 125400},
    ],
    "freeze_frame": {"battery_voltage_v": 11.6, "coolant_temp_c": 88},
    "service_history": [
        {"date": "2019-03-10", "mileage_km": 60100, "work": "Oil and filter change"},
        {"date": "2020-04-02", "mileage_km": 75300, "work": "Oil and filter change"},
        {"date": "2021-05-20", "mileage_km": 90200, "work": "Brake pads, front"},
        {"date": "2023-06-11", "mileage_km": 105000, "work": "Oil and filter change"},
        {"date": "2025-11-02", "mileage_km": 119800, "work": "Oil and filter change"},
    ],
    "technician_notes": ["Battery light flickered on the road test."],
}
