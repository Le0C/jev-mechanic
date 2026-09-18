"""Tests for the version 2 fault model: the data file, the validator rules and the model queries."""

import json
import math
from pathlib import Path

import pytest

from jev_mechanic.flowchart import NEUTRAL_OPTIONS, FlowchartError
from jev_mechanic.v2.model import DEFAULT_PATH, FaultModel, load, parse

MINI_PATH = Path(__file__).parent / "fixtures" / "mini_v2.json"

# Pairs of diagnoses in different components with almost the same symptoms, and the
# flowchart nodes that separate the two diagnoses.
LOOK_ALIKES = [
    ("parasitic_drain", "alternator_diode_leak", ["q_bat_alt_unplug", "q_alt_drain_unplug"]),
    ("fuel_pump_weak", "injector_clogged", ["q_fp_pressure_load", "q_inj_pressure_load"]),
    ("ignition_coil", "injector_stuck", ["q_ign_coil_swap", "q_inj_coil_swap"]),
    ("radiator_fan_motor", "thermostat_stuck_closed", ["q_fan_top_hose", "q_th_top_hose"]),
    ("abs_wheel_sensor", "wheel_bearing_worn", ["q_abs_play", "q_whl_play"]),
    ("can_wiring_fault", "ecu_power_supply", ["q_can_ecu_supply", "q_ecu_supply"]),
    ("air_in_brakes", "abs_pump_module", ["q_brk_pump"]),
]

