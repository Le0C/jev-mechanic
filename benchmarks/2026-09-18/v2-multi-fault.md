# Version 2 harness report

Run at 2026-09-18T12:41:52 on `jev-1.13.0`, 127 s, 1 case(s) at the same time. Prices: Jev $0.042 and Opus 5 $5.00 for each million input tokens.

The Opus 5 column prices the Jev input tokens at the Opus 5 input price. It is a lower limit. It has no output tokens and no tokenizer difference.

## Mode: report

| Measure | Value |
| --- | --- |
| Exact fault set, loop | 8 / 20 |
| Fault precision, loop | 0.83 |
| Fault recall, loop | 0.64 |
| Cascade fix order root first | 2 / 2 |
| Exact fault set, independent lane | 8 / 20 |
| Fault precision, independent lane | 0.74 |
| Fault recall, independent lane | 0.74 |
| User answers, total | 77 |
| Answers from the evidence, total | 22 |
| Errors | 0 |
| Requests for each case | 11.8 |
| Input tokens for each case | 60378 |
| Jev cost for each case | $0.002536 |
| Opus 5 cost for each case, same tokens | $0.3019 |
| Jev cost for 1,000 cases | $2.5359 |
| Opus 5 cost for 1,000 cases | $301.8897 |
| Compute time for each case | 5.68 s |
| Wait time for each case | 3.46 s |

| Kind | Requests | Mean input tokens | Min s | Median s | p95 s | Max s |
| --- | --- | --- | --- | --- | --- | --- |
| A | 41 | 2654 | 0.27 | 0.32 | 0.73 | 1.23 |
| B | 77 | 1583 | 0.25 | 0.31 | 0.38 | 1.23 |
| C | 97 | 7564 | 0.29 | 0.35 | 1.03 | 1.30 |
| E | 20 | 12159 | 1.15 | 1.23 | 1.49 | 1.59 |

