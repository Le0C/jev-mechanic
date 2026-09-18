"""The 20 version 2 cases, before the answer banks are merged in."""


def code(c, desc, status, km):
    return {"code": c, "description": desc, "status": status, "mileage_km": km}


def svc(date, km, work):
    return {"date": date, "mileage_km": km, "work": work}


CASES = [
    # ---------------------------------------------------------------- 1 fault
    dict(
        id="yaris_fan_relay",
        title="Hot in town traffic",
        date="2026-08-12",
        faults=["fan_relay"],
        tags=["look_alike"],
        report=(
            "My Yaris keeps getting hot when I'm stuck in town traffic, the needle creeps right up. "
            "Once I'm moving again it drops back to normal. I can't hear the fan doing anything, but "
            "I don't really know what it should sound like. My daughter borrowed it last week and said "
            "the same, she also left sweet wrappers everywhere."
        ),
        vehicle={"make": "Toyota", "model": "Yaris", "year": 2012, "mileage_km": 142300},
        obd=[
            code("P0217", "Engine coolant over temperature condition", "active", 142250),
            code("P0480", "Cooling fan 1 control circuit", "pending", 142280),
            code("P0442", "Evaporative emission system small leak", "cleared", 131900),
        ],
        freeze={"coolant_temp_c": 112, "engine_rpm": 780, "vehicle_speed_kmh": 0, "intake_air_temp_c": 41,
                "battery_voltage_v": 14.1, "ambient_temp_c": 29},
        service=[
            svc("2021-03-10", 116800, "Annual service, oil and filter"),
            svc("2022-04-02", 124500, "Front wiper blades and cabin filter"),
            svc("2023-05-19", 131900, "Service, evap purge valve replaced, code cleared"),
            svc("2024-06-11", 136700, "Oil and filter change"),
            svc("2025-07-03", 140100, "MOT pass, advisory: rear tyres near the limit"),
        ],
        notes=[
            "Coolant level at max, no leak on the pressure test.",
            "Fan did not start at 105 °C on the scan tool. Fan blades turn freely by hand.",
            "Fan runs at once when 12 V goes straight to the motor.",
            "Aftermarket seat covers fitted.",
        ],
        answers={
            "cooling_fan": {
                "q_fan_when": "in traffic, fine once it's moving",
                "q_fan_runs": "nope, fan sits still at 106 °C",
                "q_fan_fuse": "no, fan fuse is good",
                "q_fan_direct": "yes, spins up straight away on 12 V direct",
                "q_fan_relay_click": "no, no click and 0 V at the relay output when I command it",
                "q_fan_motor_current": "no, turns freely, 11 A on the direct test",
            },
            "thermostat": {
                "q_th_symptom": "overheats in traffic",
                "q_th_top_hose": "no, top hose is hot",
                "q_th_fan": "no, fan never kicks in",
            },
            "water_pump": {
                "q_wp_symptom": "overheats in traffic, level stays on max",
                "q_wp_flow": "no, top and bottom hoses both hot",
            },
        },
    ),
    dict(
        id="octavia_wheel_bearing",
        title="Drone at speed and an ABS light",
        date="2026-07-21",
        faults=["wheel_bearing_worn"],
        tags=["look_alike"],
        report=(
            "There's a droning noise from the front of my Octavia that gets louder the faster I go, "
            "a bit like driving on a rough road. Yesterday the ABS light and the traction control light "
            "came on as well. I do a lot of motorway miles for work. The number plate light stopped working "
            "too, not sure if that's related."
        ),
        vehicle={"make": "Skoda", "model": "Octavia", "year": 2016, "mileage_km": 168900},
        obd=[
            code("C0040", "Right front wheel speed sensor circuit", "active", 168850),
            code("P2002", "Diesel particulate filter efficiency below threshold", "history", 165000),
            code("P0299", "Turbocharger underboost", "cleared", 160200),
        ],
        freeze={"vehicle_speed_kmh": 112, "wheel_speed_fr_kmh": 0, "wheel_speed_fl_kmh": 112,
                "engine_rpm": 2400, "coolant_temp_c": 90, "battery_voltage_v": 14.2},
        service=[
            svc("2022-02-14", 120300, "Timing belt and water pump"),
            svc("2023-03-01", 135000, "Service, oil and filters"),
            svc("2024-02-20", 149800, "Front discs and pads"),
            svc("2025-02-11", 162400, "Service, DPF cleaned"),
            svc("2026-01-15", 166700, "Winter tyres fitted"),
        ],
        notes=[
            "Front right hub has play at 12 and 6 o'clock, and it is rough when spun by hand.",
            "Hum from 60 km/h, louder when the car sways to the left.",
            "Front right wheel speed sensor 1.1 kΩ, in spec, wiring intact.",
            "Rear number plate bulb blown.",
        ],
        answers={
            "wheel_bearings": {
                "q_whl_noise": "hum, a drone from the front right from about 60 km/h",
                "q_whl_load": "yes, louder when it sways left",
                "q_whl_spin": "yes, front right is rough and grumbles",
                "q_whl_play": "yes, a couple of mm of rock at 12 and 6 on the FR",
                "q_whl_sensor": "no, FR sensor 1.1 kΩ, in spec",
            },
            "abs": {
                "q_abs_codes": "C0040, front right wheel speed",
                "q_abs_live": "yes, FR drops to 0 above 90 km/h then comes back",
                "q_abs_play": "yes, FR hub has play and feels rough",
                "q_abs_sensor": "no, sensor and wiring are fine",
            },
            "brakes": {"q_brk_pads": "9 mm front, 7 mm rear"},
        },
    ),
    dict(
        id="corsa_not_right",
        title="Just not right lately (vague)",
        date="2026-02-03",
        faults=["thermostat_stuck_open"],
        tags=["vague_report"],
        report=(
            "The Corsa just doesn't feel right at the moment. It seems to go through petrol quicker "
            "and it all feels a bit sluggish in the mornings. My husband thinks I'm imagining it. "
            "We had a new radio fitted in the autumn."
        ),
        vehicle={"make": "Vauxhall", "model": "Corsa", "year": 2015, "mileage_km": 97600},
        obd=[
            code("P0128", "Coolant temperature below thermostat regulating temperature", "active", 97550),
            code("P0501", "Vehicle speed sensor range or performance", "cleared", 88000),
        ],
        freeze={"coolant_temp_c": 64, "engine_rpm": 2100, "vehicle_speed_kmh": 80, "ambient_temp_c": 3,
                "long_term_fuel_trim_pct": 2.3, "engine_load_pct": 38},
        service=[
            svc("2020-11-20", 60100, "Annual service"),
            svc("2022-01-10", 72400, "Clutch replaced"),
            svc("2023-01-30", 81000, "Service and spark plugs"),
            svc("2024-02-12", 88000, "Speed sensor replaced, code cleared"),
            svc("2025-02-04", 94300, "Oil and filter, cabin filter"),
        ],
        notes=[
            "Gauge stayed below the middle after 20 minutes on the road test.",
            "Top hose warm within 2 minutes of a cold start.",
            "Heater only lukewarm on full hot.",
            "Customer asked for a quote on new floor mats.",
        ],
        answers={
            "thermostat": {
                "q_th_symptom": "stays cold, P0128 stored",
                "q_th_warm_time": "yes, only 62 °C after 20 min driving",
                "q_th_radiator_warm": "yes, top hose warm about 2 min after a cold start",
                "q_th_sensor": "yes, 63 °C on the IR gun, sensor says 62",
            },
            "water_pump": {"q_wp_flow": "no, hoses similar, just never properly hot"},
        },
    ),
    dict(
        id="zafira_engine_light",
        title="Engine light, drives the same",
        date="2026-05-08",
        faults=["o2_sensor_fault"],
        tags=["look_alike"],
        report=(
            "The engine light has come on in the Zafira and stayed on. It drives the same as always as far "
            "as I can tell, maybe it's using a bit more fuel on the school run. The exhaust sounds normal to me. "
            "We're going camping next month so I want it sorted."
        ),
        vehicle={"make": "Vauxhall", "model": "Zafira", "year": 2013, "mileage_km": 151200},
        obd=[
            code("P0133", "O2 sensor circuit slow response, bank 1 sensor 1", "active", 151150),
            code("P0420", "Catalyst system efficiency below threshold, bank 1", "pending", 151180),
            code("P0401", "Exhaust gas recirculation flow insufficient", "cleared", 139700),
        ],
        freeze={"engine_rpm": 2200, "vehicle_speed_kmh": 64, "short_term_fuel_trim_pct": 6.3,
                "long_term_fuel_trim_pct": 8.6, "o2_sensor_b1s1_v": 0.45, "coolant_temp_c": 89},
        service=[
            svc("2021-05-02", 110000, "Annual service"),
            svc("2022-06-15", 121400, "Timing chain"),
            svc("2024-01-22", 139700, "EGR valve cleaned, code cleared"),
            svc("2025-04-30", 146800, "Annual service"),
            svc("2026-01-09", 149900, "Rear brake pads"),
        ],
        notes=[
            "Smoke test: no exhaust leak from the manifold to the rear box.",
            "Upstream O2 sensor switches about once every 3 s at 2500 rpm, too slow.",
            "Nearside rear tyre at 1.9 bar, inflated to 2.4 bar.",
        ],
        answers={
            "exhaust": {
                "q_exh_symptom": "just the codes, P0133 and P0420, sounds fine",
                "q_exh_smoke_test": "no, smoke test is tight",
                "q_exh_o2_code": "yes, P0133 bank 1 sensor 1",
                "q_exh_o2_switch": "yes, lazy, about one switch every 3 s",
                "q_exh_leak_before": "no, no leak before the sensor",
            },
        },
    ),
    dict(
        id="berlingo_hill_revs",
        title="Revs rise on the hill",
        date="2026-03-17",
        faults=["clutch_slip"],
        tags=["unclear_answer"],
        report=(
            "Going up the hill out of the builders' yard with a full load, the revs shoot up but the van "
            "doesn't really go anywhere. There was a bit of a hot smell afterwards as well. It's worse in "
            "4th and 5th. The radio aerial snapped off in the car wash last week, ignore that."
        ),
        vehicle={"make": "Citroen", "model": "Berlingo", "year": 2011, "mileage_km": 214000},
        obd=[
            code("P0380", "Glow plug circuit A", "history", 209800),
            code("P0087", "Fuel rail pressure too low", "cleared", 205100),
        ],
        freeze={"engine_rpm": 3400, "vehicle_speed_kmh": 42, "engine_load_pct": 71, "coolant_temp_c": 92},
        service=[
            svc("2020-10-01", 160000, "Cambelt kit"),
            svc("2022-03-11", 180400, "Annual service"),
            svc("2023-09-20", 195000, "Rear springs"),
            svc("2024-10-02", 205100, "Fuel filter, rail pressure code cleared"),
            svc("2025-09-15", 211300, "Service, clutch fluid checked"),
        ],
        notes=[
            "Stall test in 4th with the handbrake on: the engine keeps running at 2000 rpm.",
            "Burnt friction smell from the bell housing after the road test.",
            "Original clutch according to the history, 214,000 km.",
            "Load bay light lens cracked.",
        ],
        answers={
            "clutch": {
                "q_clu_symptom": "slips, the revs flare in 4th and 5th under load",
                "q_clu_stall_test": "yes, keeps running at 2000 in 4th with the handbrake on",
                "q_clu_adjust": "hard to say, the self-adjuster's buried and the pedal feels about right",
            },
            "brakes": {
                "q_brk_symptom": "smell after the hill, it doesn't pull",
                "q_brk_wheel_temp": "no, all four within a few degrees",
            },
        },
    ),
    dict(
        id="micra_key_light",
        title="Cranks, never catches",
        date="2026-01-26",
        faults=["immobiliser_fault"],
        tags=[],
        report=(
            "My Micra won't start this morning. It turns over like normal but it never catches. "
            "There's a little light flashing on the dash, it looks like a car with a key in it. "
            "I did drop my keys at the weekend, don't know if that matters. I've got to get to work somehow."
        ),
        vehicle={"make": "Nissan", "model": "Micra", "year": 2010, "mileage_km": 118400},
        obd=[
            code("P1610", "Immobiliser: key not recognised", "active", 118400),
            code("P0340", "Camshaft position sensor circuit", "cleared", 109600),
        ],
        freeze={"engine_rpm": 210, "battery_voltage_v": 12.3, "coolant_temp_c": 4, "ambient_temp_c": 2},
        service=[
            svc("2021-01-10", 88000, "Annual service"),
            svc("2022-02-01", 97500, "Front pads"),
            svc("2023-11-15", 109600, "Cam sensor replaced, code cleared"),
            svc("2024-12-02", 114200, "Service, new battery"),
            svc("2025-10-20", 117500, "MOT pass"),
        ],
        notes=[
            "Security light flashes fast while the engine cranks.",
            "Both keys tried. Neither key is recognised in the live data.",
            "Fuel pump primes. Rpm reads 210 while cranking.",
            "Coolant due for change at the next service.",
        ],
        answers={
            "ecu": {
                "q_ecu_symptom": "key light flashes and it cranks but won't fire",
                "q_ecu_immo_code": "yes, ECU says the key isn't recognised",
                "q_ecu_antenna": "yes, antenna ring doesn't read either key, 0 transponder reads",
            },
            "fuel_pump": {
                "q_fp_symptom": "cranks at normal speed but won't fire",
                "q_fp_pressure_crank": "at spec, 3.3 bar while cranking",
            },
            "ignition": {
                "q_ign_symptom": "cranks but won't fire",
                "q_ign_rpm": "no, 210 rpm on the scan tool while cranking",
            },
            "can_bus": {"q_can_symptom": "won't start, but the scan tool talks to every module"},
        },
    ),
    # ---------------------------------------------------------------- 2 faults
    dict(
        id="golf_alternator_battery",
        title="Slow start and a battery light",
        date="2026-09-01",
        faults=["alternator_failure", "flat_battery"],
        tags=["cascade"],
        report=(
            "My Golf was really slow to start this morning, it took three goes. On the way in the red "
            "battery light came on, and the headlights looked dim at the traffic lights. Last week I had "
            "the tracking done because it was pulling a bit. Could it just be the weather?"
        ),
        vehicle={"make": "VW", "model": "Golf", "year": 2014, "mileage_km": 128400},
        obd=[
            code("P0562", "System voltage low", "active", 128350),
            code("P2181", "Cooling system performance", "history", 125000),
            code("P0299", "Turbocharger underboost", "cleared", 116000),
        ],
        freeze={"battery_voltage_v": 12.1, "engine_rpm": 2050, "coolant_temp_c": 88, "vehicle_speed_kmh": 55,
                "alternator_load_pct": 98},
        service=[
            svc("2022-10-11", 101500, "Annual service"),
            svc("2023-11-20", 112300, "DSG oil change"),
            svc("2024-06-18", 116000, "Turbo actuator, code cleared"),
            svc("2025-11-02", 124800, "Oil and filter change"),
            svc("2026-08-26", 128300, "Four-wheel alignment"),
        ],
        notes=[
            "Battery light flickered on the road test.",
            "Charge voltage 12.4 V at 2000 rpm with the headlights on.",
            "Battery 3 years old, passed the load test after a full charge.",
            "Driver seat belt slow to retract.",
        ],
        answers={
            "alternator": {
                "q_alt_symptom": "battery light comes on while driving, lights go dim",
                "q_alt_run_voltage": "12.4 V at 2000 rpm, headlights on",
                "q_alt_belt": "no, belt's tight and not glazed",
                "q_alt_field": "yes, 12 V on the D+ with the ignition on",
                "q_alt_output": "yes, only 35 A out of 110 A",
                "q_alt_ripple": "no, 0.3 V AC",
                "q_alt_diode_drain": "no, 30 mA",
            },
            "battery": {
                "q_bat_start": "cranks slow, took three goes",
                "q_bat_voltage": "11.9 V at rest",
                "q_bat_charge_test": "yes, charged overnight and passes the load test",
                "q_bat_history": "no, it went flat while driving, not parked",
                "q_bat_age": "no, 3 years old",
            },
            "starter": {
                "q_sta_symptom": "turns over slow",
                "q_sta_lights": "no, headlights dim right down",
                "q_sta_battery_volt": "no, 11.9 V",
            },
        },
    ),
    dict(
        id="focus_motorway_overheat",
        title="Overheat on the motorway, then smoke",
        date="2026-06-30",
        faults=["thermostat_stuck_closed", "head_gasket"],
        tags=["cascade", "look_alike"],
        report=(
            "My Focus overheated on the motorway on the way back from Leeds, the gauge went all the way up "
            "and I pulled over. Since then there's a lot of white smoke out the back when I start it, and "
            "I'm topping up the water every couple of days. There's a sweet smell too. I had to get a lift "
            "home with my brother."
        ),
        vehicle={"make": "Ford", "model": "Focus", "year": 2012, "mileage_km": 176500},
        obd=[
            code("P0217", "Engine coolant over temperature condition", "active", 176450),
            code("P0171", "System too lean, bank 1", "cleared", 167900),
        ],
        freeze={"coolant_temp_c": 121, "vehicle_speed_kmh": 112, "engine_rpm": 2900, "engine_load_pct": 46,
                "ambient_temp_c": 24},
        service=[
            svc("2022-05-02", 140200, "Annual service"),
            svc("2023-06-10", 152300, "Clutch and flywheel"),
            svc("2024-05-28", 162000, "Water pump and timing belt"),
            svc("2025-06-19", 170100, "Service, coolant topped up"),
            svc("2026-03-03", 174000, "Front tyres"),
        ],
        notes=[
            "With the gauge high, the top hose is only warm and the bottom hose is cold.",
            "Thermostat housing 112 °C on the engine side, 70 °C on the radiator side.",
            "Combustion leak tester turns yellow.",
            "Leak-down: bubbles in the expansion tank from cylinder 3.",
            "Pressure test: no external leak.",
            "Washer jet nozzle blocked.",
        ],
        answers={
            "cooling_fan": {
                "q_fan_when": "on the motorway at a steady 70, not in traffic",
                "q_fan_top_hose": "yes, top hose only warm with the gauge in the red",
                "q_fan_runs": "yes, fan runs",
            },
            "thermostat": {
                "q_th_symptom": "overheats, gauge in the red",
                "q_th_top_hose": "yes, top hose only warm with the gauge in the red",
                "q_th_temp_diff": "yes, 112 °C engine side, 70 °C radiator side",
                "q_th_bench": "yes, stays shut at 90 °C in the pot",
            },
            "water_pump": {
                "q_wp_symptom": "losing coolant, white smoke at start",
                "q_wp_visible": "no, holds pressure, no external leak",
                "q_wp_combustion": "yes, turns yellow",
                "q_wp_leakdown": "yes, bubbles in the tank on cylinder 3",
                "q_wp_flow": "no, both hoses similar once the thermostat's out",
                "q_wp_impeller": "no, impeller's fine, the pump is 2 years old",
            },
        },
    ),
    dict(
        id="c3_pull_and_click",
        title="Pulls when braking, clicks on lock",
        date="2026-04-14",
        faults=["sticking_caliper", "cv_joint_worn"],
        tags=["independent_faults"],
        report=(
            "When I brake, the car pulls to the left, and after driving into town there's a hot burning smell "
            "from the front. There's also a clicking noise when I do a full lock turn in the supermarket car park. "
            "I've just put new wipers on it, if you need to know that."
        ),
        vehicle={"make": "Citroen", "model": "C3", "year": 2017, "mileage_km": 88200},
        obd=[
            code("P0441", "Evaporative emission system incorrect purge flow", "history", 80000),
            code("P0138", "O2 sensor circuit high voltage, bank 1 sensor 2", "cleared", 79800),
        ],
        freeze={"vehicle_speed_kmh": 48, "engine_rpm": 1800, "coolant_temp_c": 88},
        service=[
            svc("2021-04-01", 30000, "First service"),
            svc("2022-04-20", 45100, "Annual service"),
            svc("2023-05-11", 60700, "Service, brake fluid"),
            svc("2024-06-02", 79800, "Rear O2 sensor replaced, code cleared"),
            svc("2025-05-20", 85300, "Front pads"),
        ],
        notes=[
            "Front left wheel 145 °C after a 5 km drive, the others 55 °C.",
            "Front left drags when turned by hand.",
            "Outer boot on the front right drive shaft split, grease on the arch.",
            "Parcel shelf string missing.",
        ],
        answers={
            "brakes": {
                "q_brk_symptom": "pulls left when braking, hot smell",
                "q_brk_wheel_temp": "yes, front left 145 °C, the others about 55",
                "q_brk_wheel_spin": "yes, front left drags",
                "q_brk_runout": "0.03 mm",
                "q_brk_pads": "6 mm front, 5 mm rear",
            },
            "wheel_bearings": {
                "q_whl_noise": "clicks on full lock",
                "q_whl_cv_test": "yes, clicks in a tight circle under power",
                "q_whl_boot": "yes, front right outer boot split, grease all over the arch",
                "q_whl_cv_play": "yes, a bit of rotational play at the outer joint",
            },
        },
    ),
    dict(
        id="passat_overtake_stutter",
        title="Stutters when overtaking",
        date="2026-03-02",
        faults=["fuel_filter_clogged", "fuel_pump_weak"],
        tags=["cascade", "unclear_answer"],
        report=(
            "The Passat loses power when I overtake, it kind of stutters and then catches up. Going up the "
            "long hill on the A30 it struggles in 4th. I've got a trip to Cornwall in two weeks with the caravan. "
            "The fuel's from the same supermarket as always."
        ),
        vehicle={"make": "VW", "model": "Passat", "year": 2011, "mileage_km": 201300},
        obd=[
            code("P0087", "Fuel rail pressure too low", "active", 201250),
            code("P0171", "System too lean, bank 1", "pending", 201280),
            code("P0507", "Idle air control system rpm higher than expected", "cleared", 190400),
        ],
        freeze={"fuel_rail_pressure_bar": 2.2, "fuel_rail_pressure_spec_bar": 3.5, "engine_load_pct": 88,
                "engine_rpm": 3800, "long_term_fuel_trim_pct": 14.1, "vehicle_speed_kmh": 96},
        service=[
            svc("2021-02-15", 150200, "Service, fuel filter"),
            svc("2022-03-08", 165000, "Annual service"),
            svc("2023-04-19", 180400, "Annual service"),
            svc("2024-05-21", 190400, "Throttle body cleaned, code cleared"),
            svc("2025-06-10", 197800, "Service, fuel filter change advised, customer declined"),
        ],
        notes=[
            "Rail pressure 2.9 bar at idle, spec 3.5 bar.",
            "Rail pressure falls to 2.2 bar at full load.",
            "Pump delivered 480 ml in 30 s, spec 650 ml.",
            "Offside mirror glass loose.",
        ],
        answers={
            "fuel_pump": {
                "q_fp_symptom": "runs but stutters and loses power under load",
                "q_fp_pressure_idle": "no, 2.9 bar at idle against 3.5",
                "q_fp_filter_age": "yes, last filter at 150,200 km, well overdue",
                "q_fp_filter_swap": (
                    "hard to say, the new filter helped, 3.1 bar at full load now against 3.5 spec, was 2.2"
                ),
                "q_fp_volume": "yes, only 480 ml in 30 s, spec 650",
                "q_fp_pressure_load": "drops to 2.2 bar at full load",
                "q_fp_pressure_crank": "low, 2.8 bar",
            },
            "injectors": {
                "q_inj_symptom": "lean code P0171 and a hesitation",
                "q_inj_pressure_load": "drops to 2.2 bar flat out",
                "q_inj_trim": "+14% long term",
            },
        },
    ),
    dict(
        id="scenic_traffic_steam",
        title="Temperature light in traffic, then steam",
        date="2026-07-09",
        faults=["radiator_fan_motor", "head_gasket"],
        tags=["cascade"],
        report=(
            "The temperature light keeps coming on in traffic, it was bad on the school run with the queues. "
            "The fan never seems to come on. Now the coolant bottle is nearly empty every few days and there's "
            "steam or smoke from the exhaust in the morning. The sunroof leaks too, but it's always done that."
        ),
        vehicle={"make": "Renault", "model": "Scenic", "year": 2009, "mileage_km": 189000},
        obd=[
            code("P0217", "Engine coolant over temperature condition", "active", 188950),
            code("P0300", "Random or multiple cylinder misfire detected", "cleared", 180800),
        ],
        freeze={"coolant_temp_c": 118, "vehicle_speed_kmh": 0, "engine_rpm": 820, "ambient_temp_c": 27},
        service=[
            svc("2021-06-01", 150500, "Annual service"),
            svc("2022-07-05", 162000, "Cambelt and water pump"),
            svc("2023-07-14", 172000, "Annual service"),
            svc("2024-07-30", 180800, "Coil pack, code cleared"),
            svc("2025-07-01", 186000, "Service, coolant topped up"),
        ],
        notes=[
            "Fan fuse (40 A) blown. Fan motor seized, it will not turn by hand.",
            "Combustion leak test positive.",
            "Bubbles in the expansion tank from cylinder 2 on the leak-down test.",
            "Sunroof drain blocked.",
        ],
        answers={
            "cooling_fan": {
                "q_fan_when": "in traffic, fine on the open road",
                "q_fan_runs": "no, fan doesn't move at 110 °C",
                "q_fan_fuse": "yes, 40 A fuse blown",
                "q_fan_motor_current": "yes, motor's seized, won't turn by hand",
                "q_fan_direct": "no, dead on 12 V direct",
            },
            "thermostat": {
                "q_th_symptom": "overheats in traffic",
                "q_th_top_hose": "no, top hose is scalding",
                "q_th_fan": "no, fan never runs",
            },
            "water_pump": {
                "q_wp_symptom": "losing coolant and white smoke in the mornings",
                "q_wp_visible": "no, no external leak on the pressure test",
                "q_wp_combustion": "yes, fluid goes yellow",
                "q_wp_leakdown": "yes, bubbles in the tank from cylinder 2",
            },
        },
    ),
    dict(
        id="transit_monday_mornings",
        title="Some mornings it won't go (vague)",
        date="2026-02-18",
        faults=["parasitic_drain", "flat_battery"],
        tags=["cascade", "vague_report"],
        report=(
            "The van's been a pain some mornings, especially after the weekend. Sometimes it's fine and "
            "sometimes it just won't go without a jump off my mate's van. I fitted a dash cam and a new stereo "
            "in January if that makes any difference. We need it for work so it's costing me."
        ),
        vehicle={"make": "Ford", "model": "Transit Custom", "year": 2018, "mileage_km": 143700},
        obd=[
            code("B1318", "Battery voltage low", "history", 143500),
            code("P0401", "Exhaust gas recirculation flow insufficient", "cleared", 132600),
        ],
        freeze={"battery_voltage_v": 11.7, "engine_rpm": 0, "ambient_temp_c": 2},
        service=[
            svc("2021-01-20", 88000, "Annual service"),
            svc("2022-02-10", 104000, "Annual service"),
            svc("2023-03-01", 119000, "Clutch"),
            svc("2024-03-15", 132600, "EGR cleaned, code cleared"),
            svc("2025-03-04", 138900, "Service, new battery"),
            svc("2026-01-12", 143100, "Dash cam hard-wired, aftermarket stereo fitted"),
        ],
        notes=[
            "Sleep current 185 mA after 40 minutes, spec 50 mA.",
            "Current stays at 180 mA with the alternator B+ lead off.",
            "Drain falls to 25 mA when the dash cam fuse is pulled.",
            "Battery 11 months old, passed the load test after a charge.",
            "Nearside sliding door runner stiff.",
        ],
        answers={
            "battery": {
                "q_bat_start": "starts after a jump but it's flat again after it sits over the weekend",
                "q_bat_drain": "185 mA once it's asleep",
                "q_bat_alt_unplug": "no, still 180 mA with the B+ off",
                "q_bat_voltage": "11.7 V at rest",
                "q_bat_charge_test": "yes, passes after a charge, battery's 11 months old",
                "q_bat_history": "yes, flat after the weekend with everything off",
            },
            "alternator": {
                "q_alt_symptom": "goes flat after it sits, no light while driving",
                "q_alt_run_voltage": "14.3 V at 2000",
                "q_alt_diode_drain": "yes, 185 mA",
                "q_alt_drain_unplug": "no, still 180 mA with the B+ lead off",
            },
            "starter": {
                "q_sta_symptom": "slow on a Monday morning, then it clicks",
                "q_sta_lights": "no, lights dim when it tries",
                "q_sta_battery_volt": "no, 11.7 V",
            },
        },
    ),
    dict(
        id="polo_grind_and_blow",
        title="Brake grind and a loud exhaust",
        date="2026-05-26",
        faults=["worn_pads", "exhaust_leak"],
        tags=["independent_faults"],
        report=(
            "The brakes on my Polo have started making a horrible grinding noise, and a red light came on the "
            "dash this morning. Separately, the exhaust has got really loud, especially first thing when it's "
            "cold, a sort of blowing sound. My neighbour says it sounds like a tractor. I only use it for work "
            "and the gym."
        ),
        vehicle={"make": "VW", "model": "Polo", "year": 2015, "mileage_km": 121300},
        obd=[
            code("P0131", "O2 sensor circuit low voltage, bank 1 sensor 1", "pending", 121260),
            code("P0420", "Catalyst system efficiency below threshold, bank 1", "pending", 121280),
            code("P0455", "Evaporative emission system large leak", "cleared", 113500),
        ],
        freeze={"engine_rpm": 900, "coolant_temp_c": 30, "o2_sensor_b1s1_v": 0.08,
                "short_term_fuel_trim_pct": 12.5},
        service=[
            svc("2021-05-10", 80200, "Annual service"),
            svc("2022-06-01", 92000, "Annual service"),
            svc("2023-06-12", 105000, "Annual service"),
            svc("2024-06-20", 113500, "Evap hose, code cleared"),
            svc("2025-05-30", 118900, "Service, brake fluid change"),
        ],
        notes=[
            "Front pads 1.5 mm, the wear indicator touches the disc.",
            "Brake fluid at the minimum mark, no leaks found.",
            "Smoke test: leak at the exhaust manifold gasket, before the first O2 sensor.",
            "Glovebox catch broken.",
        ],
        answers={
            "brakes": {
                "q_brk_symptom": "grinding when braking",
                "q_brk_pads": "1.5 mm on the fronts, indicator on the disc",
                "q_brk_fluid_leak": "no, level on min but no leaks",
            },
            "exhaust": {
                "q_exh_symptom": "loud blow at a cold start",
                "q_exh_smoke_test": "yes, blows at the manifold gasket",
                "q_exh_o2_code": "yes, P0131",
                "q_exh_o2_switch": "yes, reads lean and lazy",
                "q_exh_leak_before": "yes, the manifold gasket is before the sensor",
            },
        },
    ),
    dict(
        id="megane_puddle_abs",
        title="Green puddle and an ABS light",
        date="2026-09-08",
        faults=["coolant_hose_leak", "abs_wheel_sensor"],
        tags=["independent_faults", "look_alike"],
        report=(
            "I keep finding a green puddle under the front of my Megane on the drive, and I've topped up the "
            "coolant twice this month. There's a sweet smell when I get out. On top of that the ABS light came "
            "on last Tuesday, and the skid light with it. I just had the aircon regassed."
        ),
        vehicle={"make": "Renault", "model": "Megane", "year": 2016, "mileage_km": 132800},
        obd=[
            code("C0035", "Left front wheel speed sensor circuit", "active", 132780),
            code("P0340", "Camshaft position sensor circuit", "cleared", 124000),
        ],
        freeze={"vehicle_speed_kmh": 47, "wheel_speed_fl_kmh": 0, "wheel_speed_fr_kmh": 47,
                "coolant_temp_c": 91, "engine_rpm": 1900},
        service=[
            svc("2022-08-15", 96000, "Annual service"),
            svc("2023-09-01", 110500, "Timing belt and water pump"),
            svc("2024-09-10", 124000, "Cam sensor, code cleared"),
            svc("2025-09-02", 129600, "Annual service"),
            svc("2026-08-28", 132700, "Aircon regas"),
        ],
        notes=[
            "Pressure test: drip at the lower hose clamp. The hose is soft and cracked at the clamp.",
            "Water pump weep hole dry.",
            "Front left wheel speed sensor wire chafed on the strut, open circuit.",
            "Front left hub tight, no noise on the road test.",
            "Rear wiper arm loose.",
        ],
        answers={
            "water_pump": {
                "q_wp_symptom": "losing coolant, green puddle under the front",
                "q_wp_visible": "yes, drips under pressure",
                "q_wp_leak_place": "at the lower hose clamp",
                "q_wp_weep": "no, weep hole is dry",
                "q_wp_hose_check": "yes, hose is soft and cracked at the clamp",
            },
            "abs": {
                "q_abs_codes": "C0035, left front wheel speed",
                "q_abs_live": "yes, FL drops to zero",
                "q_abs_play": "no, FL hub tight and smooth",
                "q_abs_sensor": "yes, wire chafed on the strut, open circuit",
            },
            "wheel_bearings": {
                "q_whl_noise": "no noise, just the ABS and skid lights",
                "q_whl_play": "no, tight and smooth",
                "q_whl_sensor": "yes, FL sensor open circuit, wire chafed",
            },
        },
    ),
    dict(
        id="fabia_rain_lights_rattle",
        title="Lights go mad in the rain, and a rattle",
        date="2026-01-12",
        faults=["can_wiring_fault", "dual_mass_flywheel"],
        tags=["independent_faults"],
        report=(
            "Every time it rains my Fabia goes mad, all the warning lights come on at once and the speedo "
            "drops to zero. Twice it wouldn't start afterwards, it turned over but nothing. There's also a "
            "rattly noise when it's ticking over at the lights that goes away when I push the clutch in. "
            "I spilled a coffee in the passenger footwell a while back, sorry about the smell."
        ),
        vehicle={"make": "Skoda", "model": "Fabia", "year": 2014, "mileage_km": 176900},
        obd=[
            code("U0121", "Lost communication with ABS module", "active", 176850),
            code("U0155", "Lost communication with instrument cluster", "active", 176850),
            code("U0100", "Lost communication with ECM", "history", 176700),
            code("P2263", "Turbo boost system performance", "cleared", 168000),
        ],
        freeze={"battery_voltage_v": 13.9, "engine_rpm": 800, "vehicle_speed_kmh": 0, "coolant_temp_c": 86},
        service=[
            svc("2021-01-05", 118000, "Annual service"),
            svc("2022-01-20", 132000, "Annual service"),
            svc("2023-02-01", 148000, "Annual service"),
            svc("2024-02-15", 162000, "Annual service"),
            svc("2024-11-05", 168000, "Turbo actuator, code cleared"),
            svc("2025-11-20", 175300, "Annual service"),
        ],
        notes=[
            "Passenger footwell carpet wet. Green corrosion on the connector under it.",
            "CAN resistance at OBD pins 6 and 14: 120 Ω.",
            "Rattle at idle stops when the clutch pedal goes down.",
            "Flywheel free play 28 degrees, spec 15.",
            "Wiper blades smear.",
        ],
        answers={
            "can_bus": {
                "q_can_symptom": "all the lights come on at once and the gauges drop",
                "q_can_codes": "yes, U codes in the ABS, the cluster and the engine",
                "q_can_resistance": "120 Ω across 6 and 14",
                "q_can_wiring": "yes, wet carpet and green corrosion on the connector under the passenger footwell",
            },
            "ecu": {
                "q_ecu_symptom": "scan tool can't reach the engine ECU when it plays up",
                "q_ecu_supply": "yes, 12.4 V and 0.03 V ground drop",
                "q_ecu_can_resistance": "no, 120 Ω, not 60",
            },
            "fuel_pump": {"q_fp_symptom": "cranks at normal speed but won't fire when it does it"},
            "ignition": {
                "q_ign_symptom": "cranks but won't fire when it does it",
                "q_ign_rpm": "no, rpm reads 220 cranking",
            },
            "clutch": {
                "q_clu_symptom": "rattle at idle, stops with the clutch down",
                "q_clu_rattle": "yes, stops as soon as the pedal goes down",
                "q_clu_dmf_play": "yes, 28 degrees free play, spec 15",
                "q_clu_judder": "yes, a bit when pulling off",
            },
        },
    ),
    # ---------------------------------------------------------------- 3 faults
    dict(
        id="a4_shake_and_eggs",
        title="Shakes, no power, rotten eggs",
        date="2026-08-24",
        faults=["spark_plugs_worn", "ignition_coil", "catalytic_converter_blocked"],
        tags=["cascade"],
        report=(
            "The A4 is shaking at idle and the engine light was flashing on the motorway yesterday. It has "
            "no power going up hills anymore and there's a horrible smell like rotten eggs from the back. "
            "It's drinking fuel too. I bought it at auction in the spring, so I don't know much about its history."
        ),
        vehicle={"make": "Audi", "model": "A4", "year": 2010, "mileage_km": 205600},
        obd=[
            code("P0300", "Random or multiple cylinder misfire detected", "active", 205550),
            code("P0302", "Cylinder 2 misfire detected", "active", 205550),
            code("P0420", "Catalyst system efficiency below threshold, bank 1", "active", 205560),
            code("P0456", "Evaporative emission system very small leak", "cleared", 195000),
        ],
        freeze={"engine_rpm": 750, "engine_load_pct": 34, "coolant_temp_c": 90,
                "short_term_fuel_trim_pct": -2.3, "long_term_fuel_trim_pct": 3.1, "vehicle_speed_kmh": 0},
        service=[
            svc("2019-08-10", 140000, "Service and spark plugs"),
            svc("2021-09-01", 160000, "Annual service"),
            svc("2023-03-14", 180200, "Annual service"),
            svc("2024-07-22", 195000, "Evap valve, code cleared"),
            svc("2025-04-10", 201900, "Auction inspection, no work done"),
        ],
        notes=[
            "Plug gaps 1.3 mm, spec 0.8 mm, electrodes worn. Plugs look original to the 140,000 km service.",
            "Misfire moves to cylinder 3 when the coils of cylinders 2 and 3 are swapped.",
            "Coil 2 has a crack and a carbon track.",
            "Back pressure 5.5 psi at 2500 rpm. Converter outlet 40 °C cooler than the inlet.",
            "Old tax disc holder still on the windscreen.",
        ],
        answers={
            "ignition": {
                "q_ign_symptom": "misfires and shakes, the light flashed",
                "q_ign_one_cyl": "no, P0300 plus P0302",
                "q_ign_plugs": "worn, gaps 1.3 mm against 0.8",
                "q_ign_plug_swap": "yes, the random misfire is gone with new plugs, P0300 doesn't come back",
                "q_ign_coil_swap": "yes, P0302 moves to P0303",
                "q_ign_coil_check": "yes, coil 2 cracked with a carbon track",
                "q_ign_plug_one": "yes, cylinder 2 plug worn like the rest",
            },
            "injectors": {
                "q_inj_symptom": "P0302 misfire on cylinder 2",
                "q_inj_coil_swap": "yes, misfire follows the coil to cylinder 3",
            },
            "exhaust": {
                "q_exh_symptom": "no power up hills, rotten egg smell",
                "q_exh_backpressure": "yes, 5.5 psi at 2500",
                "q_exh_cat_temp": "yes, outlet 40 °C cooler than the inlet",
                "q_exh_o2_code": "no, only P0420",
                "q_exh_cat_compare": "yes, downstream switches like the upstream one",
            },
        },
    ),
    dict(
        id="vito_flat_and_squeal",
        title="Flat after parking, squeal on cold mornings",
        date="2026-03-30",
        faults=["alternator_diode_leak", "flat_battery", "aux_belt_slip"],
        tags=["cascade", "independent_faults"],
        report=(
            "The Vito keeps going flat if it's parked for a couple of days, I've had to jump it three times this "
            "month. When it does run, the headlights sort of pulse. There's a squeal from the engine on cold "
            "mornings, worse with the heater blower on. The sliding door is sticking as well but that's a "
            "separate thing."
        ),
        vehicle={"make": "Mercedes", "model": "Vito", "year": 2016, "mileage_km": 231400},
        obd=[
            code("P0562", "System voltage low", "pending", 231300),
            code("P2463", "Diesel particulate filter soot accumulation", "cleared", 222900),
        ],
        freeze={"battery_voltage_v": 12.9, "engine_rpm": 2000, "coolant_temp_c": 12, "ambient_temp_c": 1},
        service=[
            svc("2021-03-01", 172000, "Annual service"),
            svc("2022-03-10", 189000, "Annual service"),
            svc("2023-04-05", 205000, "Annual service"),
            svc("2024-04-18", 222900, "DPF regeneration, code cleared"),
            svc("2025-03-11", 228700, "Service, auxiliary belt glazed, replacement advised"),
            svc("2026-03-20", 231200, "Jump start callout, third this month"),
        ],
        notes=[
            "Sleep current 320 mA. It falls to 28 mA with the alternator B+ lead off.",
            "AC ripple 0.8 V at the battery with the engine running.",
            "Auxiliary belt glazed. Charge voltage 12.9 V before and 14.3 V after the belt is tensioned.",
            "Driver sun visor broken.",
        ],
        answers={
            "battery": {
                "q_bat_start": "fine after a jump, flat again after two days parked",
                "q_bat_drain": "320 mA once asleep",
                "q_bat_alt_unplug": "yes, drops to 28 mA with the B+ lead off",
                "q_bat_voltage": "11.8 V at rest",
                "q_bat_history": "yes, flat after two days with nothing on",
            },
            "alternator": {
                "q_alt_symptom": "squeal on cold mornings, worse with the blower on",
                "q_alt_run_voltage": "12.9 V at 2000 with the headlights on",
                "q_alt_belt": "yes, belt's glazed and squeals under load",
                "q_alt_belt_test": "yes, 14.3 V once it's tensioned",
                "q_alt_ripple": "yes, 0.8 V AC",
                "q_alt_diode_drain": "yes, 320 mA",
                "q_alt_drain_unplug": "yes, drops to 28 mA",
                "q_alt_output": "no, 170 A of 180 A once the belt's tight",
            },
            "starter": {
                "q_sta_symptom": "slow to turn when it's been sat",
                "q_sta_lights": "no, lights dim right down",
                "q_sta_battery_volt": "no, 11.8 V",
            },
        },
    ),
    dict(
        id="qashqai_steam_and_squeal",
        title="Steam on the dual carriageway, squealing brakes",
        date="2026-07-27",
        faults=["thermostat_stuck_closed", "head_gasket", "worn_pads"],
        tags=["cascade", "independent_faults"],
        report=(
            "The Qashqai overheated badly on the dual carriageway, steam everywhere, it came home on the back "
            "of a truck. Before that I'd noticed white smoke in the mornings and I was topping up the coolant. "
            "The brakes have also been squealing for weeks, and a red brake light flickers on corners. "
            "The charger socket in the back doesn't work either."
        ),
        vehicle={"make": "Nissan", "model": "Qashqai", "year": 2014, "mileage_km": 158900},
        obd=[
            code("P0217", "Engine coolant over temperature condition", "active", 158850),
            code("P0420", "Catalyst system efficiency below threshold, bank 1", "cleared", 150300),
        ],
        freeze={"coolant_temp_c": 124, "vehicle_speed_kmh": 105, "engine_rpm": 2700, "ambient_temp_c": 26},
        service=[
            svc("2021-07-05", 112000, "Annual service"),
            svc("2022-07-20", 125500, "Annual service"),
            svc("2023-08-01", 138000, "Annual service"),
            svc("2024-06-28", 150300, "Catalytic converter replaced, code cleared"),
            svc("2025-07-02", 155700, "Service, front pads advised soon"),
        ],
        notes=[
            "Thermostat stays shut at 90 °C in the pot test.",
            "With the gauge high, the top hose is only warm.",
            "Combustion leak test positive, bubbles from cylinder 1 on the leak-down test.",
            "Front pads 2 mm. Brake fluid at the minimum mark, no leaks.",
            "Rear 12 V socket fuse blown.",
        ],
        answers={
            "cooling_fan": {
                "q_fan_when": "on the dual carriageway at a steady 60",
                "q_fan_top_hose": "yes, top hose only warm with the gauge right up",
                "q_fan_runs": "yes, fan runs",
            },
            "thermostat": {
                "q_th_symptom": "overheats",
                "q_th_top_hose": "yes, top hose only warm with the gauge right up",
                "q_th_temp_diff": "yes, 115 °C engine side, 66 °C radiator side",
                "q_th_bench": "yes, stays shut at 90 °C in the pot",
            },
            "water_pump": {
                "q_wp_symptom": "losing coolant and white smoke in the mornings",
                "q_wp_visible": "no, no external leak",
                "q_wp_combustion": "yes, goes yellow",
                "q_wp_leakdown": "yes, bubbles from cylinder 1",
            },
            "brakes": {
                "q_brk_symptom": "squealing when braking",
                "q_brk_pads": "2 mm on the fronts",
                "q_brk_fluid_leak": "no, level at min but no leaks",
            },
        },
    ),
    dict(
        id="discovery_pedals_and_light",
        title="Soft brake pedal, clutch on the floor, engine light",
        date="2026-06-15",
        faults=["abs_pump_module", "clutch_hydraulic", "o2_sensor_fault"],
        tags=["independent_faults"],
        report=(
            "Lots going on with the Discovery. The ABS and traction lights came on last week and the brake "
            "pedal feels soft, it goes down further than it used to. The clutch pedal stayed on the floor "
            "twice this weekend and I had to pull it up with my foot, and the gears crunch going into first. "
            "The engine light's on too. We tow a horsebox most weekends."
        ),
        vehicle={"make": "Land Rover", "model": "Discovery Sport", "year": 2017, "mileage_km": 139200},
        obd=[
            code("C0121", "Valve relay circuit", "active", 139150),
            code("P0133", "O2 sensor circuit slow response, bank 1 sensor 1", "active", 139100),
            code("P0420", "Catalyst system efficiency below threshold, bank 1", "pending", 139120),
            code("P0299", "Turbocharger underboost", "cleared", 130500),
        ],
        freeze={"engine_rpm": 2300, "vehicle_speed_kmh": 70, "long_term_fuel_trim_pct": 7.8,
                "o2_sensor_b1s1_v": 0.45, "coolant_temp_c": 90},
        service=[
            svc("2021-06-10", 72000, "Annual service"),
            svc("2022-06-20", 91000, "Annual service"),
            svc("2023-07-05", 110400, "Annual service"),
            svc("2024-07-15", 130500, "Turbo actuator, code cleared"),
            svc("2025-06-01", 136000, "Service, brake fluid change"),
        ],
        notes=[
            "Brake pedal sinks during the ABS valve test on the front right channel.",
            "Shared brake and clutch reservoir below the minimum. Fluid at the clutch slave cylinder.",
            "No leak at the brake pipes, hoses or calipers.",
            "Upstream O2 sensor slow. Smoke test shows no exhaust leak.",
            "Tow bar electrics OK.",
        ],
        answers={
            "brakes": {
                "q_brk_symptom": "pedal is soft, goes down further",
                "q_brk_pump": "no, stays soft however much you pump it",
                "q_brk_fluid_leak": "no, level's low but it's going out the clutch slave, nothing on the brake side",
                "q_brk_abs_test": "yes, pedal sinks on the FR valve test, C0121 stored",
            },
            "abs": {
                "q_abs_codes": "C0121 valve relay",
                "q_abs_pump_run": "yes, pump runs on the actuator test",
                "q_abs_valves": "yes, FR channel fails",
            },
            "wheel_bearings": {"q_whl_noise": "no noise, just the ABS and traction lights"},
            "clutch": {
                "q_clu_symptom": "pedal stays on the floor, gears crunch",
                "q_clu_fluid": "yes, reservoir low and wet at the slave cylinder",
            },
            "exhaust": {
                "q_exh_symptom": "just the engine light, codes P0133 and P0420",
                "q_exh_smoke_test": "no, tight",
                "q_exh_o2_code": "yes, P0133",
                "q_exh_o2_switch": "yes, switches slowly",
                "q_exh_leak_before": "no, no leak before the sensor",
            },
        },
    ),
    dict(
        id="kangoo_not_itself",
        title="Not itself (vague)",
        date="2026-02-10",
        faults=["alternator_failure", "flat_battery", "starter_motor_worn"],
        tags=["cascade", "vague_report"],
        report=(
            "The Kangoo's not been itself. Starting it is hard work and it makes a horrible noise sometimes, "
            "and there's a light that comes on now and then when I'm driving. I use it for the dog grooming "
            "business so it's full of hair, sorry about that."
        ),
        vehicle={"make": "Renault", "model": "Kangoo", "year": 2012, "mileage_km": 187300},
        obd=[
            code("P0562", "System voltage low", "active", 187250),
            code("P0103", "Mass air flow circuit high", "cleared", 178600),
        ],
        freeze={"battery_voltage_v": 12.2, "engine_rpm": 2000, "coolant_temp_c": 85},
        service=[
            svc("2021-02-01", 142000, "Annual service"),
            svc("2022-02-15", 154500, "Annual service"),
            svc("2023-03-01", 165000, "Annual service"),
            svc("2024-03-10", 178600, "MAF sensor, code cleared"),
            svc("2025-02-20", 184400, "Service, new battery"),
        ],
        notes=[
            "Charge voltage 12.5 V at 2000 rpm with the headlights on. Alternator output 30 A of a 90 A rating.",
            "Starter draws 320 A and grinds during the crank.",
            "Battery 12 months old, 11.9 V at rest, passes the load test after a charge.",
            "Dog hair in the cabin filter housing.",
        ],
        answers={
            "alternator": {
                "q_alt_symptom": "battery light on and off while driving",
                "q_alt_run_voltage": "12.5 V at 2000 with the headlights on",
                "q_alt_belt": "no, belt's fine",
                "q_alt_field": "yes, 12 V at the D+",
                "q_alt_output": "yes, only 30 A of 90 A",
                "q_alt_ripple": "no, 0.2 V AC",
                "q_alt_diode_drain": "no, 30 mA",
            },
            "battery": {
                "q_bat_start": "cranks slow and grinds",
                "q_bat_voltage": "11.9 V at rest",
                "q_bat_charge_test": "yes, passes after a charge",
                "q_bat_history": "no, it doesn't go flat parked, it's just low after driving",
                "q_bat_age": "no, 12 months old",
            },
            "starter": {
                "q_sta_symptom": "slow and grinds",
                "q_sta_noise": "yes, 320 A and a grind",
                "q_sta_bench": "yes, grinds and drags on the bench",
                "q_sta_lights": "no, headlights dim",
                "q_sta_battery_volt": "no, 11.9 V",
            },
        },
    ),
]
