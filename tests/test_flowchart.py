"""Tests for the flowchart data file and the flowchart module."""

import copy
import json
from pathlib import Path

import pytest

from jev_mechanic.flowchart import (
    DEFAULT_PATH,
    NEUTRAL_OPTIONS,
    SPECIALIST,
    Flowchart,
    FlowchartError,
    load,
    parse,
)

MINI_PATH = Path(__file__).parent / "fixtures" / "mini_flowchart.json"

# The typical answers from a system entry to each diagnosis leaf: (system, [(node, option), ...]).
TYPICAL_PATHS = {
    "flat_battery": ("no_start", [
        ("q_ns_key_turn", "slow_crank"), ("q_ns_voltage", "below_12_2"), ("q_ns_load_test", "yes"),
    ]),
    "battery_terminals": ("no_start", [
        ("q_ns_key_turn", "nothing"), ("q_ns_dash_lights", "no"), ("q_ns_terminals", "yes"),
    ]),
    "starter_motor": ("no_start", [
        ("q_ns_key_turn", "click_only"), ("q_ns_lights_dim", "no"), ("q_ns_starter_voltage", "yes"),
    ]),
    "immobiliser_fault": ("no_start", [
        ("q_ns_key_turn", "normal_crank"), ("q_ns_immobiliser", "yes"),
    ]),
    "fuel_pump": ("no_start", [
        ("q_ns_key_turn", "normal_crank"), ("q_ns_immobiliser", "no"), ("q_ns_fuel_pump_hum", "no"),
    ]),
    "crank_sensor": ("no_start", [
        ("q_ns_key_turn", "normal_crank"), ("q_ns_immobiliser", "no"),
        ("q_ns_fuel_pump_hum", "yes"), ("q_ns_rpm_signal", "no"),
    ]),
    "battery_end_of_life": ("no_start", [
        ("q_ns_key_turn", "slow_crank"), ("q_ns_voltage", "below_12_2"), ("q_ns_load_test", "no"),
    ]),
    "alternator_failure": ("charge", [
        ("q_ch_symptom", "warning_light"), ("q_ch_running_voltage", "low"),
        ("q_ch_belt", "no"), ("q_ch_terminals", "no"),
    ]),
    "aux_belt_slip": ("charge", [("q_ch_symptom", "squeal"), ("q_ch_belt", "yes")]),
    "parasitic_drain": ("charge", [("q_ch_symptom", "flat_overnight"), ("q_ch_drain", "high")]),
    "ignition_coil": ("runs_badly", [
        ("q_rb_symptom", "misfire"), ("q_rb_one_cylinder", "yes"), ("q_rb_coil_swap", "yes"),
    ]),
    "spark_plugs": ("runs_badly", [
        ("q_rb_symptom", "misfire"), ("q_rb_one_cylinder", "no"), ("q_rb_plugs", "worn"),
    ]),
    "vacuum_leak": ("runs_badly", [("q_rb_symptom", "rough_idle"), ("q_rb_idle_hiss", "yes")]),
    "maf_sensor": ("runs_badly", [
        ("q_rb_symptom", "no_power"), ("q_rb_fuel_pressure", "holds"), ("q_rb_maf", "yes"),
    ]),
    "fuel_filter": ("runs_badly", [
        ("q_rb_symptom", "no_power"), ("q_rb_fuel_pressure", "drops"), ("q_rb_filter_age", "overdue"),
    ]),
    "egr_valve": ("runs_badly", [
        ("q_rb_symptom", "rough_idle"), ("q_rb_idle_hiss", "no"), ("q_rb_egr", "yes"),
    ]),
    "thermostat_stuck": ("cooling", [("q_co_symptom", "overheat_road"), ("q_co_top_hose", "no")]),
    "coolant_hose_leak": ("cooling", [
        ("q_co_symptom", "coolant_loss"), ("q_co_visible_leak", "yes"), ("q_co_leak_place", "hose"),
    ]),
    "water_pump": ("cooling", [
        ("q_co_symptom", "coolant_loss"), ("q_co_visible_leak", "yes"), ("q_co_leak_place", "pump"),
    ]),
    "radiator_fan": ("cooling", [("q_co_symptom", "overheat_idle"), ("q_co_fan", "no")]),
    "head_gasket": ("cooling", [("q_co_symptom", "white_smoke"), ("q_co_combustion_test", "yes")]),
    "worn_pads": ("brakes", [("q_br_symptom", "noise"), ("q_br_pads", "thin")]),
    "warped_discs": ("brakes", [("q_br_symptom", "vibration"), ("q_br_runout", "high")]),
    "sticking_caliper": ("brakes", [("q_br_symptom", "pull"), ("q_br_wheel_temp", "yes")]),
    "air_in_brakes": ("brakes", [("q_br_symptom", "soft_pedal"), ("q_br_pedal_pump", "yes")]),
}


