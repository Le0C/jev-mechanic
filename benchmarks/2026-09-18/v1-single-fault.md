# Harness report

Run at 2026-09-18T12:40:57 on `jev-1.13.0`, 55 s. Prices: Jev $0.042 and Opus 5 $5.00 for each million input tokens.

The Opus 5 column prices the Jev input tokens at the Opus 5 input price. It is a lower limit. It has no output tokens and no tokenizer difference.

## fan-out on

| Measure | Value |
| --- | --- |
| Correct, flowchart lane | 13 / 15 |
| Correct, independent lane | 15 / 15 |
| Lanes agree | 13 / 15 |
| Cases with a 0.9 flag before the leaf | 0 / 15 |
| Cases where the flowchart score passed 0.9 | 13 / 15 |
| User answers, total | 29 |
| Answers from the report, total | 14 |
| Errors | 0 |
| Requests for each session | 5.9 |
| Input tokens for each session | 18828 |
| Jev cost for each session | $0.000791 |
| Opus 5 cost for each session, same tokens | $0.0941 |
| Jev cost for 1,000 sessions | $0.7908 |
| Opus 5 cost for 1,000 sessions | $94.1410 |
| Compute time for each session | 3.12 s |
| Wait time for each session | 1.76 s |

| Kind | Requests | Mean input tokens | Min s | Median s | p95 s | Max s |
| --- | --- | --- | --- | --- | --- | --- |
| A | 15 | 10400 | 0.96 | 1.03 | 1.10 | 1.21 |
| B | 29 | 1158 | 0.26 | 0.34 | 0.50 | 1.29 |
| C | 44 | 2110 | 0.28 | 0.34 | 0.79 | 0.87 |

| Case | Expected | Flowchart (score) | 0.9 step | Independent | Ind. flag step | User / report answers | Confirm / reask | Tokens | Wait s | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| golf_slow_crank | flat_battery | flat_battery (0.94) ok | 3 | flat_battery (0.33) | - | 3 / 0 | 0 / 0 | 23515 | 2.20 |  |
| clio_single_click | starter_motor | starter_motor (0.92) ok | 2 | starter_motor (0.99) | 1 | 2 / 1 | 0 / 0 | 18721 | 1.74 |  |
| fiesta_cranks_no_fire | fuel_pump | fuel_pump (0.94) ok | 2 | fuel_pump (1.00) | 2 | 2 / 1 | 0 / 0 | 18652 | 2.71 |  |
| corolla_dead_silent | battery_terminals | battery_terminals (0.95) ok | 2 | battery_terminals (1.00) | 2 | 2 / 1 | 0 / 0 | 19946 | 1.74 |  |
| passat_funny_mornings | battery_end_of_life | battery_end_of_life (0.96) ok | 3 | battery_end_of_life (1.00) | 3 | 3 / 0 | 0 / 0 | 23496 | 2.11 |  |
| transit_battery_light | alternator_failure | alternator_failure (0.96) ok | 3 | alternator_failure (1.00) | 0 | 3 / 1 | 0 / 0 | 21917 | 2.00 |  |
| mini_flat_mondays | parasitic_drain | parasitic_drain (0.91) ok | 1 | parasitic_drain (1.00) | 1 | 1 / 1 | 0 / 0 | 15632 | 1.28 |  |
| octavia_shudder_uphill | ignition_coil | ignition_coil (0.98) ok | 2 | ignition_coil (1.00) | 1 | 2 / 1 | 0 / 0 | 19243 | 1.65 |  |
| yaris_hunting_idle | vacuum_leak | specialist WRONG | - | vacuum_leak (0.60) | - | 3 / 1 | 0 / 0 | 21794 | 2.03 |  |
| berlingo_sluggish | fuel_filter | fuel_filter (0.93) ok | 2 | fuel_filter (0.83) | - | 2 / 1 | 0 / 0 | 18455 | 1.69 |  |
| c3_hot_in_traffic | radiator_fan | radiator_fan (0.98) ok | 1 | radiator_fan (1.00) | 0 | 1 / 1 | 0 / 0 | 15657 | 1.44 |  |
| megane_motorway_hot | thermostat_stuck | None WRONG | - | thermostat_stuck (0.71) | - | 2 / 1 | 0 / 2 | 18908 | 1.78 | stuck at q_co_top_hose |
| astra_sweet_smell | head_gasket | head_gasket (0.91) ok | 2 | head_gasket (1.00) | 2 | 2 / 1 | 0 / 0 | 18429 | 1.84 |  |
| bmw_brake_shudder | warped_discs | warped_discs (0.96) ok | 1 | warped_discs (1.00) | 0 | 1 / 1 | 0 / 0 | 15653 | 1.28 |  |
| zafira_pulls_left | sticking_caliper | sticking_caliper (0.95) ok | 0 | sticking_caliper (0.99) | 0 | 0 / 2 | 0 / 0 | 12405 | 1.01 |  |