# The typical answers from the entry of the primary component to each diagnosis leaf.
TYPICAL_PATHS = {
    "flat_battery": ("battery", [
        ("q_bat_start", "no_start"), ("q_bat_terminals", "no"), ("q_bat_voltage", "below_12_2"),
        ("q_bat_charge_test", "yes"), ("q_bat_history", "no"),
    ]),
    "battery_end_of_life": ("battery", [
        ("q_bat_start", "no_start"), ("q_bat_terminals", "no"), ("q_bat_voltage", "below_12_2"),
        ("q_bat_charge_test", "no"), ("q_bat_age", "yes"),
    ]),
    "battery_terminals": ("battery", [
        ("q_bat_start", "no_start"), ("q_bat_terminals", "yes"), ("q_bat_terminal_drop", "yes"),
    ]),
    "parasitic_drain": ("battery", [
        ("q_bat_start", "flat_after_standing"), ("q_bat_drain", "high"), ("q_bat_alt_unplug", "no"),
    ]),
    "alternator_failure": ("alternator", [
        ("q_alt_symptom", "warning_light"), ("q_alt_run_voltage", "low"), ("q_alt_belt", "no"),
        ("q_alt_field", "yes"), ("q_alt_output", "yes"),
    ]),
    "aux_belt_slip": ("alternator", [
        ("q_alt_symptom", "squeal"), ("q_alt_belt", "yes"), ("q_alt_belt_test", "yes"),
    ]),
    "alternator_diode_leak": ("alternator", [
        ("q_alt_symptom", "flat_after_standing"), ("q_alt_ripple", "no"), ("q_alt_drain_unplug", "yes"),
    ]),
    "starter_motor_worn": ("starter", [
        ("q_sta_symptom", "slow_grind"), ("q_sta_noise", "yes"), ("q_sta_bench", "yes"),
    ]),
    "starter_solenoid": ("starter", [
        ("q_sta_symptom", "click"), ("q_sta_lights", "yes"), ("q_sta_solenoid_volt", "yes"),
        ("q_sta_output_volt", "no"),
    ]),
    "fuel_pump_failed": ("fuel_pump", [
        ("q_fp_symptom", "no_start"), ("q_fp_prime", "yes"), ("q_fp_pressure_crank", "zero"),
    ]),
    "fuel_pump_weak": ("fuel_pump", [
        ("q_fp_symptom", "runs_poorly"), ("q_fp_pressure_idle", "no"), ("q_fp_filter_age", "yes"),
        ("q_fp_filter_swap", "no"),
    ]),
    "fuel_filter_clogged": ("fuel_pump", [
        ("q_fp_symptom", "runs_poorly"), ("q_fp_pressure_idle", "no"), ("q_fp_filter_age", "yes"),
        ("q_fp_filter_swap", "yes"),
    ]),
    "injector_clogged": ("injectors", [
        ("q_inj_symptom", "lean"), ("q_inj_pressure_load", "holds"), ("q_inj_trim", "high"),
        ("q_inj_smoke", "no"), ("q_inj_flow", "yes"),
    ]),
    "injector_stuck": ("injectors", [
        ("q_inj_symptom", "one_cylinder"), ("q_inj_coil_swap", "no"), ("q_inj_balance", "yes"),
        ("q_inj_click", "yes"),
    ]),
    "ignition_coil": ("ignition", [
        ("q_ign_symptom", "misfire"), ("q_ign_one_cyl", "yes"), ("q_ign_coil_swap", "yes"),
        ("q_ign_coil_check", "yes"),
    ]),
    "spark_plugs_worn": ("ignition", [
        ("q_ign_symptom", "misfire"), ("q_ign_one_cyl", "no"), ("q_ign_plugs", "worn"),
        ("q_ign_plug_swap", "yes"),
    ]),
    "crank_sensor": ("ignition", [
        ("q_ign_symptom", "no_start"), ("q_ign_rpm", "yes"), ("q_ign_code", "yes"),
        ("q_ign_crank_signal", "yes"),
    ]),
    "radiator_fan_motor": ("cooling_fan", [
        ("q_fan_when", "traffic"), ("q_fan_runs", "no"), ("q_fan_fuse", "yes"),
        ("q_fan_motor_current", "yes"),
    ]),
    "fan_relay": ("cooling_fan", [
        ("q_fan_when", "traffic"), ("q_fan_runs", "no"), ("q_fan_fuse", "no"), ("q_fan_direct", "yes"),
        ("q_fan_relay_click", "no"),
    ]),
    "thermostat_stuck_closed": ("thermostat", [
        ("q_th_symptom", "overheat"), ("q_th_top_hose", "yes"), ("q_th_temp_diff", "yes"),
        ("q_th_bench", "yes"),
    ]),
    "thermostat_stuck_open": ("thermostat", [
        ("q_th_symptom", "cold"), ("q_th_warm_time", "yes"), ("q_th_radiator_warm", "yes"),
        ("q_th_sensor", "yes"),
    ]),
    "water_pump_leak": ("water_pump", [
        ("q_wp_symptom", "coolant_loss"), ("q_wp_visible", "yes"), ("q_wp_leak_place", "pump"),
        ("q_wp_weep", "yes"),
    ]),
    "water_pump_impeller": ("water_pump", [
        ("q_wp_symptom", "overheat"), ("q_wp_flow", "yes"), ("q_wp_impeller", "yes"),
    ]),
    "coolant_hose_leak": ("water_pump", [
        ("q_wp_symptom", "coolant_loss"), ("q_wp_visible", "yes"), ("q_wp_leak_place", "hose"),
        ("q_wp_hose_check", "yes"),
    ]),
    "head_gasket": ("water_pump", [
        ("q_wp_symptom", "smoke"), ("q_wp_combustion", "yes"), ("q_wp_leakdown", "yes"),
    ]),
    "worn_pads": ("brakes", [("q_brk_symptom", "noise"), ("q_brk_pads", "thin")]),
    "warped_discs": ("brakes", [
        ("q_brk_symptom", "vibration"), ("q_brk_runout", "high"), ("q_brk_hub_clean", "yes"),
    ]),
    "sticking_caliper": ("brakes", [
        ("q_brk_symptom", "pull"), ("q_brk_wheel_temp", "yes"), ("q_brk_wheel_spin", "yes"),
    ]),
    "air_in_brakes": ("brakes", [
        ("q_brk_symptom", "soft_pedal"), ("q_brk_pump", "yes"), ("q_brk_bleed", "yes"),
    ]),
    "abs_wheel_sensor": ("abs", [
        ("q_abs_codes", "wheel_speed"), ("q_abs_live", "yes"), ("q_abs_play", "no"), ("q_abs_sensor", "yes"),
    ]),
    "abs_pump_module": ("abs", [("q_abs_codes", "pump"), ("q_abs_pump_run", "yes"), ("q_abs_valves", "yes")]),
    "wheel_bearing_worn": ("wheel_bearings", [
        ("q_whl_noise", "hum"), ("q_whl_load", "yes"), ("q_whl_spin", "yes"),
    ]),
    "cv_joint_worn": ("wheel_bearings", [
        ("q_whl_noise", "click"), ("q_whl_cv_test", "yes"), ("q_whl_boot", "yes"),
    ]),
    "can_wiring_fault": ("can_bus", [
        ("q_can_symptom", "many_lights"), ("q_can_codes", "yes"), ("q_can_resistance", "r120"),
        ("q_can_wiring", "yes"),
    ]),
    "can_gateway_fault": ("can_bus", [
        ("q_can_symptom", "many_lights"), ("q_can_codes", "yes"), ("q_can_resistance", "r60"),
        ("q_can_gateway", "yes"),
    ]),
    "ecu_power_supply": ("ecu", [
        ("q_ecu_symptom", "no_comm"), ("q_ecu_supply", "no"), ("q_ecu_main_relay", "yes"),
    ]),
    "immobiliser_fault": ("ecu", [
        ("q_ecu_symptom", "security"), ("q_ecu_immo_code", "yes"), ("q_ecu_antenna", "yes"),
    ]),
    "ecu_internal_fault": ("ecu", [
        ("q_ecu_symptom", "no_comm"), ("q_ecu_supply", "yes"), ("q_ecu_can_resistance", "yes"),
        ("q_ecu_internal", "yes"),
    ]),
    "clutch_slip": ("clutch", [
        ("q_clu_symptom", "slip"), ("q_clu_stall_test", "yes"), ("q_clu_adjust", "yes"),
    ]),
    "clutch_hydraulic": ("clutch", [("q_clu_symptom", "pedal"), ("q_clu_fluid", "yes")]),
    "dual_mass_flywheel": ("clutch", [
        ("q_clu_symptom", "noise"), ("q_clu_rattle", "yes"), ("q_clu_dmf_play", "yes"),
    ]),
    "exhaust_leak": ("exhaust", [("q_exh_symptom", "noise"), ("q_exh_smoke_test", "yes")]),
    "catalytic_converter_blocked": ("exhaust", [
        ("q_exh_symptom", "power"), ("q_exh_backpressure", "yes"), ("q_exh_cat_temp", "yes"),
    ]),
    "o2_sensor_fault": ("exhaust", [
        ("q_exh_symptom", "codes"), ("q_exh_o2_code", "yes"), ("q_exh_o2_switch", "yes"),
        ("q_exh_leak_before", "no"),
    ]),
}