| Case | Tags | Expected | Found (loop) | Independent | Loops | User / evidence answers | Confirm / reask | Tokens | Wait s | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yaris_fan_relay | look_alike | fan_relay | fan_relay, radiator_fan_motor WRONG | fan_relay ok | 2 | 4 / 2 | 0 / 0 | 59256 | 3.24 |  |
| octavia_wheel_bearing | look_alike | wheel_bearing_worn | wheel_bearing_worn ok | wheel_bearing_worn ok | 1 | 1 / 0 | 0 / 0 | 31654 | 1.88 |  |
| corsa_not_right | vague_report | thermostat_stuck_open | thermostat_stuck_open ok | thermostat_stuck_open ok | 4 | 10 / 0 | 0 / 0 | 124437 | 6.98 |  |
| zafira_engine_light | look_alike | o2_sensor_fault | - WRONG | - WRONG | 0 | 0 / 0 | 0 / 0 | 19472 | 1.23 |  |
| berlingo_hill_revs | unclear_answer | clutch_slip | clutch_slip, o2_sensor_fault, fuel_filter_clogged WRONG | clutch_slip, fuel_pump_weak WRONG | 3 | 9 / 1 | 0 / 0 | 109378 | 5.48 | no answer for q_exh_symptom, q_exh_o2_code, q_exh_o2_switch, q_exh_leak_before, q_fp_symptom, q_fp_pressure_idle, q_fp_pressure_load, q_fp_filter_age, q_fp_filter_swap |
| micra_key_light |  | immobiliser_fault | immobiliser_fault ok | immobiliser_fault ok | 1 | 0 / 1 | 0 / 0 | 21959 | 1.52 |  |
| golf_alternator_battery | cascade | alternator_failure, flat_battery | flat_battery, alternator_failure ok | flat_battery WRONG | 3 | 7 / 1 | 0 / 0 | 95093 | 4.70 | unexplained: old_battery, starter_intermittent |
| focus_motorway_overheat | cascade, look_alike | thermostat_stuck_closed, head_gasket | - WRONG | head_gasket, coolant_hose_leak WRONG | 1 | 2 / 0 | 0 / 2 | 42495 | 2.30 | stuck at q_wp_symptom unexplained: overheat_on_road, coolant_loss, sweet_smell, white_smoke |
| c3_pull_and_click | independent_faults | sticking_caliper, cv_joint_worn | sticking_caliper, cv_joint_worn ok | sticking_caliper, cv_joint_worn, worn_pads WRONG | 2 | 0 / 2 | 0 / 0 | 24833 | 1.82 |  |
| passat_overtake_stutter | cascade, unclear_answer | fuel_filter_clogged, fuel_pump_weak | fuel_pump_weak WRONG | fuel_filter_clogged, fuel_pump_weak ok | 1 | 3 / 1 | 1 / 0 | 48123 | 2.42 |  |
| scenic_traffic_steam | cascade | radiator_fan_motor, head_gasket | radiator_fan_motor, head_gasket ok | head_gasket WRONG | 2 | 5 / 2 | 0 / 0 | 68671 | 3.55 |  |
| transit_monday_mornings | cascade, vague_report | parasitic_drain, flat_battery | parasitic_drain WRONG | parasitic_drain, flat_battery ok | 2 | 4 / 1 | 0 / 2 | 61114 | 3.74 | stuck at q_sta_symptom unexplained: starter_intermittent |
| polo_grind_and_blow | independent_faults | worn_pads, exhaust_leak | worn_pads, exhaust_leak ok | worn_pads, exhaust_leak ok | 2 | 0 / 2 | 0 / 0 | 24859 | 1.83 |  |
| megane_puddle_abs | independent_faults, look_alike | coolant_hose_leak, abs_wheel_sensor | coolant_hose_leak, abs_wheel_sensor ok | abs_wheel_sensor, coolant_hose_leak ok | 3 | 7 / 1 | 0 / 0 | 91559 | 4.82 |  |
| fabia_rain_lights_rattle | independent_faults | can_wiring_fault, dual_mass_flywheel | can_wiring_fault, dual_mass_flywheel, injector_clogged WRONG | can_wiring_fault, can_gateway_fault, dual_mass_flywheel, immobiliser_fault, ecu_internal_fault WRONG | 5 | 12 / 2 | 0 / 0 | 145913 | 8.78 | no answer for q_inj_symptom, q_inj_pressure_load, q_inj_trim, q_inj_smoke, q_inj_flow |
| a4_shake_and_eggs | cascade | spark_plugs_worn, ignition_coil, catalytic_converter_blocked | catalytic_converter_blocked, spark_plugs_worn WRONG | spark_plugs_worn, catalytic_converter_blocked WRONG | 2 | 1 / 2 | 0 / 0 | 34078 | 2.41 |  |
| vito_flat_and_squeal | cascade, independent_faults | alternator_diode_leak, flat_battery, aux_belt_slip | alternator_diode_leak WRONG | alternator_diode_leak, alternator_failure, aux_belt_slip, flat_battery WRONG | 2 | 5 / 2 | 0 / 0 | 67343 | 3.92 | unexplained: old_battery, belt_squeal |
| qashqai_steam_and_squeal | cascade, independent_faults | thermostat_stuck_closed, head_gasket, worn_pads | - WRONG | head_gasket, worn_pads, coolant_hose_leak, water_pump_leak WRONG | 1 | 2 / 0 | 0 / 2 | 42535 | 2.21 | stuck at q_wp_symptom unexplained: overheat_gauge, overheat_on_road, coolant_temp_high, coolant_loss, brake_squeal, brake_warning_light |
| discovery_pedals_and_light | independent_faults | abs_pump_module, clutch_hydraulic, o2_sensor_fault | abs_pump_module, clutch_hydraulic, ecu_internal_fault WRONG | air_in_brakes, clutch_hydraulic WRONG | 3 | 4 / 2 | 0 / 0 | 63206 | 4.29 | unexplained: many_warning_lights no answer for q_ecu_symptom, q_ecu_supply, q_ecu_can_resistance, q_ecu_internal |
| kangoo_not_itself | cascade, vague_report | alternator_failure, flat_battery, starter_motor_worn | starter_motor_worn WRONG | starter_motor_worn WRONG | 1 | 1 / 0 | 0 / 0 | 31581 | 2.05 |  |

