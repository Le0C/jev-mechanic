"""Generate data/v2/flowchart.json for the Jev mechanic demo, version 2.

Run from the project directory:
    .venv/bin/python <this file> [--paths]

The script writes the flowchart. With --paths, it also prints the TYPICAL_PATHS table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
V1 = json.loads((PROJECT / "data" / "flowchart.json").read_text())["diagnoses"]
OUT = PROJECT / "data" / "v2" / "flowchart.json"

NS = "Not known, or the answer does not say"
HIGH = 0.9  # P(option | diagnosis) for the option on the shortest route to the diagnosis
OFF_TREE = 0.3  # P(option | diagnosis) for a diagnosis that no option of the node reaches
STRONG = 0.95  # HIGH for a direct measurement that separates two look-alike faults
# The typical answer of a node for a diagnosis, where the shortest route does not give it.
PREFER = {
    ("q_bat_start", "battery_end_of_life"): "no_start",
    ("q_ign_one_cyl", "spark_plugs_worn"): "no",
    ("q_ecu_supply", "ecu_power_supply"): "no",
    ("q_alt_run_voltage", "alternator_failure"): "low",
    ("q_whl_noise", "wheel_bearing_worn"): "hum",
}
BEST: dict[tuple[str, str], str] = {}
STRONG_NODES = {
    "q_bat_alt_unplug", "q_alt_drain_unplug", "q_fp_filter_swap", "q_ign_plug_swap",
    "q_whl_play", "q_abs_play", "q_ecu_supply", "q_can_ecu_supply",
}

# ---------------------------------------------------------------- components

COMPONENTS = {
    "battery": ("Battery", "The 12 V battery, its terminals and the earth strap, and the current that the parked car takes"),
    "alternator": ("Alternator and belt", "The alternator, its regulator and diodes, and the auxiliary belt that drives it"),
    "starter": ("Starter motor", "The starter motor and its solenoid"),
    "fuel_pump": ("Fuel pump and filter", "The in-tank fuel pump, its relay, and the fuel filter"),
    "injectors": ("Fuel injectors", "The fuel injectors and the fuel mixture that they give"),
    "ignition": ("Ignition", "The ignition coils, the spark plugs and the crankshaft position sensor"),
    "cooling_fan": ("Radiator fan", "The radiator fan motor, its fuse and its relay"),
    "thermostat": ("Thermostat", "The thermostat that controls the coolant flow through the radiator"),
    "water_pump": ("Water pump and coolant circuit", "The water pump, the coolant hoses and the head gasket"),
    "brakes": ("Brakes", "The pads, the discs, the calipers and the brake hydraulics"),
    "abs": ("ABS", "The wheel speed sensors and the ABS pump and valve module"),
    "wheel_bearings": ("Wheel bearings and drive shafts", "The wheel bearings, the hubs and the constant velocity joints"),
    "can_bus": ("CAN bus", "The CAN network wires, connectors and the gateway module"),
    "ecu": ("Engine ECU", "The engine control unit, its power supply and the immobiliser"),
    "clutch": ("Clutch", "The clutch plate, the clutch hydraulics and the dual-mass flywheel"),
    "exhaust": ("Exhaust", "The exhaust pipes and boxes, the catalytic converter and the oxygen sensors"),
}

# ---------------------------------------------------------------- symptoms

SYMPTOMS = {
    # battery and charge
    "slow_crank": ("Slow crank", "The engine turns slowly when the driver starts it"),
    "click_no_crank": ("Click, no crank", "One click or rapid clicks at the start, and the engine does not turn"),
    "dim_lights": ("Dim lights", "The headlights or the dashboard lights are dimmer than normal"),
    "flat_after_standing": ("Flat after standing", "The battery is flat after the car stands for a night or a few days"),
    "low_resting_voltage": ("Low resting voltage", "Sensor value: the resting battery voltage is less than 12.2 V"),
    "old_battery": ("Old battery", "Service history: the battery is more than five years old"),
    "terminal_corrosion": ("Terminal corrosion", "Technician note: a white or green deposit on the battery terminals"),
    "jump_start_history": ("Recent jump starts", "Service history: the car needed a jump start in the last month"),
    "battery_light": ("Battery light while driving", "The battery warning light comes on while the engine runs"),
    "low_charge_voltage": ("Low charge voltage", "Code P0562, or a charge voltage of less than 13.2 V at 2000 rpm"),
    "belt_squeal": ("Belt squeal", "A squeal from the engine bay, worst at a cold start or with the lights and heater on"),
    "flickering_lights": ("Flickering lights", "The lights flicker or pulse with the engine speed"),
    "starter_grind": ("Starter grind", "A grinding or whirring noise from the starter at the start"),
    "starter_intermittent": ("Starter works sometimes", "The starter works on some attempts and not on others"),
    # fuel, injection and ignition
    "crank_no_start": ("Cranks but does not fire", "The engine turns at normal speed but does not start"),
    "no_pump_prime": ("No fuel pump hum", "No hum from the fuel tank for two seconds when the ignition turns on"),
    "low_fuel_pressure": ("Low fuel pressure", "Code P0087, or a fuel rail pressure less than the specification"),
    "lean_code": ("Lean mixture code", "Code P0171 or P0174, the fuel mixture is too lean"),
    "hesitation": ("Hesitation", "The engine hesitates or stumbles when the driver accelerates hard"),
    "power_loss": ("Loss of power", "The car lacks power, most at high speed or up a hill"),
    "fuel_filter_overdue": ("Fuel filter overdue", "Service history: the fuel filter change is overdue"),
    "single_misfire_code": ("One-cylinder misfire code", "Code P0301 to P0304, a misfire on one cylinder"),
    "random_misfire_code": ("Random misfire code", "Code P0300, misfires on more than one cylinder"),
    "rough_idle": ("Rough idle", "The engine shakes or idles unevenly when the car is stationary"),
    "flashing_mil": ("Flashing engine light", "The engine warning light flashes while the car drives"),
    "high_fuel_use": ("High fuel use", "The fuel consumption is higher than normal"),
    "plugs_overdue": ("Spark plugs overdue", "Service history: the spark plug change is overdue"),
    "no_rpm_signal": ("No rpm signal", "Code P0335, or the rpm reads zero while the engine cranks"),
    # cooling
    "overheat_gauge": ("Overheats", "The temperature gauge goes into the red, or a coolant temperature warning comes on"),
    "overheat_in_traffic": ("Overheats in traffic", "The engine overheats when the car is stationary or in slow traffic"),
    "overheat_on_road": ("Overheats at speed", "The engine overheats at a steady speed on the open road"),
    "coolant_temp_high": ("High coolant temperature", "Code P0217, or a coolant temperature of more than 110 °C"),
    "fan_not_running": ("Fan does not run", "Technician note: the radiator fan does not run when the engine is hot"),
    "heater_cold": ("Cold heater", "The heater blows cold or only warm air"),
    "slow_warm_up": ("Slow warm-up", "The temperature gauge stays low or takes a long time to rise"),
    "p0128_code": ("Thermostat code", "Code P0128, the coolant temperature stays below the thermostat temperature"),
    "coolant_loss": ("Coolant loss", "The coolant level drops between top-ups"),
    "coolant_puddle": ("Coolant puddle", "A pink, blue or green puddle under the front of the car"),
    "sweet_smell": ("Sweet smell", "A sweet smell of coolant near the car or in the cabin"),
    "white_smoke": ("White smoke", "Thick white smoke with a sweet smell from the exhaust"),
    # brakes and wheels
    "brake_squeal": ("Brake squeal or grind", "A squeal or a metal grind when the driver brakes"),
    "brake_vibration": ("Brake vibration", "The pedal or the steering wheel shakes when the driver brakes"),
    "pull_when_braking": ("Pulls when braking", "The car pulls to one side when the driver brakes"),
    "hot_wheel": ("Hot wheel", "Technician note: one wheel is much hotter than the others after a drive"),
    "burning_smell": ("Burning smell", "A burning smell after a drive, a hill start or a tow"),
    "soft_pedal": ("Soft brake pedal", "The brake pedal is soft or spongy, or goes down too far"),
    "brake_warning_light": ("Brake warning light", "The red brake warning light is on"),
    "low_brake_fluid": ("Low brake fluid", "Technician note: the brake fluid level is below the minimum mark"),
    "abs_light": ("ABS light", "The ABS warning light is on"),
    "wheel_speed_code": ("Wheel speed code", "Code C0035 to C0050, a wheel speed sensor signal fault"),
    "traction_light": ("Traction control light", "The traction or stability control light is on"),
    "wheel_hum": ("Wheel hum", "A hum or drone from one wheel that rises with the road speed"),
    "click_on_turns": ("Click on turns", "A click or a knock from a front wheel on full lock"),
    "split_boot": ("Split drive shaft boot", "Technician note: a split drive shaft boot, and grease on the wheel arch"),
    # networks and control units
    "lost_comm_code": ("Lost communication code", "Code U0100 to U0155, a module lost communication on the bus"),
    "many_warning_lights": ("Many warning lights", "Several warning lights come on at the same time, or the gauges drop to zero"),
    "no_scan_link": ("No scan tool link", "The scan tool cannot connect to the engine ECU"),
    "security_light": ("Security light", "The key or security light flashes on the dashboard"),
    "water_ingress": ("Water ingress", "Technician note: water in a footwell, or corrosion at a connector"),
    # clutch
    "revs_no_speed": ("Revs without speed", "The engine revs rise but the road speed does not, in a high gear"),
    "hard_gear_change": ("Hard gear change", "The gears are hard to engage or grind, most at a standstill"),
    "clutch_pedal_floor": ("Clutch pedal to the floor", "The clutch pedal goes to the floor or stays down"),
    "idle_rattle": ("Rattle at idle", "A rattle from the gearbox area at idle that stops when the clutch pedal is down"),
    "pull_away_judder": ("Judder when pulling away", "The car shudders when it pulls away in first gear"),
    # exhaust
    "loud_exhaust": ("Loud exhaust", "A loud exhaust, or a tick or blow at a cold start"),
    "cat_code": ("Catalyst code", "Code P0420, the catalytic converter efficiency is below the threshold"),
    "rotten_egg_smell": ("Rotten egg smell", "A smell of rotten eggs from the exhaust"),
    "o2_code": ("Oxygen sensor code", "Code P0130 to P0141, an oxygen sensor circuit or response fault"),
}

# ---------------------------------------------------------------- diagnoses
# id: (primary component, label, description, prior, explains, causes, fix or v1 id)

D = {}


def dx(did, comp, label, desc, prior, explains, fix, causes=()):
    D[did] = dict(comp=comp, label=label, description=desc, prior=prior,
                  explains=list(explains), causes=list(causes), fix=fix)


def v1(did, key=None):
    return V1[key or did]["fix"]


dx("flat_battery", "battery", V1["flat_battery"]["label"], V1["flat_battery"]["description"], 0.12,
   ["slow_crank", "click_no_crank", "dim_lights", "low_resting_voltage", "jump_start_history"], v1("flat_battery"))
dx("battery_end_of_life", "battery", V1["battery_end_of_life"]["label"], V1["battery_end_of_life"]["description"], 0.08,
   ["slow_crank", "flat_after_standing", "low_resting_voltage", "old_battery"], v1("battery_end_of_life"))
dx("battery_terminals", "battery", V1["battery_terminals"]["label"], V1["battery_terminals"]["description"], 0.05,
   ["click_no_crank", "dim_lights", "terminal_corrosion", "starter_intermittent"], v1("battery_terminals"))
dx("parasitic_drain", "battery", V1["parasitic_drain"]["label"], V1["parasitic_drain"]["description"], 0.03,
   ["flat_after_standing", "low_resting_voltage", "jump_start_history"], v1("parasitic_drain"),
   causes=["flat_battery"])

dx("alternator_failure", "alternator", V1["alternator_failure"]["label"], V1["alternator_failure"]["description"], 0.05,
   ["battery_light", "low_charge_voltage", "dim_lights", "flickering_lights"], v1("alternator_failure"),
   causes=["flat_battery"])
dx("aux_belt_slip", "alternator", V1["aux_belt_slip"]["label"], V1["aux_belt_slip"]["description"], 0.04,
   ["belt_squeal", "battery_light", "low_charge_voltage"], v1("aux_belt_slip"))
dx("alternator_diode_leak", "alternator", "Leaking alternator diode",
   "A defective rectifier diode lets current flow back through the alternator while the car is parked", 0.02,
   ["flat_after_standing", "low_resting_voltage", "jump_start_history", "flickering_lights"],
   ["Charge the battery fully.",
    "Measure the sleep current with a clamp meter on the battery negative cable.",
    "Disconnect the alternator B+ lead and measure the sleep current again.",
    "Do an AC ripple test at the battery with the engine at 2000 rpm, 0.5 V AC maximum.",
    "Replace the alternator or its rectifier.",
    "Measure the sleep current again, 50 mA maximum."],
   causes=["flat_battery"])

dx("starter_motor_worn", "starter", "Worn starter motor",
   "The brushes, the bearings or the armature of the starter are worn, so it turns slowly or grinds", 0.04,
   ["slow_crank", "starter_grind", "starter_intermittent"], v1("starter_motor", "starter_motor"))
dx("starter_solenoid", "starter", "Starter solenoid failure",
   "The solenoid contacts are burnt, so the solenoid clicks but sends no current to the starter motor", 0.03,
   ["click_no_crank", "starter_intermittent"],
   ["Measure the voltage at the solenoid trigger terminal while the key is at start.",
    "Measure the voltage at the motor terminal of the solenoid during the same attempt.",
    "Disconnect the battery negative terminal.",
    "Remove the starter motor.",
    "Replace the solenoid, or the starter assembly if the solenoid is not a separate part.",
    "Install the starter and tighten the bolts to the torque value.",
    "Connect the battery and do five start tests."])

dx("fuel_pump_failed", "fuel_pump", V1["fuel_pump"]["label"], V1["fuel_pump"]["description"], 0.04,
   ["crank_no_start", "no_pump_prime", "low_fuel_pressure"], v1("fuel_pump", "fuel_pump"))
dx("fuel_pump_weak", "fuel_pump", "Weak fuel pump",
   "The fuel pump runs but cannot hold the fuel pressure at high load", 0.04,
   ["low_fuel_pressure", "lean_code", "hesitation", "power_loss"],
   ["Connect a fuel pressure gauge and measure the pressure at idle and at full load.",
    "Measure the pump delivery volume in 30 s.",
    "Release the fuel pressure and disconnect the battery negative terminal.",
    "Remove the access cover and replace the fuel pump module with a new seal.",
    "Connect the battery and examine the pump for leaks.",
    "Measure the fuel pressure at full load on a road test."])
dx("fuel_filter_clogged", "fuel_pump", V1["fuel_filter"]["label"], V1["fuel_filter"]["description"], 0.03,
   ["low_fuel_pressure", "hesitation", "power_loss", "fuel_filter_overdue"], v1("fuel_filter", "fuel_filter"),
   causes=["fuel_pump_weak"])

dx("injector_clogged", "injectors", "Clogged injectors",
   "Deposits restrict the injectors, so all cylinders get too little fuel", 0.04,
   ["lean_code", "hesitation", "random_misfire_code", "rough_idle"],
   ["Read the fuel trims at idle and at 2500 rpm.",
    "Do a smoke test on the intake to find a vacuum leak.",
    "Remove the fuel rail and the injectors.",
    "Do a flow test and clean the injectors in an ultrasonic cleaner.",
    "Replace an injector that stays below 90 percent of its rated flow.",
    "Install the injectors with new seals and clear the fuel trims.",
    "Do a road test and read the fuel trims again, within 10 percent."])
dx("injector_stuck", "injectors", "Stuck injector",
   "One injector sticks open or closed, so one cylinder misfires", 0.03,
   ["single_misfire_code", "rough_idle", "flashing_mil", "high_fuel_use"],
   ["Read the misfire codes and find the cylinder.",
    "Do an injector balance test.",
    "Release the fuel pressure and disconnect the battery negative terminal.",
    "Remove the defective injector.",
    "Install the new injector with new seals.",
    "Code the injector to the ECU with the diagnostic tool if the ECU requires it.",
    "Clear the codes and do a road test under load."])

dx("ignition_coil", "ignition", V1["ignition_coil"]["label"], V1["ignition_coil"]["description"], 0.05,
   ["single_misfire_code", "rough_idle", "flashing_mil", "hesitation"], v1("ignition_coil"),
   causes=["catalytic_converter_blocked"])
dx("spark_plugs_worn", "ignition", V1["spark_plugs"]["label"], V1["spark_plugs"]["description"], 0.06,
   ["random_misfire_code", "rough_idle", "high_fuel_use", "plugs_overdue"], v1("spark_plugs", "spark_plugs"),
   causes=["ignition_coil"])
dx("crank_sensor", "ignition", V1["crank_sensor"]["label"], V1["crank_sensor"]["description"], 0.03,
   ["crank_no_start", "no_rpm_signal"], v1("crank_sensor"))

dx("radiator_fan_motor", "cooling_fan", "Radiator fan motor failure",
   "The radiator fan motor is seized or burnt, so the engine overheats at low speed and in traffic", 0.03,
   ["overheat_gauge", "overheat_in_traffic", "fan_not_running", "coolant_temp_high"], v1("radiator_fan", "radiator_fan"),
   causes=["head_gasket"])
dx("fan_relay", "cooling_fan", "Radiator fan relay failure",
   "The fan relay does not close when the ECU commands the fan, so the fan motor gets no power", 0.03,
   ["overheat_in_traffic", "fan_not_running", "coolant_temp_high"],
   ["Read the fan command in the live data with the engine hot.",
    "Listen for a click from the fan relay when the ECU commands the fan.",
    "Measure the voltage at the relay output terminal.",
    "Replace the fan relay.",
    "Run the engine to operating temperature and make sure that the fan starts."])

dx("thermostat_stuck_closed", "thermostat", V1["thermostat_stuck"]["label"], V1["thermostat_stuck"]["description"], 0.05,
   ["overheat_gauge", "overheat_on_road", "coolant_temp_high"], v1("thermostat_stuck", "thermostat_stuck"),
   causes=["head_gasket"])
dx("thermostat_stuck_open", "thermostat", "Thermostat stuck open",
   "The thermostat does not close, so the engine does not reach its operating temperature", 0.05,
   ["slow_warm_up", "p0128_code", "heater_cold", "high_fuel_use"],
   ["Compare the coolant sensor value with an infrared reading at the engine.",
    "Let the engine cool fully and drain the coolant.",
    "Remove the thermostat housing and the thermostat.",
    "Install the new thermostat with a new seal and the correct orientation.",
    "Fill the system with coolant and bleed the air.",
    "Clear code P0128 and do a road test until the gauge reaches the normal position."])

dx("water_pump_leak", "water_pump", "Water pump seal leak",
   "The water pump leaks at its seal, so coolant comes out at the weep hole", 0.03,
   ["coolant_loss", "coolant_puddle", "sweet_smell", "overheat_gauge"], v1("water_pump", "water_pump"))
dx("water_pump_impeller", "water_pump", "Worn water pump impeller",
   "The impeller is eroded or loose on its shaft, so the coolant does not circulate at speed", 0.02,
   ["overheat_gauge", "overheat_on_road", "heater_cold", "coolant_temp_high"],
   ["Measure the temperature of the top hose and the bottom hose with an infrared thermometer.",
    "Let the engine cool fully and drain the coolant.",
    "Remove the belt that drives the pump.",
    "Remove the water pump and examine the impeller.",
    "Install the new pump with a new gasket and set the belt tension.",
    "Fill the system with coolant and bleed the air.",
    "Do a road test at motorway speed and read the coolant temperature."])
dx("coolant_hose_leak", "water_pump", V1["coolant_hose_leak"]["label"], V1["coolant_hose_leak"]["description"], 0.05,
   ["coolant_loss", "coolant_puddle", "sweet_smell"], v1("coolant_hose_leak"))
dx("head_gasket", "water_pump", V1["head_gasket"]["label"], V1["head_gasket"]["description"], 0.02,
   ["white_smoke", "coolant_loss", "sweet_smell", "overheat_gauge"], v1("head_gasket"))

dx("worn_pads", "brakes", V1["worn_pads"]["label"], V1["worn_pads"]["description"], 0.1,
   ["brake_squeal", "brake_warning_light", "low_brake_fluid"], v1("worn_pads"))
dx("warped_discs", "brakes", V1["warped_discs"]["label"], V1["warped_discs"]["description"], 0.05,
   ["brake_vibration", "pull_when_braking"], v1("warped_discs"))
dx("sticking_caliper", "brakes", V1["sticking_caliper"]["label"], V1["sticking_caliper"]["description"], 0.03,
   ["pull_when_braking", "hot_wheel", "burning_smell"], v1("sticking_caliper"),
   causes=["warped_discs"])
dx("air_in_brakes", "brakes", V1["air_in_brakes"]["label"], V1["air_in_brakes"]["description"], 0.02,
   ["soft_pedal", "brake_warning_light", "low_brake_fluid"], v1("air_in_brakes"))

dx("abs_wheel_sensor", "abs", "ABS wheel speed sensor fault",
   "A wheel speed sensor or its wire gives no signal or a bad signal", 0.05,
   ["abs_light", "wheel_speed_code", "traction_light"],
   ["Read the ABS fault codes and find the wheel.",
    "Compare the wheel speeds in the live data on a road test.",
    "Examine the sensor wire and the connector for damage.",
    "Measure the sensor resistance or the signal.",
    "Clean the sensor mounting and install the new sensor.",
    "Clear the codes and do a road test above 30 km/h."])
dx("abs_pump_module", "abs", "ABS pump and valve module fault",
   "The ABS pump motor or a valve in the hydraulic module fails", 0.02,
   ["abs_light", "traction_light", "soft_pedal", "brake_warning_light"],
   ["Read the ABS fault codes.",
    "Do the pump and valve actuator tests with the diagnostic tool.",
    "Measure the supply voltage at the pump motor fuse and the module connector.",
    "Replace the ABS module or send it for repair.",
    "Code the module to the vehicle with the diagnostic tool.",
    "Do the ABS bleed procedure with the diagnostic tool.",
    "Clear the codes and make sure that the pedal is firm, then do a road test."])

dx("wheel_bearing_worn", "wheel_bearings", "Worn wheel bearing",
   "A wheel bearing has play or rough races, so it hums, and it can disturb the wheel speed signal", 0.05,
   ["wheel_hum", "abs_light", "wheel_speed_code", "traction_light"],
   ["Lift the car and examine each wheel for play and a rough feel.",
    "Remove the wheel, the caliper and the disc.",
    "Remove the hub or press out the bearing.",
    "Install the new bearing or hub with the magnetic encoder toward the sensor.",
    "Install the disc, the caliper and the wheel, and tighten to the torque values.",
    "Clear the ABS codes and do a road test."])
dx("cv_joint_worn", "wheel_bearings", "Worn CV joint",
   "The outer constant velocity joint of a drive shaft is worn, most often after the boot split", 0.04,
   ["click_on_turns", "split_boot"],
   ["Do a road test in a tight circle and find the side that clicks.",
    "Lift the car and remove the wheel.",
    "Remove the hub nut and the drive shaft.",
    "Install a new drive shaft, or a new joint and boot with the correct grease.",
    "Tighten the hub nut to the torque value.",
    "Do a road test in tight circles in both directions."])

dx("can_wiring_fault", "can_bus", "CAN wiring fault",
   "Water, corrosion or chafe damages a CAN wire or connector, so the modules lose communication", 0.03,
   ["lost_comm_code", "many_warning_lights", "no_scan_link", "water_ingress", "crank_no_start"],
   ["Read the lost-communication codes in all modules.",
    "Measure the resistance between OBD pins 6 and 14 with the battery disconnected, 60 Ω.",
    "Examine the connectors near water entry points for corrosion.",
    "Divide the bus into sections and find the damaged section.",
    "Repair the wire or replace the connector, and seal it.",
    "Clear the codes in all modules and do a road test."])
dx("can_gateway_fault", "can_bus", "Gateway module fault",
   "The gateway module does not pass messages between the CAN networks", 0.02,
   ["lost_comm_code", "many_warning_lights"],
   ["Read the codes in all modules and find the network that lost communication.",
    "Measure the supply and the ground at the gateway module.",
    "Replace the gateway module.",
    "Code the new module to the vehicle with the diagnostic tool.",
    "Clear the codes in all modules and do a road test."])

dx("ecu_power_supply", "ecu", "ECU power supply fault",
   "The ECU main relay, a fuse, or a supply or ground wire fails, so the engine ECU gets no power", 0.03,
   ["no_scan_link", "crank_no_start", "lost_comm_code", "many_warning_lights"],
   ["Measure the supply voltage at the ECU connector with the ignition on.",
    "Examine the ECU main relay and the ECU fuses.",
    "Measure the voltage drop on the ECU ground wires, 0.1 V maximum.",
    "Replace the relay or the fuse, or repair the wire.",
    "Clear the codes in all modules and do a start test."])
dx("immobiliser_fault", "ecu", V1["immobiliser_fault"]["label"], V1["immobiliser_fault"]["description"], 0.03,
   ["crank_no_start", "security_light"], v1("immobiliser_fault"))
dx("ecu_internal_fault", "ecu", "ECU internal fault",
   "The engine ECU has an internal fault, so it does not respond although it has good power and a good bus", 0.01,
   ["no_scan_link", "lost_comm_code", "water_ingress"],
   ["Measure the supply and the ground at the ECU connector.",
    "Examine the ECU housing and the connector for water.",
    "Tell the customer the cost of the repair and get approval before the work.",
    "Replace the ECU, or send it for repair.",
    "Program the ECU and the immobiliser data with the diagnostic tool.",
    "Clear the codes in all modules and do a road test."])

dx("clutch_slip", "clutch", "Slipping clutch",
   "The clutch friction plate is worn or oily, so it slips under load", 0.04,
   ["revs_no_speed", "burning_smell", "pull_away_judder"],
   ["Do a clutch stall test in a high gear with the handbrake on.",
    "Examine the clutch adjustment and the release system.",
    "Remove the gearbox.",
    "Replace the clutch plate, the pressure plate and the release bearing.",
    "Examine the flywheel face and the crankshaft seal for oil.",
    "Install the gearbox and do a road test."])
dx("clutch_hydraulic", "clutch", "Clutch hydraulic fault",
   "The clutch master or slave cylinder leaks, so the clutch does not release fully", 0.03,
   ["clutch_pedal_floor", "hard_gear_change", "low_brake_fluid"],
   ["Examine the fluid level in the shared reservoir.",
    "Examine the slave cylinder and the footwell for fluid.",
    "Replace the master cylinder or the slave cylinder that leaks.",
    "Bleed the clutch hydraulics.",
    "Make sure that all gears engage at a standstill, then do a road test."])
dx("dual_mass_flywheel", "clutch", "Worn dual-mass flywheel",
   "The springs of the dual-mass flywheel are worn, so it rattles at idle and judders when the car pulls away", 0.03,
   ["idle_rattle", "pull_away_judder"],
   ["Measure the free rotation and the rock of the flywheel with the gearbox removed.",
    "Remove the clutch and the flywheel.",
    "Install a new flywheel with new bolts, and tighten to the torque sequence.",
    "Install a new clutch kit.",
    "Install the gearbox and do a road test."])

dx("exhaust_leak", "exhaust", "Exhaust leak",
   "A cracked manifold, a failed gasket or a hole lets exhaust gas out before the rear box", 0.05,
   ["loud_exhaust", "o2_code", "cat_code"],
   ["Do a smoke test on the exhaust and find the leak.",
    "Let the exhaust cool fully.",
    "Replace the gasket, the section or the manifold that leaks.",
    "Tighten the clamps and the flange nuts to the torque values.",
    "Clear the codes and do a road test."])
dx("catalytic_converter_blocked", "exhaust", "Blocked catalytic converter",
   "The catalytic converter is melted or blocked, so the exhaust back pressure is too high", 0.03,
   ["power_loss", "cat_code", "rotten_egg_smell"],
   ["Measure the exhaust back pressure at 2500 rpm.",
    "Compare the inlet and outlet temperatures of the converter.",
    "Find and repair the misfire or the fuel fault that damaged the converter.",
    "Replace the catalytic converter with new gaskets.",
    "Clear the codes and do a road test at full load."])
dx("o2_sensor_fault", "exhaust", "Oxygen sensor fault",
   "An oxygen sensor responds slowly or its heater fails, so the fuel control is wrong", 0.04,
   ["o2_code", "cat_code", "high_fuel_use"],
   ["Read the oxygen sensor codes and the live sensor values.",
    "Measure the sensor heater resistance.",
    "Remove the sensor with a sensor socket.",
    "Apply anti-seize compound to the thread of the new sensor and install it.",
    "Clear the codes and do a road test."])

# ---------------------------------------------------------------- nodes

NODES: dict[str, dict] = {}
ENTRY: dict[str, str] = {}


def q(nid, question, options, not_sure):
    NODES[nid] = {"question": question,
                  "options": {**{o: {"text": t, "next": n} for o, t, n in options},
                              "not_sure": {"text": NS, "next": not_sure}}}


def yn(nid, question, yes_text, yes_next, no_text, no_next, not_sure):
    q(nid, question, [("yes", yes_text, yes_next), ("no", no_text, no_next)], not_sure)


SP = "specialist"

# battery
ENTRY["battery"] = "q_bat_start"
q("q_bat_start", "What does the battery problem look like?", [
    ("no_start", "The engine turns slowly, only clicks, or does not turn", "q_bat_terminals"),
    ("flat_after_standing", "The car starts after a charge or a jump, but it is flat again after it stands", "q_bat_drain"),
], "q_bat_terminals")
yn("q_bat_terminals", "Are the battery terminals or the earth strap corroded, loose or hot to touch?",
   "Yes, there is corrosion, a loose clamp or a hot terminal", "q_bat_terminal_drop",
   "No, the terminals are clean and tight", "q_bat_voltage", "q_bat_voltage")
yn("q_bat_terminal_drop", "During a start attempt, is the voltage drop across a terminal or the earth strap more than 0.5 V?",
   "Yes, more than 0.5 V", "battery_terminals", "No, 0.5 V or less", "q_bat_voltage", "battery_terminals")
q("q_bat_voltage", "What is the battery voltage at rest, with the engine off?", [
    ("below_12_2", "Less than 12.2 V", "q_bat_charge_test"),
    ("mid", "From 12.2 V to 12.4 V", "q_bat_charge_test"),
    ("above_12_4", "More than 12.4 V", SP),
], "q_bat_charge_test")
yn("q_bat_charge_test", "After a full charge, does the battery pass a load test?",
   "Yes, it passes the load test", "q_bat_history", "No, it fails the load test", "q_bat_age", "q_bat_age")
yn("q_bat_age", "Is the battery more than five years old, or does the tester report a low state of health?",
   "Yes, it is old or its state of health is low", "battery_end_of_life",
   "No, it is newer and the tester does not report a low state of health", "q_bat_cell", "battery_end_of_life")
yn("q_bat_cell", "Does the voltage fall below 12.4 V within 12 hours after the charge?",
   "Yes, the voltage falls", "battery_end_of_life", "No, the voltage holds", SP, SP)
yn("q_bat_history", "Did the battery go flat while the car stood for more than a day with nothing left on?",
   "Yes, it went flat with nothing left on", "q_bat_drain",
   "No, lights were left on, or the car makes only short trips", "flat_battery", "flat_battery")
q("q_bat_drain", "With the car locked and asleep, what is the current from the battery?", [
    ("high", "More than 50 mA", "q_bat_alt_unplug"),
    ("normal", "50 mA or less", "battery_end_of_life"),
], "q_bat_alt_unplug")
yn("q_bat_alt_unplug", "Disconnect the alternator B+ lead. Does the drain fall below 50 mA?",
   "Yes, the drain falls below 50 mA", "alternator_diode_leak",
   "No, the drain stays high", "parasitic_drain", "parasitic_drain")

# alternator
ENTRY["alternator"] = "q_alt_symptom"
q("q_alt_symptom", "What does the charge problem look like?", [
    ("warning_light", "The battery light comes on, or the lights go dim, while the engine runs", "q_alt_run_voltage"),
    ("squeal", "A belt squeal from the engine bay, worst at a cold start or with the lights and heater on", "q_alt_belt"),
    ("flat_after_standing", "The battery goes flat after the car stands, and the lights flicker when it runs", "q_alt_ripple"),
], "q_alt_run_voltage")
q("q_alt_run_voltage", "What is the battery voltage with the engine at 2000 rpm and the headlights on?", [
    ("low", "Less than 13.2 V", "q_alt_belt"),
    ("normal", "From 13.8 V to 14.7 V", "q_alt_ripple"),
    ("high", "More than 15 V", "alternator_failure"),
], "q_alt_belt")
yn("q_alt_belt", "Is the auxiliary belt glazed, cracked or loose, or does it squeal under electrical load?",
   "Yes, the belt is worn or loose, or it squeals", "q_alt_belt_test",
   "No, the belt is in good condition and quiet", "q_alt_field", "q_alt_field")
yn("q_alt_belt_test", "With the belt tension set correctly, does the charge voltage rise to 13.8 V or more?",
   "Yes, the charge voltage becomes normal", "aux_belt_slip",
   "No, the charge voltage stays low", "q_alt_field", "aux_belt_slip")
yn("q_alt_field", "With the ignition on, is there voltage at the warning-lamp or field terminal of the alternator?",
   "Yes, there is voltage", "q_alt_output", "No, there is no voltage", SP, "q_alt_output")
yn("q_alt_output", "Does an output test show less than 70 percent of the rated alternator current?",
   "Yes, the output is low", "alternator_failure", "No, the output is at the rating", SP, "alternator_failure")
yn("q_alt_ripple", "With the engine running, does an AC ripple test at the battery show more than 0.5 V AC?",
   "Yes, more than 0.5 V AC", "q_alt_diode_drain", "No, 0.5 V AC or less", "q_alt_drain_unplug", "q_alt_drain_unplug")
yn("q_alt_diode_drain", "With the car locked and asleep, is the current from the battery more than 50 mA?",
   "Yes, more than 50 mA", "q_alt_drain_unplug", "No, 50 mA or less", "alternator_failure", "q_alt_drain_unplug")
yn("q_alt_drain_unplug", "Disconnect the alternator B+ lead. Does the drain fall below 50 mA?",
   "Yes, the drain falls below 50 mA", "alternator_diode_leak",
   "No, the drain stays high", "parasitic_drain", SP)

# starter
ENTRY["starter"] = "q_sta_symptom"
q("q_sta_symptom", "What does the starter do when the driver starts the engine?", [
    ("click", "A single click, and the engine does not turn", "q_sta_lights"),
    ("slow_grind", "The engine turns slowly, or the starter grinds or whirs", "q_sta_noise"),
    ("intermittent", "The starter works on some attempts only", "q_sta_tap"),
], "q_sta_lights")
yn("q_sta_lights", "Do the headlights stay bright during the start attempt?",
   "Yes, the headlights stay bright", "q_sta_solenoid_volt",
   "No, the headlights go dim or out", "q_sta_battery_volt", "q_sta_battery_volt")
yn("q_sta_battery_volt", "Is the battery voltage at rest more than 12.4 V?",
   "Yes, more than 12.4 V", "q_sta_solenoid_volt", "No, 12.4 V or less", "flat_battery", "q_sta_solenoid_volt")
yn("q_sta_solenoid_volt", "While the key is at start, is there more than 10 V at the solenoid trigger terminal?",
   "Yes, more than 10 V", "q_sta_output_volt", "No, 10 V or less", SP, "q_sta_output_volt")
yn("q_sta_output_volt", "During the same attempt, does the motor terminal of the solenoid reach 10 V?",
   "Yes, it reaches 10 V", "starter_motor_worn", "No, it stays below 10 V", "starter_solenoid", "starter_solenoid")
yn("q_sta_noise", "Does the starter draw more than 250 A, or grind during the start?",
   "Yes, a high current or a grind", "q_sta_bench", "No, the current is normal and there is no grind",
   "q_sta_battery_volt", "q_sta_bench")
yn("q_sta_bench", "On a bench test, does the removed starter turn slowly or grind?",
   "Yes, it turns slowly or grinds", "starter_motor_worn", "No, it turns correctly", SP, "starter_motor_worn")
yn("q_sta_tap", "Does the starter work after a light tap on its body?",
   "Yes, it works after the tap", "q_sta_bench", "No, a tap has no effect", "q_sta_solenoid_volt", "q_sta_solenoid_volt")

# fuel pump
ENTRY["fuel_pump"] = "q_fp_symptom"
q("q_fp_symptom", "What does the fuel problem look like?", [
    ("no_start", "The engine cranks at normal speed but does not fire", "q_fp_prime"),
    ("runs_poorly", "The engine runs, but it hesitates or loses power under load", "q_fp_pressure_idle"),
], "q_fp_pressure_idle")
yn("q_fp_prime", "When the ignition turns on, is there a two-second hum from the fuel tank?",
   "Yes, the pump hums", "q_fp_pressure_crank", "No, there is no hum", "q_fp_relay", "q_fp_pressure_crank")
yn("q_fp_relay", "With the pump relay bridged, is there 12 V at the pump connector?",
   "Yes, there is 12 V", "q_fp_pump_current", "No, there is no voltage", SP, "q_fp_pump_current")
yn("q_fp_pump_current", "With 12 V at the connector, does the pump stay silent and draw no current?",
   "Yes, the pump does not run", "fuel_pump_failed", "No, the pump runs", SP, "fuel_pump_failed")
q("q_fp_pressure_crank", "What is the fuel rail pressure while the engine cranks?", [
    ("zero", "Zero, or almost zero", "fuel_pump_failed"),
    ("low", "Some pressure, but less than the specification", "q_fp_filter_age"),
    ("normal", "At the specification", SP),
], "q_fp_filter_age")
yn("q_fp_pressure_idle", "Is the fuel rail pressure at the specification at idle?",
   "Yes, at the specification", "q_fp_pressure_load", "No, it is low", "q_fp_filter_age", "q_fp_pressure_load")
q("q_fp_pressure_load", "On a road test at full load, what does the fuel rail pressure do?", [
    ("holds", "It stays at the specification", "injector_clogged"),
    ("drops", "It drops below the specification", "q_fp_filter_age"),
], "q_fp_filter_age")
yn("q_fp_filter_age", "Is the fuel filter change overdue, or is the filter older than 60,000 km?",
   "Yes, the filter change is overdue", "q_fp_filter_swap", "No, the filter is new", "q_fp_volume", "q_fp_filter_swap")
yn("q_fp_filter_swap", "After a new filter is installed, does the pressure hold at full load?",
   "Yes, the pressure holds", "fuel_filter_clogged", "No, the pressure still drops", "fuel_pump_weak", "fuel_filter_clogged")
yn("q_fp_volume", "Does the pump deliver less than the specified volume in 30 s?",
   "Yes, the volume is low", "fuel_pump_weak", "No, the volume is correct", SP, "fuel_pump_weak")

# injectors
ENTRY["injectors"] = "q_inj_symptom"
q("q_inj_symptom", "Which mixture fault does the scan tool or the customer show?", [
    ("one_cylinder", "A misfire on one cylinder, code P0301 to P0304", "q_inj_coil_swap"),
    ("lean", "Lean codes P0171 or P0174, hesitation, or random misfires", "q_inj_pressure_load"),
], "q_inj_pressure_load")
yn("q_inj_coil_swap", "Swap the coil of the misfiring cylinder with a neighbour. Does the misfire code move with the coil?",
   "Yes, the misfire moves with the coil", "ignition_coil",
   "No, the misfire stays on the same cylinder", "q_inj_balance", "q_inj_balance")
yn("q_inj_balance", "Does an injector balance test show one injector far outside the others?",
   "Yes, one injector is far outside", "q_inj_click", "No, all injectors are similar", SP, "q_inj_click")
yn("q_inj_click", "With a stethoscope, is the click of that injector missing or weak?",
   "Yes, the click is missing or weak", "injector_stuck", "No, the click is normal", "q_inj_leak", "q_inj_leak")
yn("q_inj_leak", "In a leak-down test, does that injector drip?",
   "Yes, the injector drips", "injector_stuck", "No, it does not drip", SP, SP)
q("q_inj_pressure_load", "On a road test at full load, what does the fuel rail pressure do?", [
    ("holds", "It stays at the specification", "q_inj_trim"),
    ("drops", "It drops below the specification", "fuel_pump_weak"),
], "q_inj_trim")
q("q_inj_trim", "What is the long-term fuel trim at idle?", [
    ("high", "More than +10 percent", "q_inj_smoke"),
    ("normal", "From -10 to +10 percent", SP),
], "q_inj_smoke")
yn("q_inj_smoke", "Does a smoke test show a leak in the intake?",
   "Yes, there is an intake leak", SP, "No, the intake is tight", "q_inj_flow", "q_inj_flow")
yn("q_inj_flow", "Does a flow test show that the injectors deliver less than 90 percent of their rated flow?",
   "Yes, the flow is low", "injector_clogged", "No, the flow is correct", SP, "injector_clogged")

# ignition
ENTRY["ignition"] = "q_ign_symptom"
q("q_ign_symptom", "What does the ignition problem look like?", [
    ("misfire", "The engine misfires or shakes, or the engine light flashes", "q_ign_one_cyl"),
    ("no_start", "The engine cranks at normal speed but does not fire, or it cuts out when warm", "q_ign_rpm"),
], "q_ign_one_cyl")
yn("q_ign_one_cyl", "Does the scan tool show a misfire on one cylinder only?",
   "Yes, one cylinder only", "q_ign_coil_swap", "No, more than one cylinder, or code P0300", "q_ign_plugs", "q_ign_plugs")
yn("q_ign_coil_swap", "Swap the coil of the misfiring cylinder with a neighbour. Does the misfire code move with the coil?",
   "Yes, the misfire moves with the coil", "q_ign_coil_check",
   "No, the misfire stays on the same cylinder", "q_ign_plug_one", "q_ign_coil_check")
yn("q_ign_coil_check", "Does the coil show a crack or a carbon track, or a secondary resistance out of the specification?",
   "Yes, the coil is damaged or out of the specification", "ignition_coil",
   "No, the coil looks and measures correct", SP, "ignition_coil")
yn("q_ign_plug_one", "Is the spark plug of that cylinder worn, cracked or fouled?",
   "Yes, the plug is worn, cracked or fouled", "spark_plugs_worn", "No, the plug is in good condition",
   "injector_stuck", "injector_stuck")
q("q_ign_plugs", "What condition are the spark plugs in?", [
    ("worn", "Worn electrodes, a gap above the specification, or fouled", "q_ign_plug_swap"),
    ("good", "Good condition", SP),
], "q_ign_plug_swap")
yn("q_ign_plug_swap", "After new plugs are installed, does the misfire stop on a road test?",
   "Yes, the misfire stops", "spark_plugs_worn", "No, the misfire continues", SP, "spark_plugs_worn")
yn("q_ign_rpm", "Does the rpm on the scan tool read zero while the engine cranks?",
   "Yes, the rpm reads zero", "q_ign_code", "No, the rpm reads normal", SP, "q_ign_code")
yn("q_ign_code", "Is code P0335 or P0336 stored?",
   "Yes, P0335 or P0336 is stored", "q_ign_crank_signal", "No, neither code is stored", "q_ign_crank_signal",
   "q_ign_crank_signal")
yn("q_ign_crank_signal", "Is the crank sensor signal missing on an oscilloscope, or its resistance out of the specification?",
   "Yes, the signal is missing or the resistance is wrong", "crank_sensor",
   "No, the signal and the resistance are correct", SP, "crank_sensor")

# cooling fan
ENTRY["cooling_fan"] = "q_fan_when"
q("q_fan_when", "When does the engine overheat?", [
    ("traffic", "In traffic or at idle, and it cools down at speed", "q_fan_runs"),
    ("road", "At a steady speed on the road also", "q_fan_top_hose"),
], "q_fan_runs")
yn("q_fan_top_hose", "With the gauge high, is the top radiator hose cold or only warm?",
   "Yes, the top hose is cold or only warm", "thermostat_stuck_closed",
   "No, the top hose is hot", "q_fan_runs", "q_fan_runs")
yn("q_fan_runs", "Does the radiator fan run when the coolant is above 100 °C, or when the AC is on?",
   "Yes, the fan runs", SP, "No, the fan does not run", "q_fan_fuse", "q_fan_fuse")
yn("q_fan_fuse", "Is the fan fuse blown?",
   "Yes, the fuse is blown", "q_fan_motor_current", "No, the fuse is good", "q_fan_direct", "q_fan_direct")
yn("q_fan_direct", "Does the fan run with 12 V applied directly to the motor?",
   "Yes, the fan runs", "q_fan_relay_click", "No, the fan does not run", "radiator_fan_motor", "q_fan_relay_click")
yn("q_fan_relay_click", "When the ECU commands the fan, does the relay click and give 12 V at its output?",
   "Yes, the relay clicks and gives 12 V", SP, "No, there is no click or no output", "fan_relay", "fan_relay")
yn("q_fan_motor_current", "Is the fan motor stiff to turn by hand, or does it draw more than its rated current?",
   "Yes, the motor is stiff or draws too much current", "radiator_fan_motor",
   "No, the motor turns freely and draws the rated current", SP, "radiator_fan_motor")

# thermostat
ENTRY["thermostat"] = "q_th_symptom"
q("q_th_symptom", "What does the temperature problem look like?", [
    ("overheat", "The engine overheats", "q_th_top_hose"),
    ("cold", "The engine stays cold, the heater is weak, or code P0128 is stored", "q_th_warm_time"),
], "q_th_top_hose")
yn("q_th_top_hose", "With the gauge high, is the top radiator hose cold or only warm?",
   "Yes, the top hose is cold or only warm", "q_th_temp_diff",
   "No, the top hose is hot", "q_th_fan", "q_th_temp_diff")
yn("q_th_fan", "Does the radiator fan run when the coolant is above 100 °C?",
   "Yes, the fan runs", SP, "No, the fan does not run", "radiator_fan_motor", SP)
yn("q_th_temp_diff", "Is the engine side of the thermostat more than 20 °C hotter than the radiator side?",
   "Yes, more than 20 °C hotter", "q_th_bench", "No, the difference is small", SP, "q_th_bench")
yn("q_th_bench", "In a pot of hot water, does the removed thermostat stay closed at its rated temperature?",
   "Yes, it stays closed", "thermostat_stuck_closed", "No, it opens", SP, "thermostat_stuck_closed")
yn("q_th_warm_time", "After 15 minutes of driving, does the coolant temperature stay below 70 °C?",
   "Yes, it stays below 70 °C", "q_th_radiator_warm", "No, it reaches the normal temperature", SP, "q_th_radiator_warm")
yn("q_th_radiator_warm", "Does the top radiator hose get warm within a few minutes of a cold start?",
   "Yes, it gets warm early", "q_th_sensor", "No, it stays cold", SP, "q_th_sensor")
yn("q_th_sensor", "Does the coolant sensor value agree with an infrared reading at the engine?",
   "Yes, the values agree", "thermostat_stuck_open", "No, the sensor reads wrong", SP, "thermostat_stuck_open")

# water pump and coolant circuit
ENTRY["water_pump"] = "q_wp_symptom"
q("q_wp_symptom", "What does the coolant problem look like?", [
    ("coolant_loss", "The coolant level drops, or there is a puddle or a sweet smell", "q_wp_visible"),
    ("smoke", "White smoke from the exhaust, or bubbles in the coolant", "q_wp_combustion"),
    ("overheat", "The engine overheats at speed and the heater blows cold, with no coolant loss", "q_wp_flow"),
], "q_wp_visible")
yn("q_wp_visible", "Does a pressure test show an external leak?",
   "Yes, there is an external leak", "q_wp_leak_place", "No, there is no external leak", "q_wp_combustion",
   "q_wp_combustion")
q("q_wp_leak_place", "Where is the leak?", [
    ("pump", "At the water pump or its weep hole", "q_wp_weep"),
    ("hose", "At a hose or a hose clamp", "q_wp_hose_check"),
    ("other", "At the radiator or at a different place", SP),
], SP)
yn("q_wp_weep", "Is there a coolant trace below the weep hole of the pump?",
   "Yes, there is a trace", "water_pump_leak", "No, there is no trace", SP, "water_pump_leak")
yn("q_wp_hose_check", "Is the hose soft, swollen or cracked at the leak?",
   "Yes, the hose is damaged", "coolant_hose_leak", "No, the hose is in good condition", "q_wp_clamp", "q_wp_clamp")
yn("q_wp_clamp", "Is the hose clamp at the leak loose or corroded?",
   "Yes, the clamp is loose or corroded", "coolant_hose_leak", "No, the clamp is tight", SP, "coolant_hose_leak")
yn("q_wp_combustion", "Does a combustion leak test on the coolant change color?",
   "Yes, the test fluid changes color", "q_wp_leakdown", "No, the color does not change", SP, "q_wp_leakdown")
yn("q_wp_leakdown", "Does a leak-down test show air in the coolant from one cylinder?",
   "Yes, air comes into the coolant", "head_gasket", "No, no air comes into the coolant", SP, "head_gasket")
yn("q_wp_flow", "With the thermostat open, is the top hose hot while the bottom hose stays much cooler?",
   "Yes, a large temperature difference", "q_wp_impeller", "No, the hoses are at a similar temperature", SP,
   "q_wp_impeller")
yn("q_wp_impeller", "With the pump removed, is the impeller eroded, broken or loose on its shaft?",
   "Yes, the impeller is damaged", "water_pump_impeller", "No, the impeller is in good condition", SP,
   "water_pump_impeller")

# brakes
ENTRY["brakes"] = "q_brk_symptom"
q("q_brk_symptom", "What is the main brake complaint?", [
    ("noise", "A squeal or a grind when the driver brakes", "q_brk_pads"),
    ("vibration", "A shake in the pedal or the steering wheel when the driver brakes", "q_brk_runout"),
    ("pull", "The car pulls to one side, or one wheel smells hot", "q_brk_wheel_temp"),
    ("soft_pedal", "The pedal is soft or spongy, or goes down too far", "q_brk_pump"),
], "q_brk_pads")
q("q_brk_pads", "What is the thickness of the pad material?", [
    ("thin", "Less than 3 mm, or the wear indicator touches the disc", "worn_pads"),
    ("ok", "3 mm or more", SP),
], SP)
q("q_brk_runout", "What is the disc run-out?", [
    ("high", "More than 0.05 mm", "q_brk_hub_clean"),
    ("normal", "0.05 mm or less", SP),
], "q_brk_hub_clean")
yn("q_brk_hub_clean", "After the hub face is cleaned, is the run-out still more than 0.05 mm?",
   "Yes, the run-out is still high", "warped_discs", "No, the run-out is now normal", SP, "warped_discs")
yn("q_brk_wheel_temp", "After a short drive, is one wheel much hotter than the others?",
   "Yes, one wheel is much hotter", "q_brk_wheel_spin", "No, the temperatures are similar", SP, "q_brk_wheel_spin")
yn("q_brk_wheel_spin", "With the car raised, does that wheel drag when it is turned by hand?",
   "Yes, the wheel drags", "sticking_caliper", "No, it turns freely", SP, "sticking_caliper")
yn("q_brk_pump", "Does the pedal get firmer when the driver pumps it?",
   "Yes, it gets firmer", "q_brk_bleed", "No, it stays soft", "q_brk_fluid_leak", "q_brk_bleed")
yn("q_brk_bleed", "When a caliper is bled, do air bubbles come out?",
   "Yes, air bubbles come out", "air_in_brakes", "No, only clean fluid comes out", SP, "air_in_brakes")
yn("q_brk_fluid_leak", "Is the brake fluid level low, with a visible leak at a pipe, a hose or a caliper?",
   "Yes, there is a visible leak", SP, "No, there is no visible leak", "q_brk_abs_test", "q_brk_abs_test")
yn("q_brk_abs_test", "Does the pedal sink during an ABS valve test, or is an ABS pump or valve code stored?",
   "Yes, the pedal sinks or a code is stored", "abs_pump_module", "No, the test is normal", SP, "abs_pump_module")

# ABS
ENTRY["abs"] = "q_abs_codes"
q("q_abs_codes", "Which ABS code does the scan tool show?", [
    ("wheel_speed", "A wheel speed sensor code, C0035 to C0050", "q_abs_live"),
    ("pump", "A pump motor or valve code, C0110 or C0121", "q_abs_pump_run"),
], "q_abs_live")
yn("q_abs_live", "On a road test, does the live data show a dropout or an erratic speed from one wheel?",
   "Yes, one wheel drops out or reads erratic", "q_abs_play", "No, all wheel speeds agree", SP, "q_abs_play")
yn("q_abs_play", "With that wheel off the ground, is there play at 12 and 6 o'clock, or a rough feel when it spins?",
   "Yes, there is play or a rough feel", "wheel_bearing_worn",
   "No, the wheel is tight and smooth", "q_abs_sensor", "q_abs_sensor")
yn("q_abs_sensor", "Is the sensor resistance or its signal out of the specification, or is its wire damaged?",
   "Yes, the sensor or its wire is defective", "abs_wheel_sensor", "No, the sensor and its wire are correct", SP,
   "abs_wheel_sensor")
yn("q_abs_pump_run", "Does the ABS pump run during an actuator test?",
   "Yes, the pump runs", "q_abs_valves", "No, the pump does not run", "q_abs_pump_power", "q_abs_valves")
yn("q_abs_pump_power", "Is there 12 V at the pump motor fuse and at the module connector?",
   "Yes, there is 12 V", "abs_pump_module", "No, the supply is missing", SP, "abs_pump_module")
yn("q_abs_valves", "Does a valve test fail on one channel, or does the pedal sink during the test?",
   "Yes, a channel fails or the pedal sinks", "abs_pump_module", "No, all channels pass", SP, "abs_pump_module")

# wheel bearings and drive shafts
ENTRY["wheel_bearings"] = "q_whl_noise"
q("q_whl_noise", "What does the customer notice at the wheels?", [
    ("hum", "A hum or drone that rises with the road speed", "q_whl_load"),
    ("click", "A click or a knock on full lock", "q_whl_cv_test"),
    ("warning", "No noise, but the ABS or traction light is on", "q_whl_play"),
], "q_whl_load")
yn("q_whl_load", "Does the hum change when the car sways in a bend?",
   "Yes, the hum changes in a bend", "q_whl_spin", "No, the hum stays the same", SP, "q_whl_spin")
yn("q_whl_spin", "With the car raised, does one wheel feel rough or make noise when it is turned by hand?",
   "Yes, one wheel is rough or noisy", "wheel_bearing_worn", "No, all wheels turn smoothly", SP,
   "wheel_bearing_worn")
yn("q_whl_play", "With the wheel off the ground, is there play at 12 and 6 o'clock, or a rough feel when it spins?",
   "Yes, there is play or a rough feel", "wheel_bearing_worn",
   "No, the wheel is tight and smooth", "q_whl_sensor", "q_whl_sensor")
yn("q_whl_sensor", "Is the wheel speed sensor resistance or its signal out of the specification?",
   "Yes, the sensor is out of the specification", "abs_wheel_sensor", "No, the sensor is correct", SP, SP)
yn("q_whl_cv_test", "Does the click repeat when the car drives in a tight circle under power?",
   "Yes, it clicks in a tight circle", "q_whl_boot", "No, there is no click in a tight circle", SP, "q_whl_boot")
yn("q_whl_boot", "Is a drive shaft boot split, with grease on the wheel arch?",
   "Yes, a boot is split", "cv_joint_worn", "No, the boots are in good condition", "q_whl_cv_play", "q_whl_cv_play")
yn("q_whl_cv_play", "Is there rotational play at the outer joint of the drive shaft?",
   "Yes, the joint has play", "cv_joint_worn", "No, the joint has no play", SP, "cv_joint_worn")

# CAN bus
ENTRY["can_bus"] = "q_can_symptom"
q("q_can_symptom", "What does the network problem look like?", [
    ("many_lights", "Several warning lights come on at the same time, or the gauges drop to zero", "q_can_codes"),
    ("no_start", "The engine does not start, and the scan tool cannot reach the engine ECU", "q_can_ecu_supply"),
], "q_can_codes")
yn("q_can_codes", "Are lost-communication codes, U0100 to U0155, stored in more than one module?",
   "Yes, in more than one module", "q_can_resistance", "No, in one module or none", SP, "q_can_resistance")
yn("q_can_ecu_supply", "With the ignition on, is the supply voltage at the engine ECU connector more than 11.5 V?",
   "Yes, more than 11.5 V", "q_can_resistance", "No, 11.5 V or less", "ecu_power_supply", "q_can_resistance")
q("q_can_resistance", "With the battery disconnected, what is the resistance between pins 6 and 14 of the OBD socket?", [
    ("r60", "Approximately 60 Ω", "q_can_gateway"),
    ("r120", "Approximately 120 Ω", "q_can_wiring"),
    ("low", "Less than 50 Ω, or a short to ground", "q_can_wiring"),
], "q_can_wiring")
yn("q_can_wiring", "Is there water, corrosion or chafe damage at a CAN connector or in the harness?",
   "Yes, there is damage", "can_wiring_fault", "No, the harness looks good", "q_can_scope", "q_can_scope")
yn("q_can_scope", "Does an oscilloscope show a flat or distorted CAN signal on one section of the harness?",
   "Yes, one section has a bad signal", "can_wiring_fault", "No, the signal is clean", SP, "can_wiring_fault")
yn("q_can_gateway", "Does the gateway module report an internal fault, or does the bus work with a test gateway?",
   "Yes, the gateway is at fault", "can_gateway_fault", "No, the gateway is not at fault", SP, "can_gateway_fault")

# engine ECU
ENTRY["ecu"] = "q_ecu_symptom"
q("q_ecu_symptom", "What does the engine control problem look like?", [
    ("security", "The key or security light flashes, and the engine cranks but does not fire", "q_ecu_immo_code"),
    ("no_comm", "The scan tool cannot reach the engine ECU, or the ECU reports an internal fault", "q_ecu_supply"),
], "q_ecu_supply")
yn("q_ecu_immo_code", "Is an immobiliser code stored, or does the ECU report that it does not recognise the key?",
   "Yes, the ECU does not recognise the key", "q_ecu_antenna", "No, there is no immobiliser code", SP, "q_ecu_antenna")
yn("q_ecu_antenna", "In the live data, does the antenna ring fail to read the key?",
   "Yes, the antenna ring does not read the key", "immobiliser_fault", "No, the antenna ring reads the key", SP,
   "immobiliser_fault")
yn("q_ecu_supply", "With the ignition on, is the ECU supply more than 11.5 V, and the drop on the ECU ground 0.1 V or less?",
   "Yes, the supply and the ground are good", "q_ecu_can_resistance",
   "No, the supply is low or the ground drop is high", "q_ecu_main_relay", "q_ecu_can_resistance")
yn("q_ecu_main_relay", "Is the ECU main relay or an ECU fuse defective?",
   "Yes, the relay or a fuse is defective", "ecu_power_supply", "No, the relay and the fuses are good",
   "q_ecu_supply_wire", "q_ecu_supply_wire")
yn("q_ecu_supply_wire", "Is the voltage drop on the ECU supply wire more than 0.5 V, or on the ground wire more than 0.1 V?",
   "Yes, the drop is too high", "ecu_power_supply", "No, the drops are small", SP, "ecu_power_supply")
yn("q_ecu_can_resistance", "With the battery disconnected, is the resistance between OBD pins 6 and 14 approximately 60 Ω?",
   "Yes, approximately 60 Ω", "q_ecu_internal", "No, 120 Ω or a short", "can_wiring_fault", "q_ecu_internal")
yn("q_ecu_internal", "With good power and a good bus, does the ECU still not respond, or report code P0601 to P0606?",
   "Yes, the ECU does not respond or reports an internal code", "ecu_internal_fault",
   "No, the ECU responds normally", SP, "ecu_internal_fault")

# clutch
ENTRY["clutch"] = "q_clu_symptom"
q("q_clu_symptom", "What does the clutch problem look like?", [
    ("slip", "The engine revs rise but the road speed does not, in a high gear", "q_clu_stall_test"),
    ("pedal", "The pedal is soft or goes to the floor, or the gears grind", "q_clu_fluid"),
    ("noise", "A rattle at idle, or a judder when the car pulls away", "q_clu_rattle"),
], "q_clu_stall_test")
yn("q_clu_stall_test", "In 4th gear at 2000 rpm with the handbrake on, does the engine keep running when the clutch is released?",
   "Yes, the engine keeps running", "q_clu_adjust", "No, the engine stalls", SP, "q_clu_adjust")
yn("q_clu_adjust", "Is the clutch free play, or the self-adjuster, in the specification?",
   "Yes, the adjustment is correct", "clutch_slip", "No, the adjustment is wrong", SP, "clutch_slip")
yn("q_clu_fluid", "Is the fluid in the clutch reservoir low, or is there fluid at the slave cylinder or in the footwell?",
   "Yes, the fluid is low or leaks", "clutch_hydraulic", "No, the fluid level is correct and there is no leak",
   "q_clu_bleed", "q_clu_bleed")
yn("q_clu_bleed", "After the clutch hydraulics are bled, does the pedal stay low?",
   "Yes, the pedal stays low", "clutch_hydraulic", "No, the pedal is now firm", SP, "clutch_hydraulic")
yn("q_clu_rattle", "Does the rattle at idle stop when the clutch pedal is pressed?",
   "Yes, the rattle stops", "q_clu_dmf_play", "No, the rattle continues", "q_clu_judder", "q_clu_judder")
yn("q_clu_judder", "Does the car judder when it pulls away in first gear?",
   "Yes, it judders", "q_clu_dmf_play", "No, it pulls away smoothly", SP, "q_clu_dmf_play")
yn("q_clu_dmf_play", "Is the free rotation or the rock of the flywheel more than the specification?",
   "Yes, more than the specification", "dual_mass_flywheel", "No, within the specification", SP, "dual_mass_flywheel")

# exhaust
ENTRY["exhaust"] = "q_exh_symptom"
q("q_exh_symptom", "What does the exhaust problem look like?", [
    ("noise", "A loud exhaust, a tick at a cold start, or an exhaust smell", "q_exh_smoke_test"),
    ("power", "A loss of power at high speed, or a smell of rotten eggs", "q_exh_backpressure"),
    ("codes", "Code P0420 or an oxygen sensor code, with no other complaint", "q_exh_o2_code"),
], "q_exh_o2_code")
yn("q_exh_smoke_test", "Does a smoke test show a leak in the exhaust before the rear box?",
   "Yes, there is a leak", "exhaust_leak", "No, there is no leak", SP, "exhaust_leak")
yn("q_exh_backpressure", "Is the exhaust back pressure more than 3 psi at 2500 rpm?",
   "Yes, more than 3 psi", "q_exh_cat_temp", "No, 3 psi or less", SP, "q_exh_cat_temp")
yn("q_exh_cat_temp", "With an infrared thermometer, is the converter outlet cooler than its inlet?",
   "Yes, the outlet is cooler", "catalytic_converter_blocked", "No, the outlet is hotter", SP,
   "catalytic_converter_blocked")
yn("q_exh_o2_code", "Is an oxygen sensor code, P0130 to P0141, stored?",
   "Yes, an oxygen sensor code is stored", "q_exh_o2_switch", "No, only P0420 is stored", "q_exh_cat_compare",
   "q_exh_o2_switch")
yn("q_exh_o2_switch", "In the live data, does the upstream oxygen sensor switch slowly or stay flat?",
   "Yes, it switches slowly or stays flat", "q_exh_leak_before", "No, it switches normally", SP, "q_exh_leak_before")
yn("q_exh_leak_before", "Does a smoke test show a leak before the first oxygen sensor?",
   "Yes, there is a leak before the sensor", "exhaust_leak", "No, there is no leak", "o2_sensor_fault",
   "o2_sensor_fault")
yn("q_exh_cat_compare", "Does the downstream oxygen sensor switch at the same rate as the upstream sensor?",
   "Yes, both switch at the same rate", "q_exh_backpressure", "No, the downstream sensor stays steady", SP,
   "q_exh_backpressure")

# ---------------------------------------------------------------- derived data

NEUTRAL = {"not_sure"}


def leaves_below(target, memo={}):
    """Return {diagnosis: shortest number of questions to reach it} from `target`."""
    if target in D:
        return {target: 0}
    if target == SP:
        return {}
    if target in memo:
        return memo[target]
    out: dict[str, int] = {}
    for opt in NODES[target]["options"].values():
        for d, n in leaves_below(opt["next"]).items():
            out[d] = min(out.get(d, 99), n + 1)
    memo[target] = out
    return out


def reachable(entry):
    seen, stack = [], [entry]
    while stack:
        n = stack.pop()
        if n in seen or n not in NODES:
            continue
        seen.append(n)
        stack.extend(o["next"] for o in NODES[n]["options"].values())
    return seen


def component_systems():
    systems = {d: [D[d]["comp"]] for d in D}
    for comp, entry in ENTRY.items():
        for d in leaves_below(entry):
            if comp not in systems[d]:
                systems[d].append(comp)
    return systems


def evidence(nid, candidates):
    node = NODES[nid]
    opts = [o for o in node["options"] if o not in NEUTRAL]
    k = len(opts)
    below = {o: leaves_below(node["options"][o]["next"]) for o in opts}
    table = {o: {} for o in opts}
    for d in candidates:
        routes = {o: below[o][d] for o in opts if d in below[o]}
        if not routes:
            for o in opts:
                table[o][d] = round(min(OFF_TREE, 0.9 / k), 3)
            continue
        best = PREFER.get((nid, d)) or min(routes, key=lambda o: (routes[o], opts.index(o)))
        assert best in routes, (nid, d, best)
        BEST[(nid, d)] = best
        high = STRONG if nid in STRONG_NODES else HIGH
        rest = round((1 - high) / (k - 1), 3)
        for o in opts:
            table[o][d] = high if o == best else rest
    return table


def build():
    systems = component_systems()
    node_comp = {}
    for comp, entry in ENTRY.items():
        for n in reachable(entry):
            assert n not in node_comp, f"{n} is in two components"
            node_comp[n] = comp
    assert set(node_comp) == set(NODES), set(NODES) - set(node_comp)
    for nid, node in NODES.items():
        comp = node_comp[nid]
        candidates = [d for d in D if comp in systems[d]]
        node["evidence"] = evidence(nid, candidates)
    return {
        "systems": {c: {"label": l, "description": s, "entry": ENTRY[c]} for c, (l, s) in COMPONENTS.items()},
        "symptoms": {s: {"label": l, "description": t} for s, (l, t) in SYMPTOMS.items()},
        "diagnoses": {
            d: {"label": v["label"], "description": v["description"], "systems": systems[d],
                "prior": v["prior"], "explains": v["explains"], "causes": v["causes"], "fix": v["fix"]}
            for d, v in D.items()
        },
        "nodes": NODES,
    }


def typical_paths(raw):
    """Return {diagnosis: (component, [(node, option)])}: the typical answers inside the primary component."""
    out = {}
    for d, dd in raw["diagnoses"].items():
        comp = dd["systems"][0]
        nid, path = raw["systems"][comp]["entry"], []
        while nid != d:
            option = BEST[(nid, d)]
            path.append((nid, option))
            nid = raw["nodes"][nid]["options"][option]["next"]
        out[d] = (comp, path)
    return out


if __name__ == "__main__":
    raw = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}: {len(raw['systems'])} components, {len(D)} diagnoses, "
          f"{len(SYMPTOMS)} symptoms, {len(NODES)} nodes")
    if "--paths" in sys.argv:
        print("TYPICAL_PATHS = {")
        for d, (comp, path) in typical_paths(raw).items():
            print(f"    {d!r}: ({comp!r}, {path!r}),")
        print("}")
