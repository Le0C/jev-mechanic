"""Check the version 2 cases in data/v2/cases.json against the fault model and the filter.

The walk tests read the answers of the mechanic with a keyword table. The table finds
the option that an answer selects. The walk then follows the flowchart to a leaf.
"""

import json
import re
from pathlib import Path

import pytest

from jev_mechanic import flowchart as fc
from jev_mechanic.v2 import model as fm
from jev_mechanic.v2.casefile import filter_case_file

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "data" / "v2" / "cases.json").read_text())
MODEL = fm.load()
BY_ID = {c["id"]: c for c in CASES}

TAGS = {"cascade", "look_alike", "vague_report", "unclear_answer", "independent_faults", "no_fix"}
SOURCES = {"vehicle", "obd_codes", "freeze_frame", "service_history", "technician_notes"}
CODE_STATUS = {"active", "pending", "history", "cleared"}

# Look-alike pairs: two diagnoses that share two or more symptoms, and that one check separates.
LOOK_ALIKE_PAIRS = [
    ("fan_relay", "radiator_fan_motor"),
    ("abs_wheel_sensor", "wheel_bearing_worn"),
    ("thermostat_stuck_closed", "water_pump_impeller"),
    ("water_pump_leak", "coolant_hose_leak"),
    ("exhaust_leak", "o2_sensor_fault"),
    ("injector_stuck", "ignition_coil"),
    ("can_wiring_fault", "ecu_power_supply"),
    ("alternator_failure", "aux_belt_slip"),
]

# A walk in a component with no fault of the case must end at `specialist` or at a
# true fault. These walks end at a false fault because the flowchart has no healthy
# exit on that path. The report of the case lane lists them as data defects.
KNOWN_FALSE_LEAVES = {
    # q_th_fan "no" goes to radiator_fan_motor, also when the relay is the fault.
    ("yaris_fan_relay", "thermostat"): "radiator_fan_motor",
    # q_fp_pressure_load "holds" goes to injector_clogged, with no specialist exit.
    ("a4_shake_and_eggs", "fuel_pump"): "injector_clogged",
}

# Words that mark an answer that does not say. They select `not_sure`.
UNCLEAR = ("not sure", "can't tell", "hard to say", "no idea", "n/a", "either way")
# Words that mark a deliberately unclear answer on the path to a fault.
DELIBERATE_UNCLEAR = ("hard to say", "either way")
YES = {"yes", "yeah", "yep", "yup"}
NO = {"no", "nope", "nah"}