@pytest.fixture(scope="module")
def model() -> FaultModel:
    return load(DEFAULT_PATH)


@pytest.fixture(scope="module")
def mini() -> FaultModel:
    return load(MINI_PATH)


@pytest.fixture
def mini_raw() -> dict:
    return json.loads(MINI_PATH.read_text())


def expect_error(raw: dict, fragment: str) -> None:
    with pytest.raises(FlowchartError) as info:
        parse(raw)
    assert any(fragment in e for e in info.value.errors), info.value.errors


def primary(model: FaultModel, diagnosis_id: str) -> str:
    return model.diagnoses[diagnosis_id].systems[0]


def leaves_below(model: FaultModel, target: str) -> set[str]:
    """Return the diagnosis leaves that a walk from `target` can reach."""
    if target in model.diagnoses:
        return {target}
    if target not in model.chart.nodes:
        return set()
    return set().union(*(leaves_below(model, o.next) for o in model.chart.nodes[target].options.values()))


def longest_path(model: FaultModel, node_id: str) -> int:
    """Return the number of questions on the longest path from `node_id` to a leaf."""
    nexts = [o.next for o in model.chart.nodes[node_id].options.values() if o.next in model.chart.nodes]
    return 1 + max((longest_path(model, n) for n in nexts), default=0)


# ---------------------------------------------------------------- the data file


def test_data_file_loads(model):
    assert len(model.components) == 16
    assert 36 <= len(model.diagnoses) <= 46
    assert 55 <= len(model.symptoms) <= 70
    assert 130 <= len(model.chart.nodes) <= 170
    assert 7 <= sum(len(v) for v in model.causes.values()) <= 10


def test_each_component_has_1_to_4_primary_diagnoses(model):
    for component in model.components:
        own = [d for d in model.diagnoses if primary(model, d) == component]
        assert 1 <= len(own) <= 4, (component, own)


def test_each_diagnosis_explains_2_to_5_symptoms(model):
    for diagnosis_id, symptoms in model.explains.items():
        assert 2 <= len(symptoms) <= 5, diagnosis_id
        assert len(set(symptoms)) == len(symptoms), diagnosis_id


def test_each_diagnosis_has_4_to_8_fix_steps(model):
    for diagnosis in model.diagnoses.values():
        assert 4 <= len(diagnosis.fix) <= 8, diagnosis.id


def test_each_node_has_a_not_sure_option(model):
    for node in model.chart.nodes.values():
        assert "not_sure" in node.options, node.id


def test_yes_no_nodes_use_the_standard_option_ids(model):
    for node in model.chart.nodes.values():
        if {"yes", "no"} & set(node.options):
            assert node.is_yes_no, node.id


def test_named_likelihoods_of_a_diagnosis_sum_to_at_most_one(model):
    for node in model.chart.nodes.values():
        named = {d for table in node.evidence.values() for d in table}
        for d in named:
            total = sum(node.likelihood(o, d) for o in node.options if o not in NEUTRAL_OPTIONS)
            assert total <= 1.0 + 1e-9, (node.id, d, total)


def test_each_diagnosis_is_reachable_from_each_of_its_components(model):
    for diagnosis in model.diagnoses.values():
        for component in diagnosis.systems:
            assert diagnosis.id in leaves_below(model, model.components[component].entry), (
                diagnosis.id, component,
            )