## Mode: case_file

| Measure | Value |
| --- | --- |
| Exact fault set, loop | 11 / 20 |
| Fault precision, loop | 0.91 |
| Fault recall, loop | 0.79 |
| Cascade fix order root first | 2 / 3 |
| Exact fault set, independent lane | 14 / 20 |
| Fault precision, independent lane | 0.88 |
| Fault recall, independent lane | 0.95 |
| User answers, total | 36 |
| Answers from the evidence, total | 49 |
| Errors | 0 |
| Requests for each case | 7.5 |
| Input tokens for each case | 56695 |
| Jev cost for each case | $0.002381 |
| Opus 5 cost for each case, same tokens | $0.2835 |
| Jev cost for 1,000 cases | $2.3812 |
| Opus 5 cost for 1,000 cases | $283.4745 |
| Compute time for each case | 4.46 s |
| Wait time for each case | 2.88 s |

| Kind | Requests | Mean input tokens | Min s | Median s | p95 s | Max s |
| --- | --- | --- | --- | --- | --- | --- |
| A | 39 | 5344 | 0.28 | 0.33 | 0.66 | 1.33 |
| B | 36 | 1877 | 0.26 | 0.31 | 0.45 | 1.67 |
| C | 56 | 8848 | 0.29 | 0.39 | 1.05 | 1.49 |
| E | 20 | 18122 | 1.16 | 1.26 | 1.62 | 1.80 |