# Options with keywords. The keyword that occurs first in the answer selects its option.
KEYWORDS = {
    "q_bat_start": {"no_start": ["crank", "click", "won't turn", "slow", "dead"],
                    "flat_after_standing": ["flat again", "sits", "sat", "parked", "standing"]},
    "q_alt_symptom": {"warning_light": ["light", "dim"], "squeal": ["squeal"],
                      "flat_after_standing": ["flat after", "sits", "parked"]},
    "q_sta_symptom": {"click": ["click"], "slow_grind": ["slow", "grind", "whir"],
                      "intermittent": ["sometimes", "hit and miss"]},
    "q_fp_symptom": {"no_start": ["won't fire", "won't start", "doesn't fire"],
                     "runs_poorly": ["stutter", "hesitat", "power", "runs but"]},
    "q_fp_pressure_crank": {"zero": ["zero", " 0 bar"], "low": ["low"], "normal": ["at spec", "on spec"]},
    "q_fp_pressure_load": {"drops": ["drop", "sag", "falls"], "holds": ["hold", "steady"]},
    "q_inj_symptom": {"one_cylinder": [re.compile(r"P030[1-4]"), "one cylinder"],
                      "lean": ["P0171", "P0174", "lean", "P0300", "hesitat"]},
    "q_inj_pressure_load": {"drops": ["drop", "sag", "falls"], "holds": ["hold", "steady"]},
    "q_ign_symptom": {"misfire": ["misfire", "shake", "flash", "rough"],
                      "no_start": ["won't fire", "won't start", "doesn't fire", "cuts out"]},
    "q_ign_plugs": {"worn": ["worn", "fouled", "gap"], "good": ["good", "fine"]},
    "q_fan_when": {"traffic": ["traffic", "idle", "queue"],
                   "road": ["motorway", "open road", "dual carriageway", "at speed"]},
    "q_th_symptom": {"overheat": ["overheat", "in the red", "too hot"], "cold": ["cold", "P0128"]},
    "q_wp_symptom": {"coolant_loss": ["losing", "puddle", "top up", "topping"], "smoke": ["smoke", "bubbl"],
                     "overheat": ["overheat"]},
    "q_wp_leak_place": {"pump": ["pump", "weep"], "hose": ["hose", "clamp"], "other": ["radiator"]},
    "q_brk_symptom": {"noise": ["squeal", "grind"], "vibration": ["shake", "vibrat", "wobble"],
                      "pull": ["pull", "smell", "hot"], "soft_pedal": ["soft", "spongy", "sink"]},
    "q_abs_codes": {"wheel_speed": [re.compile(r"C00[345]\d"), "wheel speed"],
                    "pump": ["C0110", "C0121", "pump", "valve"]},
    "q_whl_noise": {"hum": ["hum", "drone"], "click": ["click", "knock"], "warning": ["light"]},
    "q_can_symptom": {"many_lights": ["lights", "gauges"], "no_start": ["won't start"]},
    "q_clu_symptom": {"slip": ["slip", "revs"], "pedal": ["pedal", "floor"], "noise": ["rattle", "judder"]},
    "q_exh_symptom": {"noise": ["loud", "tick", "blow"], "power": ["power", "rotten egg"],
                      "codes": ["code", "P0420", "P013", "engine light"]},
    "q_ecu_symptom": {"security": ["key light", "security", "immobil"],
                      "no_comm": ["scan tool", "internal"]},
}

# Options that a measurement selects: (unit pattern, function of the value).
NUMBER = r"([+-]?\d+(?:\.\d+)?)"
MEASURED = {
    "q_bat_voltage": (NUMBER + r"\s*V\b",
                      lambda v: "below_12_2" if v < 12.2 else "mid" if v <= 12.4 else "above_12_4"),
    "q_bat_drain": (NUMBER + r"\s*mA", lambda v: "high" if v > 50 else "normal"),
    "q_alt_run_voltage": (NUMBER + r"\s*V\b",
                          lambda v: "low" if v < 13.2 else "high" if v > 15 else "normal"),
    "q_brk_pads": (NUMBER + r"\s*mm", lambda v: "thin" if v < 3 else "ok"),
    "q_brk_runout": (NUMBER + r"\s*mm", lambda v: "high" if v > 0.05 else "normal"),
    "q_inj_trim": (NUMBER + r"\s*%", lambda v: "high" if v > 10 else "normal"),
    "q_can_resistance": (NUMBER + r"\s*Ω", lambda v: "low" if v < 50 else "r60" if v < 90 else "r120"),
}


def resolve(node_id: str, text: str) -> str:
    """Return the option that the answer text selects, with the keyword table."""
    node = MODEL.chart.nodes[node_id]
    lower = text.lower()
    if any(marker in lower for marker in UNCLEAR):
        return "not_sure"
    if node_id in MEASURED:
        pattern, pick = MEASURED[node_id]
        match = re.search(pattern, text)
        assert match, f"{node_id}: no measurement in {text!r}"
        return pick(float(match.group(1)))
    if node_id in KEYWORDS:
        best, best_at = None, None
        for option, words in KEYWORDS[node_id].items():
            for word in words:
                found = word.search(text) if isinstance(word, re.Pattern) else re.search(re.escape(word.lower()), lower)
                if found and (best_at is None or found.start() < best_at):
                    best, best_at = option, found.start()
        assert best is not None, f"{node_id}: no keyword in {text!r}"
        assert best in node.options, f"{node_id}: keyword option {best} is not an option"
        return best
    first = re.split(r"[\s,.]+", lower, maxsplit=1)[0]
    assert set(node.options) >= {"yes", "no"}, f"{node_id}: needs a keyword entry"
    if first in YES:
        return "yes"
    if first in NO:
        return "no"
    raise AssertionError(f"{node_id}: the answer {text!r} does not start with a yes or a no")