## fan-out off

| Measure | Value |
| --- | --- |
| Correct, flowchart lane | 13 / 15 |
| Correct, independent lane | 15 / 15 |
| Lanes agree | 13 / 15 |
| Cases with a 0.9 flag before the leaf | 0 / 15 |
| Cases where the flowchart score passed 0.9 | 13 / 15 |
| User answers, total | 30 |
| Answers from the report, total | 14 |
| Errors | 0 |
| Requests for each session | 6.0 |
| Input tokens for each session | 18066 |
| Jev cost for each session | $0.000759 |
| Opus 5 cost for each session, same tokens | $0.0903 |
| Jev cost for 1,000 sessions | $0.7588 |
| Opus 5 cost for 1,000 sessions | $90.3283 |
| Compute time for each session | 3.28 s |
| Wait time for each session | 1.88 s |

| Kind | Requests | Mean input tokens | Min s | Median s | p95 s | Max s |
| --- | --- | --- | --- | --- | --- | --- |
| A | 15 | 10400 | 0.97 | 1.02 | 1.12 | 1.13 |
| B | 30 | 655 | 0.27 | 0.31 | 0.42 | 0.89 |
| C | 45 | 2118 | 0.27 | 0.38 | 0.86 | 1.40 |

| Case | Expected | Flowchart (score) | 0.9 step | Independent | Ind. flag step | User / report answers | Confirm / reask | Tokens | Wait s | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| golf_slow_crank | flat_battery | flat_battery (0.94) ok | 3 | flat_battery (0.38) | - | 3 / 0 | 0 / 0 | 21097 | 2.15 |  |
| clio_single_click | starter_motor | starter_motor (0.92) ok | 2 | starter_motor (0.99) | 1 | 2 / 1 | 0 / 0 | 17971 | 1.77 |  |
| fiesta_cranks_no_fire | fuel_pump | fuel_pump (0.94) ok | 2 | fuel_pump (1.00) | 2 | 2 / 1 | 0 / 0 | 17947 | 2.22 |  |
| corolla_dead_silent | battery_terminals | battery_terminals (0.94) ok | 2 | battery_terminals (1.00) | 2 | 2 / 1 | 0 / 0 | 17966 | 1.66 |  |
| passat_funny_mornings | battery_end_of_life | battery_end_of_life (0.96) ok | 3 | battery_end_of_life (1.00) | 3 | 3 / 0 | 0 / 0 | 21078 | 2.40 |  |
| transit_battery_light | alternator_failure | alternator_failure (0.96) ok | 3 | alternator_failure (1.00) | 0 | 3 / 1 | 0 / 0 | 20958 | 2.03 |  |
| mini_flat_mondays | parasitic_drain | parasitic_drain (0.91) ok | 1 | parasitic_drain (1.00) | 1 | 1 / 1 | 0 / 0 | 15156 | 1.37 |  |
| octavia_shudder_uphill | ignition_coil | ignition_coil (0.98) ok | 2 | ignition_coil (1.00) | 1 | 2 / 1 | 0 / 0 | 18041 | 1.89 |  |
| yaris_hunting_idle | vacuum_leak | specialist WRONG | - | vacuum_leak (0.83) | - | 4 / 1 | 1 / 1 | 24172 | 2.84 |  |
| berlingo_sluggish | fuel_filter | fuel_filter (0.93) ok | 2 | fuel_filter (0.83) | - | 2 / 1 | 0 / 0 | 17954 | 2.12 |  |
| c3_hot_in_traffic | radiator_fan | radiator_fan (0.98) ok | 1 | radiator_fan (1.00) | 0 | 1 / 1 | 0 / 0 | 15176 | 1.91 |  |
| megane_motorway_hot | thermostat_stuck | None WRONG | - | thermostat_stuck (0.71) | - | 2 / 1 | 0 / 2 | 17946 | 1.70 | stuck at q_co_top_hose |
| astra_sweet_smell | head_gasket | head_gasket (0.90) ok | 2 | head_gasket (1.00) | 2 | 2 / 1 | 0 / 0 | 17950 | 1.66 |  |
| bmw_brake_shudder | warped_discs | warped_discs (0.96) ok | 1 | warped_discs (1.00) | 0 | 1 / 1 | 0 / 0 | 15168 | 1.34 |  |
| zafira_pulls_left | sticking_caliper | sticking_caliper (0.95) ok | 0 | sticking_caliper (0.99) | 0 | 0 / 2 | 0 / 0 | 12405 | 1.12 |  |