| Case | Tags | Expected | Found (loop) | Independent | Loops | User / evidence answers | Confirm / reask | Tokens | Wait s | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yaris_fan_relay | look_alike | fan_relay | fan_relay, radiator_fan_motor WRONG | fan_relay ok | 2 | 1 / 4 | 0 / 0 | 46510 | 2.51 |  |
| octavia_wheel_bearing | look_alike | wheel_bearing_worn | wheel_bearing_worn ok | wheel_bearing_worn, abs_wheel_sensor WRONG | 1 | 0 / 1 | 0 / 0 | 31916 | 2.17 |  |
| corsa_not_right | vague_report | thermostat_stuck_open | thermostat_stuck_open ok | thermostat_stuck_open ok | 1 | 0 / 1 | 0 / 0 | 31602 | 2.27 |  |
| zafira_engine_light | look_alike | o2_sensor_fault | o2_sensor_fault ok | o2_sensor_fault ok | 1 | 0 / 1 | 0 / 0 | 31909 | 1.55 |  |
| berlingo_hill_revs | unclear_answer | clutch_slip | clutch_slip, fuel_filter_clogged WRONG | clutch_slip ok | 2 | 5 / 1 | 0 / 0 | 89165 | 4.36 | no answer for q_fp_symptom, q_fp_pressure_idle, q_fp_pressure_load, q_fp_filter_age, q_fp_filter_swap |
| micra_key_light |  | immobiliser_fault | immobiliser_fault ok | immobiliser_fault ok | 1 | 0 / 1 | 0 / 0 | 31674 | 1.58 |  |
| golf_alternator_battery | cascade | alternator_failure, flat_battery | alternator_failure, flat_battery ok | alternator_failure, flat_battery ok | 3 | 6 / 2 | 0 / 0 | 109558 | 5.99 | unexplained: starter_intermittent |
| focus_motorway_overheat | cascade, look_alike | thermostat_stuck_closed, head_gasket | - WRONG | head_gasket WRONG | 1 | 2 / 0 | 0 / 2 | 55608 | 2.41 | stuck at q_wp_symptom unexplained: overheat_gauge, overheat_on_road, coolant_temp_high, coolant_loss, sweet_smell, white_smoke |
| c3_pull_and_click | independent_faults | sticking_caliper, cv_joint_worn | sticking_caliper, cv_joint_worn ok | sticking_caliper, cv_joint_worn ok | 2 | 0 / 2 | 0 / 0 | 37535 | 1.99 |  |
| passat_overtake_stutter | cascade, unclear_answer | fuel_filter_clogged, fuel_pump_weak | fuel_pump_weak WRONG | fuel_pump_weak, fuel_filter_clogged ok | 1 | 2 / 2 | 1 / 0 | 52398 | 2.29 | unexplained: fuel_filter_overdue |
| scenic_traffic_steam | cascade | radiator_fan_motor, head_gasket | radiator_fan_motor WRONG | radiator_fan_motor, head_gasket ok | 2 | 2 / 3 | 0 / 2 | 59687 | 2.56 | stuck at q_wp_symptom unexplained: coolant_loss, white_smoke |
| transit_monday_mornings | cascade, vague_report | parasitic_drain, flat_battery | parasitic_drain WRONG | parasitic_drain, flat_battery ok | 2 | 2 / 3 | 0 / 2 | 59949 | 2.89 | stuck at q_sta_symptom unexplained: starter_intermittent |
| polo_grind_and_blow | independent_faults | worn_pads, exhaust_leak | exhaust_leak, worn_pads ok | worn_pads, exhaust_leak, o2_sensor_fault WRONG | 2 | 0 / 2 | 0 / 0 | 37873 | 1.91 |  |
| megane_puddle_abs | independent_faults, look_alike | coolant_hose_leak, abs_wheel_sensor | abs_wheel_sensor, coolant_hose_leak ok | coolant_hose_leak, abs_wheel_sensor ok | 2 | 1 / 5 | 0 / 0 | 46837 | 2.18 |  |
| fabia_rain_lights_rattle | independent_faults | can_wiring_fault, dual_mass_flywheel | can_wiring_fault, dual_mass_flywheel, abs_wheel_sensor WRONG | dual_mass_flywheel, can_wiring_fault ok | 3 | 7 / 1 | 0 / 0 | 114980 | 4.78 | unexplained: starter_intermittent no answer for q_abs_codes, q_abs_live, q_abs_play, q_abs_sensor |
| a4_shake_and_eggs | cascade | spark_plugs_worn, ignition_coil, catalytic_converter_blocked | spark_plugs_worn, catalytic_converter_blocked, ignition_coil ok | ignition_coil, spark_plugs_worn WRONG | 3 | 2 / 4 | 0 / 0 | 66742 | 3.33 |  |
| vito_flat_and_squeal | cascade, independent_faults | alternator_diode_leak, flat_battery, aux_belt_slip | alternator_diode_leak WRONG | aux_belt_slip, parasitic_drain, flat_battery, alternator_diode_leak, alternator_failure WRONG | 1 | 0 / 4 | 0 / 0 | 32359 | 2.51 | unexplained: low_charge_voltage, belt_squeal |
| qashqai_steam_and_squeal | cascade, independent_faults | thermostat_stuck_closed, head_gasket, worn_pads | thermostat_stuck_closed, worn_pads WRONG | head_gasket, worn_pads, thermostat_stuck_closed ok | 3 | 2 / 3 | 0 / 2 | 66521 | 4.22 | stuck at q_wp_symptom unexplained: overheat_in_traffic, coolant_loss |
| discovery_pedals_and_light | independent_faults | abs_pump_module, clutch_hydraulic, o2_sensor_fault | abs_pump_module, clutch_hydraulic, o2_sensor_fault ok | o2_sensor_fault, abs_pump_module, air_in_brakes, clutch_hydraulic WRONG | 3 | 1 / 6 | 0 / 0 | 53510 | 2.84 | unexplained: many_warning_lights |
| kangoo_not_itself | cascade, vague_report | alternator_failure, flat_battery, starter_motor_worn | starter_motor_worn, alternator_failure, flat_battery ok | starter_motor_worn, alternator_failure, flat_battery ok | 3 | 3 / 3 | 0 / 0 | 77565 | 3.35 | fix order wrong |