def walk(case: dict, component: str) -> tuple[str, list[tuple[str, str]]]:
    """Walk a component branch with the answers of the case. Return the leaf and the path."""
    node_id = MODEL.components[component].entry
    path = []
    while not MODEL.chart.is_leaf(node_id):
        assert node_id in case["answers"], f"{case['id']}: no answer for {node_id}"
        option = resolve(node_id, case["answers"][node_id])
        path.append((node_id, option))
        node_id = MODEL.chart.nodes[node_id].options[option].next
        assert len(path) < 20, f"{case['id']}: the walk in {component} does not end"
    return node_id, path


def symptoms_of(case: dict) -> set[str]:
    return {s for f in case["faults"] for s in MODEL.explains[f]}


def selectable(case: dict) -> list[str]:
    """Return each component that has a diagnosis that explains a symptom of the case."""
    symptoms = symptoms_of(case)
    return [
        c for c in MODEL.components
        if any(set(MODEL.explains[d]) & symptoms for d in MODEL.diagnoses_of(c))
    ]


def tagged(tag: str) -> list[dict]:
    return [c for c in CASES if tag in c["tags"]]


def has_cause_link(faults: list[str]) -> bool:
    return any(effect in faults for f in faults for effect in MODEL.causes[f])


def related(a: str, b: str) -> bool:
    """Return True when a cause chain links the two diagnoses, in either direction."""
    def reaches(start: str, goal: str) -> bool:
        todo, seen = [start], set()
        while todo:
            d = todo.pop()
            if d == goal:
                return True
            if d not in seen:
                seen.add(d)
                todo.extend(MODEL.causes[d])
        return False
    return reaches(a, b) or reaches(b, a)


# Shape and ids


def test_case_ids_are_unique():
    assert len(BY_ID) == len(CASES) == 20


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_shape(case):
    assert set(case) == {"id", "title", "date", "faults", "tags", "report", "case_file", "answers"}
    assert 1 <= len(case["faults"]) <= fm.MAX_FAULTS
    assert len(set(case["faults"])) == len(case["faults"])
    for fault in case["faults"]:
        assert fault in MODEL.diagnoses, fault
    for tag in case["tags"]:
        assert tag in TAGS, tag
    for node_id in case["answers"]:
        assert node_id in MODEL.chart.nodes, node_id
        assert case["answers"][node_id].strip()
    assert set(case["case_file"]) == SOURCES
    for code in case["case_file"]["obd_codes"]:
        assert code["status"] in CODE_STATUS
        assert re.fullmatch(r"[PBCU]\d{4}", code["code"]), code["code"]
    for key, value in case["case_file"]["freeze_frame"].items():
        assert isinstance(value, (int, float)), key
        assert re.search(r"_(v|c|kmh|rpm|pct|bar|kpa|mg|psi)$", key) or key.endswith("_rpm"), key


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_report_is_two_to_six_sentences(case):
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", case["report"].strip()) if s]
    assert 2 <= len(sentences) <= 6, sentences
    for fault in case["faults"]:
        assert MODEL.diagnoses[fault].label.lower() not in case["report"].lower()


# Counts


def test_fault_counts():
    sizes = [len(c["faults"]) for c in CASES]
    assert (sizes.count(1), sizes.count(2), sizes.count(3)) == (6, 9, 5)


def test_cascade_cases_hold_a_cause_link():
    cases = tagged("cascade")
    assert len(cases) >= 7
    for case in cases:
        assert has_cause_link(case["faults"]), case["id"]