@pytest.mark.parametrize("component", sorted(json.loads(DEFAULT_PATH.read_text())["systems"]))
def test_component_branch_is_3_to_8_questions_deep(model, component):
    assert 3 <= longest_path(model, model.components[component].entry) <= 8


def test_each_diagnosis_has_a_typical_path(model):
    assert set(TYPICAL_PATHS) == set(model.diagnoses)


@pytest.mark.parametrize("diagnosis_id", sorted(TYPICAL_PATHS))
def test_typical_path_gives_a_posterior_above_0_9_in_its_component(model, diagnosis_id):
    component, path = TYPICAL_PATHS[diagnosis_id]
    assert component in model.diagnoses[diagnosis_id].systems
    assert model.components[component].entry == path[0][0]
    for (node_id, option_id), following in zip(path, [*path[1:], (diagnosis_id, None)]):
        assert model.chart.nodes[node_id].options[option_id].next == following[0]
    scores = {d: 1.0 for d in model.diagnoses_of(component)}
    for node_id, option_id in path:
        for d in scores:
            scores[d] *= model.chart.nodes[node_id].likelihood(option_id, d)
    posterior = scores[diagnosis_id] / sum(scores.values())
    assert posterior > 0.9, (diagnosis_id, posterior)


@pytest.mark.parametrize("first, second, nodes", LOOK_ALIKES)
def test_look_alike_pair_shares_symptoms_and_has_a_separating_check(model, first, second, nodes):
    assert primary(model, first) != primary(model, second)
    assert len(set(model.explains[first]) & set(model.explains[second])) >= 2
    for node_id in nodes:
        node = model.chart.nodes[node_id]
        reach = {o: leaves_below(model, opt.next) for o, opt in node.options.items() if o not in NEUTRAL_OPTIONS}
        assert any(first in r and second not in r for r in reach.values()), node_id
        assert any(second in r and first not in r for r in reach.values()), node_id
        ratio = max(abs(math.log(node.likelihood(o, first) / node.likelihood(o, second))) for o in reach)
        assert ratio >= math.log(5), (node_id, ratio)


def test_cause_links(model):
    assert "flat_battery" in model.causes["alternator_failure"]
    assert "head_gasket" in model.causes["thermostat_stuck_closed"]
    assert model.caused_by("head_gasket") == ["radiator_fan_motor", "thermostat_stuck_closed"]


# ---------------------------------------------------------------- the validator


def test_mini_fixture_is_valid(mini_raw):
    parse(mini_raw)


def test_rejects_an_unknown_symptom_in_explains(mini_raw):
    mini_raw["diagnoses"]["flat_battery"]["explains"].append("smoke_signal")
    expect_error(mini_raw, "diagnosis flat_battery: explains unknown symptom 'smoke_signal'")


def test_rejects_a_symptom_that_no_diagnosis_explains(mini_raw):
    mini_raw["symptoms"]["rattle"] = {"label": "Rattle", "description": "A rattle under the car"}
    expect_error(mini_raw, "symptom rattle: no diagnosis explains it")


def test_rejects_a_cause_cycle(mini_raw):
    mini_raw["diagnoses"]["flat_battery"]["causes"] = ["alternator_failure"]
    expect_error(mini_raw, "closes a cycle")


def test_rejects_a_diagnosis_that_causes_itself(mini_raw):
    mini_raw["diagnoses"]["fan_failure"]["causes"] = ["fan_failure"]
    expect_error(mini_raw, "diagnosis fan_failure: causes itself")


# ---------------------------------------------------------------- the mini fixture


def test_explained_by(mini):
    assert mini.explained_by("dim_lights") == ["flat_battery", "alternator_failure"]
    assert mini.explained_by("battery_light") == ["alternator_failure", "slipping_belt"]
    assert mini.explained_by("coolant_smell") == ["hose_leak"]
    assert mini.explained_by("no_such_symptom") == []


def test_root_first_puts_each_cause_before_its_effect(mini):
    assert mini.root_first(["flat_battery", "alternator_failure"]) == ["alternator_failure", "flat_battery"]
    assert mini.root_first(["flat_battery", "slipping_belt", "fan_failure"]) == [
        "slipping_belt", "flat_battery", "fan_failure",
    ]


def test_root_first_keeps_unrelated_faults_in_order(mini):
    assert mini.root_first(["fan_failure", "hose_leak"]) == ["fan_failure", "hose_leak"]
    assert mini.root_first(["alternator_failure", "flat_battery"]) == ["alternator_failure", "flat_battery"]


def test_root_first_orders_a_chain_with_a_missing_middle_link(model):
    # spark_plugs_worn causes ignition_coil, and ignition_coil causes catalytic_converter_blocked.
    order = model.root_first(["catalytic_converter_blocked", "spark_plugs_worn"])
    assert order == ["spark_plugs_worn", "catalytic_converter_blocked"]