@pytest.fixture(scope="module")
def chart() -> Flowchart:
    return load(DEFAULT_PATH)


@pytest.fixture(scope="module")
def mini() -> Flowchart:
    return load(MINI_PATH)


@pytest.fixture
def mini_raw() -> dict:
    return json.loads(MINI_PATH.read_text())


def hard_posterior(chart: Flowchart, system: str, path: list[tuple[str, str]]) -> dict[str, float]:
    """Return the diagnosis scores after hard triage onto `system` and hard answers along `path`."""
    scores = {d: dx.prior for d, dx in chart.diagnoses.items() if system in dx.systems}
    for node_id, option_id in path:
        for d in scores:
            scores[d] *= chart.nodes[node_id].likelihood(option_id, d)
    total = sum(scores.values())
    return {d: v / total for d, v in scores.items()}


# ---------------------------------------------------------------- the data file


def test_data_file_loads(chart):
    assert len(chart.systems) == 5
    assert len(chart.diagnoses) >= 25
    assert 30 <= len(chart.nodes) <= 45


def test_each_diagnosis_has_4_to_8_fix_steps(chart):
    for diagnosis in chart.diagnoses.values():
        assert 4 <= len(diagnosis.fix) <= 8, diagnosis.id


def test_each_path_ends_at_a_leaf(chart):
    def walk(node_id, seen):
        assert node_id not in seen, f"cycle at {node_id}"
        for option in chart.nodes[node_id].options.values():
            if option.next in chart.nodes:
                walk(option.next, seen | {node_id})
            else:
                assert chart.is_leaf(option.next)

    for system in chart.systems.values():
        walk(system.entry, frozenset())


def test_each_diagnosis_is_reachable_from_each_of_its_systems(chart):
    for diagnosis in chart.diagnoses.values():
        for system_id in diagnosis.systems:
            nodes = chart.reachable_nodes(chart.systems[system_id].entry)
            leaves = {o.next for n in nodes for o in chart.nodes[n].options.values()}
            assert diagnosis.id in leaves, (diagnosis.id, system_id)


def test_yes_no_nodes_use_the_standard_option_ids(chart):
    for node in chart.nodes.values():
        if {"yes", "no"} & set(node.options):
            assert node.is_yes_no, node.id


def test_named_likelihoods_of_a_diagnosis_sum_to_at_most_one(chart):
    for node in chart.nodes.values():
        named = {d for table in node.evidence.values() for d in table}
        for d in named:
            total = sum(
                node.likelihood(o, d) for o in node.options if o not in NEUTRAL_OPTIONS
            )
            assert total <= 1.0 + 1e-9, (node.id, d, total)


def test_each_diagnosis_has_a_typical_path(chart):
    assert set(TYPICAL_PATHS) == set(chart.diagnoses)


@pytest.mark.parametrize("diagnosis_id", sorted(TYPICAL_PATHS))
def test_typical_path_gives_a_posterior_above_0_9(chart, diagnosis_id):
    system, path = TYPICAL_PATHS[diagnosis_id]
    assert chart.systems[system].entry == path[0][0]
    for (node_id, option_id), following in zip(path, [*path[1:], (diagnosis_id, None)]):
        assert chart.nodes[node_id].options[option_id].next == following[0]
    scores = hard_posterior(chart, system, path)
    assert scores[diagnosis_id] > 0.9, scores


# ---------------------------------------------------------------- the validator


def expect_error(raw: dict, fragment: str) -> None:
    with pytest.raises(FlowchartError) as info:
        parse(raw)
    assert any(fragment in e for e in info.value.errors), info.value.errors


def test_mini_fixture_is_valid(mini_raw):
    parse(mini_raw)