def test_look_alike_cases_hold_a_pair_from_the_data():
    for a, b in LOOK_ALIKE_PAIRS:
        assert len(set(MODEL.explains[a]) & set(MODEL.explains[b])) >= 2, (a, b)
    cases = tagged("look_alike")
    assert len(cases) >= 4
    for case in cases:
        faults = set(case["faults"])
        twins = [(a, b) for a, b in LOOK_ALIKE_PAIRS if (a in faults) != (b in faults)]
        assert twins, f"{case['id']}: no fault with a look-alike twin"


def test_independent_cases_hold_two_unrelated_faults():
    cases = tagged("independent_faults")
    assert len(cases) >= 3
    for case in cases:
        faults = case["faults"]
        pairs = [(a, b) for i, a in enumerate(faults) for b in faults[i + 1:] if not related(a, b)]
        assert pairs, case["id"]


def test_vague_and_unclear_counts():
    assert len(tagged("vague_report")) == 3
    assert len(tagged("unclear_answer")) == 2


def test_component_coverage():
    covered = {s for c in CASES for f in c["faults"] for s in MODEL.diagnoses[f].systems}
    assert len(covered) >= 12, sorted(covered)


# Answers and walks


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_each_node_of_each_selectable_component_has_an_answer(case):
    for component in selectable(case):
        for node_id in MODEL.chart.reachable_nodes(MODEL.components[component].entry):
            assert node_id in case["answers"], f"{component}: no answer for {node_id}"
            resolve(node_id, case["answers"][node_id])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_each_true_fault_is_reachable(case):
    leaves = {c: walk(case, c)[0] for c in selectable(case)}
    for fault in case["faults"]:
        homes = [c for c in MODEL.diagnoses[fault].systems if c in leaves]
        assert any(leaves[c] == fault for c in homes), f"{fault}: walks end at {leaves}"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_walks_end_at_specialist_or_at_a_true_fault(case):
    for component in selectable(case):
        leaf, path = walk(case, component)
        if leaf == fc.SPECIALIST or leaf in case["faults"]:
            continue
        assert KNOWN_FALSE_LEAVES.get((case["id"], component)) == leaf, f"{component} ends at {leaf}: {path}"


def test_known_false_leaves_still_occur():
    for (case_id, component), leaf in KNOWN_FALSE_LEAVES.items():
        assert walk(BY_ID[case_id], component)[0] == leaf


@pytest.mark.parametrize("case", tagged("unclear_answer"), ids=lambda c: c["id"])
def test_unclear_answer_is_on_a_fault_path(case):
    hits = []
    for component in selectable(case):
        leaf, path = walk(case, component)
        if leaf not in case["faults"]:
            continue
        for node_id, option in path:
            text = case["answers"][node_id].lower()
            if option == "not_sure" and any(m in text for m in DELIBERATE_UNCLEAR):
                hits.append(node_id)
    assert hits


# Case file and filter


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_filter_removes_old_entries(case):
    kept, removed = filter_case_file(case["case_file"], case["date"])
    sources = {r["source"] for r in removed}
    assert sources == {"obd_codes", "service_history"}, removed
    assert all(r["entry"]["status"] == "cleared" for r in removed if r["source"] == "obd_codes")
    assert kept["obd_codes"] and kept["service_history"] and kept["technician_notes"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_file_dates_and_mileage_are_consistent(case):
    mileage = case["case_file"]["vehicle"]["mileage_km"]
    for code in case["case_file"]["obd_codes"]:
        assert code["mileage_km"] <= mileage
    history = case["case_file"]["service_history"]
    assert [e["date"] for e in history] == sorted(e["date"] for e in history)
    assert all(e["date"] <= case["date"] and e["mileage_km"] <= mileage for e in history)
    assert [e["mileage_km"] for e in history] == sorted(e["mileage_km"] for e in history)