def test_rejects_an_unknown_next(mini_raw):
    mini_raw["nodes"]["q_key_turn"]["options"]["slow_crank"]["next"] = "q_missing"
    expect_error(mini_raw, "next 'q_missing' is not a node or a leaf")


def test_rejects_an_unreachable_node(mini_raw):
    mini_raw["nodes"]["q_orphan"] = {
        "question": "Is this node reachable?",
        "options": {
            "yes": {"text": "Yes", "next": "flat_battery"},
            "no": {"text": "No", "next": SPECIALIST},
        },
    }
    expect_error(mini_raw, "node q_orphan: not reachable")


def test_rejects_a_likelihood_of_zero(mini_raw):
    mini_raw["nodes"]["q_brake_noise"]["evidence"]["squeal"]["warped_discs"] = 0
    expect_error(mini_raw, "likelihood 0 is not in (0, 1]")


@pytest.mark.parametrize("reserved", ["unclear", "not_stated"])
def test_rejects_a_reserved_option_id(mini_raw, reserved):
    options = mini_raw["nodes"]["q_headlights_dim"]["options"]
    options[reserved] = options.pop("not_sure")
    expect_error(mini_raw, f"option id '{reserved}' is reserved")


def test_error_lists_every_problem(mini_raw):
    raw = copy.deepcopy(mini_raw)
    raw["nodes"]["q_key_turn"]["options"]["slow_crank"]["next"] = "q_missing"
    raw["nodes"]["q_brake_noise"]["evidence"]["squeal"]["warped_discs"] = 0
    with pytest.raises(FlowchartError) as info:
        parse(raw)
    assert len(info.value.errors) == 2


# ---------------------------------------------------------------- the mini fixture


def test_reachable_nodes(mini):
    assert mini.reachable_nodes("q_key_turn") == ["q_key_turn", "q_headlights_dim"]
    assert mini.reachable_nodes("q_brake_noise") == ["q_brake_noise"]
    assert mini.reachable_nodes("flat_battery") == []


def test_is_yes_no(mini):
    assert mini.nodes["q_headlights_dim"].is_yes_no
    assert not mini.nodes["q_key_turn"].is_yes_no
    assert not mini.nodes["q_brake_noise"].is_yes_no


def test_likelihood(mini):
    node = mini.nodes["q_key_turn"]
    assert node.likelihood("click_only", "starter_motor") == 0.8
    assert node.likelihood("not_sure", "starter_motor") == 1.0
    assert node.likelihood("click_only", "worn_pads") == 0.1


def test_to_mermaid(mini):
    text = mini.to_mermaid()
    lines = text.splitlines()
    assert lines[0] == "flowchart TD"
    assert '  sys_no_start(["No start"]) --> q_key_turn' in lines
    assert '  q_key_turn -->|"click only"| q_headlights_dim' in lines
    assert '  specialist["Refer to a specialist"]' in lines
    assert not any(line.startswith("  class ") and "onpath" in line for line in lines)


def test_to_mermaid_marks_the_path_and_the_current_node(mini):
    lines = mini.to_mermaid(path=["q_key_turn", "q_headlights_dim"], current="q_headlights_dim")
    lines = lines.splitlines()
    assert "  class q_key_turn onpath" in lines
    assert "  class q_headlights_dim current" in lines


def test_to_mermaid_of_the_data_file_names_every_node(chart):
    text = chart.to_mermaid()
    for node_id in chart.nodes:
        assert f"  {node_id}{{" in text


# ---------------------------------------------------------------- the scenarios

SCENARIOS_PATH = DEFAULT_PATH.parent / "scenarios.json"


def test_scenarios_match_the_flowchart(chart):
    cases = json.loads(SCENARIOS_PATH.read_text())
    assert len(cases) == 15
    assert len({c["id"] for c in cases}) == 15
    systems = set()
    for case in cases:
        assert case["report"] and case["title"], case["id"]
        diagnosis = chart.diagnoses[case["expected"]]
        systems.update(diagnosis.systems)
        assert set(case["answers"]) <= set(chart.nodes), case["id"]
        assert all(text.strip() for text in case["answers"].values()), case["id"]
        covered = [
            s for s in diagnosis.systems
            if set(chart.reachable_nodes(chart.systems[s].entry)) <= set(case["answers"])
        ]
        assert covered, f"{case['id']}: no system of {diagnosis.id} has an answer for each node"
    assert systems == set(chart.systems)
