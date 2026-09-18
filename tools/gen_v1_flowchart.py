"""Generate data/flowchart.json. Likelihoods are written per diagnosis, then transposed."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "flowchart.json"

systems = {
    "no_start": {
        "label": "No start or hard start",
        "description": "The engine does not start, cranks slowly, only clicks, or needs many attempts to start",
        "entry": "q_ns_key_turn",
    },
    "charge": {
        "label": "Charge and electrical",
        "description": "Battery warning light, a battery that goes flat, dim or flickering lights, or a belt squeal",
        "entry": "q_ch_symptom",
    },
    "runs_badly": {
        "label": "Engine runs badly",
        "description": "The engine starts but misfires, idles rough, stalls, hesitates or lacks power",
        "entry": "q_rb_symptom",
    },
    "cooling": {
        "label": "Cooling",
        "description": "The engine overheats, loses coolant, or blows white smoke with a sweet smell",
        "entry": "q_co_symptom",
    },
    "brakes": {
        "label": "Brakes",
        "description": "Brake noise, a shake when braking, a pull to one side, or a soft or low pedal",
        "entry": "q_br_symptom",
    },
}

D = {}


def diag(did, label, description, systems_, prior, fix):
    D[did] = {"label": label, "description": description, "systems": systems_, "prior": prior, "fix": fix}


diag("flat_battery", "Flat battery",
     "The battery is healthy but has too little charge to turn the starter",
     ["no_start"], 0.12, [
         "Measure the resting voltage across the battery terminals with the engine off.",
         "Connect a smart charger and charge the battery to 12.6 V or more.",
         "Do a load test on the charged battery.",
         "Start the engine and measure the charge voltage at 2000 rpm, 13.8 V to 14.7 V.",
         "Ask the customer about short trips or lights left on, and record the answer.",
     ])
diag("battery_terminals", "Corroded or loose battery terminals",
     "Corrosion or a loose clamp at the battery terminals or the earth strap blocks the current",
     ["no_start", "charge"], 0.05, [
         "Disconnect the negative terminal first, then the positive terminal.",
         "Clean the posts and the clamps with a terminal brush and a baking soda solution.",
         "Examine the cables and the earth strap for corrosion under the insulation.",
         "Replace a clamp or a cable that has corrosion under the insulation.",
         "Connect the positive terminal first, then the negative terminal, and tighten to the torque value.",
         "Apply terminal protection grease.",
         "Do a start test and measure the voltage drop across each connection, 0.2 V maximum.",
     ])
diag("starter_motor", "Starter motor failure",
     "The starter motor or its solenoid does not turn the engine, though the battery supplies full voltage",
     ["no_start"], 0.06, [
         "Disconnect the battery negative terminal.",
         "Remove the starter supply cable and the solenoid trigger wire.",
         "Remove the starter motor mounting bolts and remove the starter motor.",
         "Examine the flywheel ring gear for damaged teeth.",
         "Install the new starter motor and tighten the bolts to the torque value.",
         "Connect the cables and the battery negative terminal.",
         "Do five start tests and listen for a clean engagement.",
     ])
diag("immobiliser_fault", "Immobiliser fault",
     "The immobiliser does not recognise the key, so the engine computer blocks the start",
     ["no_start"], 0.03, [
         "Read the immobiliser fault codes with a diagnostic tool.",
         "Do a start test with the spare key.",
         "Replace the key battery if the key has one.",
         "Examine the antenna ring around the ignition barrel and its connector.",
         "Program the key to the vehicle with the diagnostic tool.",
         "Clear the fault codes and do three start tests.",
     ])
diag("fuel_pump", "Fuel pump failure",
     "The in-tank fuel pump does not supply fuel pressure, so the engine cranks but does not fire",
     ["no_start"], 0.04, [
         "Examine the fuel pump fuse and relay, and replace a defective part.",
         "Connect a fuel pressure gauge to the fuel rail and measure the pressure at ignition on.",
         "Release the fuel pressure and disconnect the battery negative terminal.",
         "Remove the rear seat base or the access cover over the pump.",
         "Replace the fuel pump module and install a new seal.",
         "Connect the battery, turn the ignition on and examine the pump for leaks.",
         "Measure the fuel pressure again and do a start test.",
     ])
diag("crank_sensor", "Crankshaft position sensor failure",
     "The engine computer gets no crankshaft signal, so it gives no spark and no fuel",
     ["no_start"], 0.03, [
         "Read the fault codes with a diagnostic tool.",
         "Examine the sensor connector and the wires for damage and oil.",
         "Measure the sensor resistance or the signal with an oscilloscope while the engine cranks.",
         "Remove the sensor and clean the mounting face.",
         "Install the new sensor with the correct air gap.",
         "Clear the fault codes and do a start test.",
     ])
diag("battery_end_of_life", "Battery at end of life",
     "The battery no longer holds a charge, so it fails a load test even after a full charge",
     ["no_start", "charge"], 0.08, [
         "Charge the battery fully and do a load test to confirm the failure.",
         "Connect a memory saver to the diagnostic socket.",
         "Disconnect the negative terminal, then the positive terminal, and remove the clamp.",
         "Install a new battery with the correct capacity and cold-crank rating.",
         "Connect the positive terminal, then the negative terminal.",
         "Register the new battery with the diagnostic tool if the car has a battery monitor.",
         "Measure the charge voltage at 2000 rpm, 13.8 V to 14.7 V.",
     ])
diag("alternator_failure", "Alternator failure",
     "The alternator or its regulator gives too little or too much charge voltage",
     ["charge"], 0.05, [
         "Measure the charge voltage at 2000 rpm with the lights and the fan on.",
         "Disconnect the battery negative terminal.",
         "Release the belt tension and remove the auxiliary belt from the alternator pulley.",
         "Disconnect the alternator cables and remove the alternator.",
         "Install the new alternator and connect the cables.",
         "Install the belt, then connect the battery negative terminal.",
         "Measure the charge voltage again, 13.8 V to 14.7 V.",
     ])
diag("aux_belt_slip", "Slipping auxiliary belt",
     "The auxiliary belt is worn, glazed or loose, so it slips on the alternator pulley",
     ["charge"], 0.04, [
         "Examine the belt for cracks, glazing and missing ribs.",
         "Examine the tensioner and the idler pulleys for noise and play.",
         "Release the tensioner and remove the belt.",
         "Replace the tensioner if it has play or a weak spring.",
         "Install a new belt on the correct routing.",
         "Run the engine with full electrical load and listen for a squeal.",
     ])
diag("parasitic_drain", "Parasitic drain",
     "A circuit takes current while the car is parked and makes the battery go flat",
     ["charge"], 0.03, [
         "Charge the battery fully.",
         "Lock the car and wait until the control units go to sleep, approximately 30 minutes.",
         "Connect a clamp meter to the battery negative cable and measure the current.",
         "Remove fuses one at a time and find the circuit that stops the drain.",
         "Repair or replace the part on that circuit.",
         "Measure the sleep current again, 50 mA maximum.",
     ])
diag("ignition_coil", "Ignition coil failure",
     "One coil gives a weak or no spark, so one cylinder misfires",
     ["runs_badly"], 0.05, [
         "Read the misfire codes and find the cylinder.",
         "Disconnect the connector of the coil on that cylinder.",
         "Remove the coil.",
         "Examine the spark plug of that cylinder and replace it if it is worn.",
         "Install the new coil and connect it.",
         "Clear the codes and do a road test under load.",
     ])
diag("spark_plugs", "Worn spark plugs",
     "The spark plugs are worn or fouled, so the engine misfires on more than one cylinder",
     ["runs_badly"], 0.06, [
         "Remove the coils or the plug leads.",
         "Remove the spark plugs and examine each one.",
         "Set the gap of the new plugs to the specification.",
         "Install the new plugs and tighten them to the torque value.",
         "Install the coils or the plug leads.",
         "Clear the codes and do a road test.",
     ])
diag("vacuum_leak", "Vacuum leak",
     "Unmetered air enters the intake through a split hose or a gasket, so the engine runs lean",
     ["runs_badly"], 0.04, [
         "Read the fuel trims at idle with a diagnostic tool.",
         "Do a smoke test on the intake and find the leak.",
         "Replace the split hose or the defective gasket.",
         "Examine the brake servo hose and the PCV valve.",
         "Clear the codes and let the engine idle for 10 minutes.",
         "Read the fuel trims again, within 10 percent.",
     ])
diag("maf_sensor", "MAF sensor fault",
     "The mass air flow sensor reads the air flow wrong, so the engine gets the wrong mixture",
     ["runs_badly"], 0.04, [
         "Read the fault codes and the live MAF value at idle.",
         "Examine the air filter and the air intake for dirt and leaks.",
         "Remove the MAF sensor and clean it with MAF sensor cleaner.",
         "Install the sensor and do a road test.",
         "Replace the sensor if the live value stays out of specification.",
         "Clear the codes and reset the fuel trims.",
     ])
diag("fuel_filter", "Clogged fuel filter",
     "A blocked fuel filter lets the fuel pressure fall at high load",
     ["runs_badly"], 0.03, [
         "Release the fuel pressure.",
         "Disconnect the battery negative terminal.",
         "Remove the fuel filter and catch the fuel in a container.",
         "Install the new filter with the flow arrow in the correct direction.",
         "Connect the battery and turn the ignition on to prime the system.",
         "Examine the filter connections for leaks.",
         "Measure the fuel pressure at full load during a road test.",
     ])
diag("egr_valve", "Stuck EGR valve",
     "The EGR valve is stuck open with carbon, so exhaust gas enters the intake at idle",
     ["runs_badly"], 0.03, [
         "Read the EGR fault codes and the valve position value.",
         "Disconnect the EGR valve connector and remove the valve.",
         "Clean the carbon from the valve and the intake port.",
         "Replace the valve if it does not close fully.",
         "Install the valve with a new gasket.",
         "Clear the codes and do the EGR adaptation with the diagnostic tool.",
     ])
diag("thermostat_stuck", "Thermostat stuck closed",
     "The thermostat does not open, so the coolant does not flow through the radiator",
     ["cooling"], 0.05, [
         "Let the engine cool fully.",
         "Drain the coolant into a clean container.",
         "Remove the thermostat housing and the thermostat.",
         "Install the new thermostat with a new seal and the correct orientation.",
         "Fill the system with coolant and bleed the air.",
         "Run the engine to operating temperature and feel the top hose get hot.",
     ])
diag("coolant_hose_leak", "Coolant hose leak",
     "A coolant hose or a hose clip leaks, so the coolant level falls",
     ["cooling"], 0.05, [
         "Let the engine cool fully.",
         "Do a pressure test on the cooling system and find the leak.",
         "Drain the coolant to below the leak.",
         "Replace the hose and the clips.",
         "Fill the system with coolant and bleed the air.",
         "Do a pressure test again for 10 minutes.",
     ])
diag("water_pump", "Water pump failure",
     "The water pump leaks at its seal or its bearing is worn, so the coolant does not circulate",
     ["cooling"], 0.03, [
         "Let the engine cool fully and drain the coolant.",
         "Remove the drive belt or the timing belt that drives the pump.",
         "Remove the water pump.",
         "Clean the mounting face and install the new pump with a new gasket.",
         "Install the belt and set its tension.",
         "Fill the system with coolant and bleed the air.",
         "Run the engine to operating temperature and examine the pump for leaks.",
     ])
diag("radiator_fan", "Radiator fan failure",
     "The radiator fan does not run, so the engine overheats at low speed and in traffic",
     ["cooling"], 0.03, [
         "Examine the fan fuse and the fan relay.",
         "Connect 12 V directly to the fan motor and see if it turns.",
         "Examine the coolant temperature sensor and its signal.",
         "Replace the fan motor, the relay or the sensor that is defective.",
         "Run the engine to operating temperature and make sure that the fan starts.",
     ])
diag("head_gasket", "Head gasket failure",
     "The head gasket leaks between a cylinder and a coolant passage",
     ["cooling", "runs_badly"], 0.02, [
         "Do a combustion leak test on the coolant.",
         "Do a compression test and a leak-down test on each cylinder.",
         "Tell the customer the cost of the repair and get approval before the work.",
         "Remove the cylinder head.",
         "Send the head for a flatness check and a pressure test.",
         "Install the head with a new gasket and new bolts, and tighten to the torque sequence.",
         "Fill the coolant, bleed the air and change the engine oil.",
         "Run the engine and do a combustion leak test again.",
     ])
diag("worn_pads", "Worn brake pads",
     "The pad material is at or below the wear limit",
     ["brakes"], 0.10, [
         "Lift the car and remove the wheels.",
         "Measure the pad thickness and the disc thickness.",
         "Push the caliper piston back and remove the old pads.",
         "Clean the caliper carrier and apply brake grease to the contact points.",
         "Install the new pads and the wear sensor.",
         "Install the wheels and tighten the nuts to the torque value.",
         "Pump the pedal until it is firm, then bed in the pads on a road test.",
     ])
diag("warped_discs", "Warped brake discs",
     "The brake discs have run-out or uneven thickness, so the pedal pulses when braking",
     ["brakes"], 0.05, [
         "Lift the car and remove the wheels.",
         "Measure the disc run-out and the thickness variation.",
         "Remove the calipers and the discs.",
         "Clean the hub face of rust.",
         "Install the new discs and new pads.",
         "Install the calipers and the wheels, and tighten to the torque values.",
         "Bed in the pads on a road test.",
     ])
diag("sticking_caliper", "Sticking brake caliper",
     "A caliper piston or slide pin sticks, so one brake drags and gets hot",
     ["brakes"], 0.03, [
         "Lift the car and find the wheel that drags.",
         "Remove the wheel and the caliper.",
         "Examine the slide pins and the piston seal.",
         "Clean and grease the slide pins, or replace the caliper if the piston sticks.",
         "Replace the pads and the disc if heat damaged them.",
         "Bleed the brakes on that circuit.",
         "Do a road test and measure the wheel temperatures.",
     ])
diag("air_in_brakes", "Air in the brake fluid",
     "Air in the hydraulic system makes the pedal soft and spongy",
     ["brakes"], 0.02, [
         "Examine the brake pipes, the hoses and the calipers for leaks.",
         "Fill the reservoir with new brake fluid of the correct specification.",
         "Bleed each wheel in the sequence of the manufacturer.",
         "Do the ABS bleed procedure with the diagnostic tool if the manual requires it.",
         "Fill the reservoir to the maximum mark.",
         "Make sure that the pedal is firm, then do a road test.",
     ])

N = {}


def node(nid, question, options, lik, default=None):
    """options: {oid: (text, next)}. lik: {diagnosis: {oid: P(oid | diagnosis)}}."""
    evidence = {}
    for did, row in lik.items():
        for oid, p in row.items():
            evidence.setdefault(oid, {})[did] = p
    n = {
        "question": question,
        "options": {oid: {"text": t, "next": nx} for oid, (t, nx) in options.items()},
        "evidence": {oid: evidence[oid] for oid in options if oid in evidence},
    }
    if default is not None:
        n["default_likelihood"] = default
    N[nid] = n


NS = "Not known, or the answer does not say"

# ---------------------------------------------------------------- no start
node("q_ns_key_turn", "What happens when the driver turns the key or presses the start button?", {
    "nothing": ("No sound and no movement at all", "q_ns_dash_lights"),
    "click_only": ("One click or rapid clicks, and the engine does not turn", "q_ns_lights_dim"),
    "slow_crank": ("The engine turns slowly, or turns and slows down", "q_ns_voltage"),
    "normal_crank": ("The engine turns at normal speed but does not fire", "q_ns_immobiliser"),
    "not_sure": (NS, "q_ns_voltage"),
}, {
    "flat_battery": {"nothing": 0.15, "click_only": 0.4, "slow_crank": 0.4, "normal_crank": 0.02},
    "battery_terminals": {"nothing": 0.45, "click_only": 0.35, "slow_crank": 0.15, "normal_crank": 0.02},
    "starter_motor": {"nothing": 0.4, "click_only": 0.5, "slow_crank": 0.05, "normal_crank": 0.02},
    "immobiliser_fault": {"nothing": 0.15, "click_only": 0.01, "slow_crank": 0.02, "normal_crank": 0.8},
    "fuel_pump": {"nothing": 0.01, "click_only": 0.01, "slow_crank": 0.02, "normal_crank": 0.9},
    "crank_sensor": {"nothing": 0.01, "click_only": 0.01, "slow_crank": 0.02, "normal_crank": 0.9},
    "battery_end_of_life": {"nothing": 0.05, "click_only": 0.3, "slow_crank": 0.6, "normal_crank": 0.02},
})
node("q_ns_dash_lights", "Do the dashboard lights come on when the ignition is on?", {
    "yes": ("Yes, the dashboard lights come on at normal brightness", "q_ns_security_light"),
    "no": ("No, the dashboard stays dark or very dim", "q_ns_terminals"),
    "not_sure": (NS, "q_ns_terminals"),
}, {
    "flat_battery": {"yes": 0.15, "no": 0.8},
    "battery_terminals": {"yes": 0.2, "no": 0.75},
    "starter_motor": {"yes": 0.9, "no": 0.05},
    "immobiliser_fault": {"yes": 0.9, "no": 0.05},
    "fuel_pump": {"yes": 0.9, "no": 0.05},
    "crank_sensor": {"yes": 0.9, "no": 0.05},
    "battery_end_of_life": {"yes": 0.2, "no": 0.75},
})
node("q_ns_terminals", "Are the battery terminals or the earth strap corroded, loose or hot to touch?", {
    "yes": ("Yes, there is corrosion, a loose clamp or a hot terminal", "battery_terminals"),
    "no": ("No, the terminals are clean and tight", "q_ns_voltage"),
    "not_sure": (NS, "q_ns_voltage"),
}, {
    "flat_battery": {"yes": 0.05, "no": 0.9},
    "battery_terminals": {"yes": 0.9, "no": 0.08},
    "starter_motor": {"yes": 0.1, "no": 0.85},
    "immobiliser_fault": {"yes": 0.1, "no": 0.85},
    "fuel_pump": {"yes": 0.1, "no": 0.85},
    "crank_sensor": {"yes": 0.1, "no": 0.85},
    "battery_end_of_life": {"yes": 0.1, "no": 0.85},
})
node("q_ns_security_light", "Is the immobiliser, key or security light on or flashing on the dashboard?", {
    "yes": ("Yes, a key or security light stays on or flashes", "immobiliser_fault"),
    "no": ("No, there is no key or security light", "q_ns_starter_voltage"),
    "not_sure": (NS, "specialist"),
}, {
    "flat_battery": {"yes": 0.05, "no": 0.9},
    "battery_terminals": {"yes": 0.05, "no": 0.9},
    "starter_motor": {"yes": 0.03, "no": 0.92},
    "immobiliser_fault": {"yes": 0.9, "no": 0.08},
    "fuel_pump": {"yes": 0.05, "no": 0.9},
    "crank_sensor": {"yes": 0.05, "no": 0.9},
    "battery_end_of_life": {"yes": 0.05, "no": 0.9},
})
node("q_ns_lights_dim", "Do the headlights go dim or out when the key turns to start?", {
    "yes": ("Yes, the headlights go dim or out", "q_ns_voltage"),
    "no": ("No, the headlights stay bright", "q_ns_starter_voltage"),
    "not_sure": (NS, "q_ns_voltage"),
}, {
    "flat_battery": {"yes": 0.9, "no": 0.05},
    "battery_terminals": {"yes": 0.6, "no": 0.35},
    "starter_motor": {"yes": 0.1, "no": 0.85},
    "immobiliser_fault": {"yes": 0.1, "no": 0.85},
    "fuel_pump": {"yes": 0.1, "no": 0.85},
    "crank_sensor": {"yes": 0.1, "no": 0.85},
    "battery_end_of_life": {"yes": 0.9, "no": 0.05},
})
node("q_ns_voltage", "What is the battery voltage at rest, with the engine off?", {
    "below_12_2": ("Less than 12.2 V", "q_ns_load_test"),
    "mid": ("From 12.2 V to 12.4 V", "q_ns_load_test"),
    "above_12_4": ("More than 12.4 V", "q_ns_starter_voltage"),
    "not_sure": (NS, "q_ns_load_test"),
}, {
    "flat_battery": {"below_12_2": 0.75, "mid": 0.2, "above_12_4": 0.04},
    "battery_terminals": {"below_12_2": 0.15, "mid": 0.25, "above_12_4": 0.6},
    "starter_motor": {"below_12_2": 0.1, "mid": 0.2, "above_12_4": 0.7},
    "immobiliser_fault": {"below_12_2": 0.1, "mid": 0.2, "above_12_4": 0.7},
    "fuel_pump": {"below_12_2": 0.1, "mid": 0.2, "above_12_4": 0.7},
    "crank_sensor": {"below_12_2": 0.1, "mid": 0.2, "above_12_4": 0.7},
    "battery_end_of_life": {"below_12_2": 0.55, "mid": 0.35, "above_12_4": 0.08},
})
node("q_ns_load_test", "After a full charge, does the battery pass a load or conductance test?", {
    "yes": ("Yes, the battery passes the test", "flat_battery"),
    "no": ("No, the battery fails the test", "battery_end_of_life"),
    "not_sure": (NS, "specialist"),
}, {
    "flat_battery": {"yes": 0.92, "no": 0.05},
    "battery_terminals": {"yes": 0.85, "no": 0.1},
    "starter_motor": {"yes": 0.85, "no": 0.1},
    "immobiliser_fault": {"yes": 0.85, "no": 0.1},
    "fuel_pump": {"yes": 0.85, "no": 0.1},
    "crank_sensor": {"yes": 0.85, "no": 0.1},
    "battery_end_of_life": {"yes": 0.03, "no": 0.95},
})
node("q_ns_starter_voltage", "Is there more than 10 V at the starter solenoid terminal while the key is at start?", {
    "yes": ("Yes, the voltage at the starter is more than 10 V", "starter_motor"),
    "no": ("No, the voltage falls at the starter but not at the battery", "battery_terminals"),
    "not_sure": (NS, "specialist"),
}, {
    "flat_battery": {"yes": 0.2, "no": 0.75},
    "battery_terminals": {"yes": 0.1, "no": 0.85},
    "starter_motor": {"yes": 0.9, "no": 0.08},
    "immobiliser_fault": {"yes": 0.5, "no": 0.4},
    "fuel_pump": {"yes": 0.9, "no": 0.08},
    "crank_sensor": {"yes": 0.9, "no": 0.08},
    "battery_end_of_life": {"yes": 0.2, "no": 0.75},
})
node("q_ns_immobiliser", "Is the immobiliser, key or security light on or flashing while the engine cranks?", {
    "yes": ("Yes, a key or security light stays on or flashes", "immobiliser_fault"),
    "no": ("No, there is no key or security light", "q_ns_fuel_pump_hum"),
    "not_sure": (NS, "q_ns_fuel_pump_hum"),
}, {
    "flat_battery": {"yes": 0.05, "no": 0.9},
    "battery_terminals": {"yes": 0.05, "no": 0.9},
    "starter_motor": {"yes": 0.05, "no": 0.9},
    "immobiliser_fault": {"yes": 0.9, "no": 0.08},
    "fuel_pump": {"yes": 0.02, "no": 0.95},
    "crank_sensor": {"yes": 0.02, "no": 0.95},
    "battery_end_of_life": {"yes": 0.05, "no": 0.9},
})
node("q_ns_fuel_pump_hum", "Does the fuel pump hum for approximately 2 seconds when the ignition turns on?", {
    "yes": ("Yes, the pump hums at ignition on", "q_ns_rpm_signal"),
    "no": ("No, the pump makes no sound, or the fuel pressure is zero", "fuel_pump"),
    "not_sure": (NS, "q_ns_rpm_signal"),
}, {
    "flat_battery": {"yes": 0.85, "no": 0.1},
    "battery_terminals": {"yes": 0.85, "no": 0.1},
    "starter_motor": {"yes": 0.85, "no": 0.1},
    "immobiliser_fault": {"yes": 0.9, "no": 0.05},
    "fuel_pump": {"yes": 0.08, "no": 0.9},
    "crank_sensor": {"yes": 0.9, "no": 0.05},
    "battery_end_of_life": {"yes": 0.85, "no": 0.1},
})
node("q_ns_rpm_signal", "Does the rev counter needle move while the engine cranks?", {
    "yes": ("Yes, the rev counter shows a few hundred rpm", "specialist"),
    "no": ("No, the rev counter stays at zero", "crank_sensor"),
    "not_sure": (NS, "specialist"),
}, {
    "flat_battery": {"yes": 0.85, "no": 0.1},
    "battery_terminals": {"yes": 0.85, "no": 0.1},
    "starter_motor": {"yes": 0.85, "no": 0.1},
    "immobiliser_fault": {"yes": 0.85, "no": 0.1},
    "fuel_pump": {"yes": 0.85, "no": 0.1},
    "crank_sensor": {"yes": 0.08, "no": 0.9},
    "battery_end_of_life": {"yes": 0.85, "no": 0.1},
})

# ---------------------------------------------------------------- charge
node("q_ch_symptom", "What electrical problem does the driver notice first?", {
    "warning_light": ("The battery or charge warning light comes on while the car drives", "q_ch_running_voltage"),
    "flat_overnight": ("The battery goes flat after the car stands overnight or for a few days", "q_ch_drain"),
    "dim_lights": ("The lights go dim or flicker, most at idle", "q_ch_running_voltage"),
    "squeal": ("A squeal from the engine bay, at start, in the wet or at full steering lock", "q_ch_belt"),
    "not_sure": (NS, "q_ch_running_voltage"),
}, {
    "alternator_failure": {"warning_light": 0.6, "flat_overnight": 0.1, "dim_lights": 0.25, "squeal": 0.04},
    "aux_belt_slip": {"warning_light": 0.25, "flat_overnight": 0.05, "dim_lights": 0.1, "squeal": 0.6},
    "parasitic_drain": {"warning_light": 0.02, "flat_overnight": 0.9, "dim_lights": 0.03, "squeal": 0.02},
    "battery_end_of_life": {"warning_light": 0.05, "flat_overnight": 0.6, "dim_lights": 0.25, "squeal": 0.02},
    "battery_terminals": {"warning_light": 0.2, "flat_overnight": 0.1, "dim_lights": 0.6, "squeal": 0.02},
})
node("q_ch_running_voltage", "What is the battery voltage with the engine at 2000 rpm and the lights on?", {
    "low": ("Less than 13.2 V", "q_ch_belt"),
    "normal": ("From 13.8 V to 14.7 V", "q_ch_battery_test"),
    "high": ("More than 15 V", "alternator_failure"),
    "not_sure": (NS, "q_ch_belt"),
}, {
    "alternator_failure": {"low": 0.7, "normal": 0.05, "high": 0.22},
    "aux_belt_slip": {"low": 0.8, "normal": 0.15, "high": 0.01},
    "parasitic_drain": {"low": 0.05, "normal": 0.9, "high": 0.01},
    "battery_end_of_life": {"low": 0.1, "normal": 0.85, "high": 0.01},
    "battery_terminals": {"low": 0.45, "normal": 0.5, "high": 0.01},
})
node("q_ch_belt", "Is the auxiliary belt glazed, cracked or loose, or does it squeal under load?", {
    "yes": ("Yes, the belt is worn, loose or squeals", "aux_belt_slip"),
    "no": ("No, the belt and its tension are good", "q_ch_terminals"),
    "not_sure": (NS, "q_ch_terminals"),
}, {
    "alternator_failure": {"yes": 0.1, "no": 0.85},
    "aux_belt_slip": {"yes": 0.95, "no": 0.03},
    "parasitic_drain": {"yes": 0.1, "no": 0.85},
    "battery_end_of_life": {"yes": 0.1, "no": 0.85},
    "battery_terminals": {"yes": 0.1, "no": 0.85},
})
node("q_ch_terminals", "Are the battery terminals, the alternator cable or the earth strap corroded or loose?", {
    "yes": ("Yes, a terminal or a cable is corroded or loose", "battery_terminals"),
    "no": ("No, the connections are clean and tight", "alternator_failure"),
    "not_sure": (NS, "specialist"),
}, {
    "alternator_failure": {"yes": 0.08, "no": 0.9},
    "aux_belt_slip": {"yes": 0.1, "no": 0.85},
    "parasitic_drain": {"yes": 0.1, "no": 0.85},
    "battery_end_of_life": {"yes": 0.15, "no": 0.8},
    "battery_terminals": {"yes": 0.92, "no": 0.05},
})
node("q_ch_drain", "What current does the battery supply when the car is locked and asleep, after 30 minutes?", {
    "high": ("More than 50 mA", "parasitic_drain"),
    "normal": ("50 mA or less", "q_ch_battery_test"),
    "not_sure": (NS, "q_ch_battery_test"),
}, {
    "alternator_failure": {"high": 0.05, "normal": 0.9},
    "aux_belt_slip": {"high": 0.05, "normal": 0.9},
    "parasitic_drain": {"high": 0.92, "normal": 0.05},
    "battery_end_of_life": {"high": 0.03, "normal": 0.92},
    "battery_terminals": {"high": 0.05, "normal": 0.9},
})
node("q_ch_battery_test", "After a full charge, does the battery pass a load or conductance test?", {
    "yes": ("Yes, the battery passes the test", "q_ch_terminals"),
    "no": ("No, the battery fails the test", "battery_end_of_life"),
    "not_sure": (NS, "q_ch_terminals"),
}, {
    "alternator_failure": {"yes": 0.8, "no": 0.15},
    "aux_belt_slip": {"yes": 0.8, "no": 0.15},
    "parasitic_drain": {"yes": 0.75, "no": 0.2},
    "battery_end_of_life": {"yes": 0.05, "no": 0.92},
    "battery_terminals": {"yes": 0.85, "no": 0.1},
})

# ---------------------------------------------------------------- runs badly
node("q_rb_symptom", "How does the engine run badly?", {
    "misfire": ("It shakes or stumbles, worse under load, and the engine light can flash", "q_rb_one_cylinder"),
    "rough_idle": ("The idle is rough or hunts, and the engine can stall at idle", "q_rb_idle_hiss"),
    "no_power": ("A flat spot or a loss of power when it accelerates, but a smooth idle", "q_rb_fuel_pressure"),
    "white_smoke": ("White smoke with a sweet smell from the exhaust, and a rough run", "q_rb_coolant_loss"),
    "not_sure": (NS, "q_rb_fuel_pressure"),
}, {
    "ignition_coil": {"misfire": 0.8, "rough_idle": 0.12, "no_power": 0.05, "white_smoke": 0.01},
    "spark_plugs": {"misfire": 0.65, "rough_idle": 0.2, "no_power": 0.12, "white_smoke": 0.01},
    "vacuum_leak": {"misfire": 0.1, "rough_idle": 0.75, "no_power": 0.1, "white_smoke": 0.01},
    "maf_sensor": {"misfire": 0.05, "rough_idle": 0.25, "no_power": 0.65, "white_smoke": 0.01},
    "fuel_filter": {"misfire": 0.05, "rough_idle": 0.05, "no_power": 0.85, "white_smoke": 0.01},
    "egr_valve": {"misfire": 0.05, "rough_idle": 0.7, "no_power": 0.2, "white_smoke": 0.02},
    "head_gasket": {"misfire": 0.2, "rough_idle": 0.05, "no_power": 0.03, "white_smoke": 0.7},
})
node("q_rb_one_cylinder", "Is the misfire on one cylinder only, for example one code from P0301 to P0308?", {
    "yes": ("Yes, one cylinder only", "q_rb_coil_swap"),
    "no": ("No, more than one cylinder, or a random misfire code P0300", "q_rb_plugs"),
    "not_sure": (NS, "q_rb_plugs"),
}, {
    "ignition_coil": {"yes": 0.9, "no": 0.08},
    "spark_plugs": {"yes": 0.25, "no": 0.7},
    "vacuum_leak": {"yes": 0.1, "no": 0.85},
    "maf_sensor": {"yes": 0.05, "no": 0.9},
    "fuel_filter": {"yes": 0.05, "no": 0.9},
    "egr_valve": {"yes": 0.1, "no": 0.85},
    "head_gasket": {"yes": 0.6, "no": 0.35},
})
node("q_rb_coil_swap", "When the coil of the bad cylinder goes on a different cylinder, does the misfire move with it?", {
    "yes": ("Yes, the misfire moves with the coil", "ignition_coil"),
    "no": ("No, the misfire stays on the same cylinder", "q_rb_plugs"),
    "not_sure": (NS, "q_rb_plugs"),
}, {
    "ignition_coil": {"yes": 0.9, "no": 0.08},
    "spark_plugs": {"yes": 0.05, "no": 0.9},
    "vacuum_leak": {"yes": 0.05, "no": 0.9},
    "maf_sensor": {"yes": 0.05, "no": 0.9},
    "fuel_filter": {"yes": 0.05, "no": 0.9},
    "egr_valve": {"yes": 0.05, "no": 0.9},
    "head_gasket": {"yes": 0.05, "no": 0.9},
})
node("q_rb_plugs", "What condition are the spark plugs in?", {
    "worn": ("Worn or fouled, a large gap, or past the service interval", "spark_plugs"),
    "good": ("Good, clean and with the gap in specification", "q_rb_coolant_loss"),
    "not_sure": (NS, "specialist"),
}, {
    "ignition_coil": {"worn": 0.15, "good": 0.8},
    "spark_plugs": {"worn": 0.92, "good": 0.05},
    "vacuum_leak": {"worn": 0.15, "good": 0.8},
    "maf_sensor": {"worn": 0.15, "good": 0.8},
    "fuel_filter": {"worn": 0.15, "good": 0.8},
    "egr_valve": {"worn": 0.15, "good": 0.8},
    "head_gasket": {"worn": 0.2, "good": 0.75},
})
node("q_rb_coolant_loss", "Does the coolant level fall with no external leak, or is the spark plug of one cylinder steam-clean?", {
    "yes": ("Yes, coolant goes missing with no leak, or one plug is steam-clean", "head_gasket"),
    "no": ("No, the coolant level stays constant", "specialist"),
    "not_sure": (NS, "specialist"),
}, {
    "ignition_coil": {"yes": 0.05, "no": 0.9},
    "spark_plugs": {"yes": 0.05, "no": 0.9},
    "vacuum_leak": {"yes": 0.05, "no": 0.9},
    "maf_sensor": {"yes": 0.05, "no": 0.9},
    "fuel_filter": {"yes": 0.05, "no": 0.9},
    "egr_valve": {"yes": 0.05, "no": 0.9},
    "head_gasket": {"yes": 0.9, "no": 0.08},
})
node("q_rb_idle_hiss", "Is there a hiss at idle, or does the idle change when carb cleaner is sprayed near the intake?", {
    "yes": ("Yes, a hiss, or the idle changes with the spray, or a smoke test shows a leak", "vacuum_leak"),
    "no": ("No hiss and no change", "q_rb_egr"),
    "not_sure": (NS, "q_rb_egr"),
}, {
    "ignition_coil": {"yes": 0.03, "no": 0.92},
    "spark_plugs": {"yes": 0.03, "no": 0.92},
    "vacuum_leak": {"yes": 0.9, "no": 0.08},
    "maf_sensor": {"yes": 0.05, "no": 0.9},
    "fuel_filter": {"yes": 0.05, "no": 0.9},
    "egr_valve": {"yes": 0.05, "no": 0.9},
    "head_gasket": {"yes": 0.05, "no": 0.9},
})
node("q_rb_egr", "Is the EGR valve stuck open or heavy with carbon, or is an EGR code from P0400 to P0409 stored?", {
    "yes": ("Yes, the EGR valve sticks, has heavy carbon, or has a code", "egr_valve"),
    "no": ("No, the EGR valve moves freely and has no code", "q_rb_maf"),
    "not_sure": (NS, "q_rb_maf"),
}, {
    "ignition_coil": {"yes": 0.03, "no": 0.92},
    "spark_plugs": {"yes": 0.03, "no": 0.92},
    "vacuum_leak": {"yes": 0.08, "no": 0.9},
    "maf_sensor": {"yes": 0.05, "no": 0.9},
    "fuel_filter": {"yes": 0.05, "no": 0.9},
    "egr_valve": {"yes": 0.9, "no": 0.08},
    "head_gasket": {"yes": 0.05, "no": 0.9},
})
node("q_rb_fuel_pressure", "What does the fuel pressure do at full load?", {
    "drops": ("It falls below the specification", "q_rb_filter_age"),
    "holds": ("It stays in the specification", "q_rb_maf"),
    "not_sure": (NS, "q_rb_maf"),
}, {
    "ignition_coil": {"drops": 0.05, "holds": 0.9},
    "spark_plugs": {"drops": 0.05, "holds": 0.9},
    "vacuum_leak": {"drops": 0.05, "holds": 0.9},
    "maf_sensor": {"drops": 0.05, "holds": 0.9},
    "fuel_filter": {"drops": 0.9, "holds": 0.08},
    "egr_valve": {"drops": 0.05, "holds": 0.9},
    "head_gasket": {"drops": 0.05, "holds": 0.9},
})
node("q_rb_filter_age", "When did the fuel filter last get replaced?", {
    "overdue": ("Never, not in the records, or more than 60,000 km ago", "fuel_filter"),
    "recent": ("Less than 60,000 km ago", "specialist"),
    "not_sure": (NS, "specialist"),
}, {
    "ignition_coil": {"overdue": 0.4, "recent": 0.5},
    "spark_plugs": {"overdue": 0.4, "recent": 0.5},
    "vacuum_leak": {"overdue": 0.4, "recent": 0.5},
    "maf_sensor": {"overdue": 0.4, "recent": 0.5},
    "fuel_filter": {"overdue": 0.85, "recent": 0.1},
    "egr_valve": {"overdue": 0.4, "recent": 0.5},
    "head_gasket": {"overdue": 0.4, "recent": 0.5},
})
node("q_rb_maf", "Does the engine run better with the MAF sensor unplugged, or is a code from P0100 to P0104 stored?", {
    "yes": ("Yes, it runs better unplugged, or there is a MAF code", "maf_sensor"),
    "no": ("No change and no MAF code", "specialist"),
    "not_sure": (NS, "specialist"),
}, {
    "ignition_coil": {"yes": 0.05, "no": 0.9},
    "spark_plugs": {"yes": 0.05, "no": 0.9},
    "vacuum_leak": {"yes": 0.15, "no": 0.8},
    "maf_sensor": {"yes": 0.9, "no": 0.08},
    "fuel_filter": {"yes": 0.05, "no": 0.9},
    "egr_valve": {"yes": 0.1, "no": 0.85},
    "head_gasket": {"yes": 0.05, "no": 0.9},
})

# ---------------------------------------------------------------- cooling
node("q_co_symptom", "What cooling problem does the driver notice first?", {
    "overheat_road": ("The temperature gauge climbs on the open road or soon after start", "q_co_top_hose"),
    "overheat_idle": ("The temperature climbs in traffic or at idle, and falls at speed", "q_co_fan"),
    "coolant_loss": ("The coolant level falls, a warning shows, or there is a puddle or a sweet smell", "q_co_visible_leak"),
    "white_smoke": ("White sweet smoke from the exhaust, or bubbles in the expansion tank", "q_co_combustion_test"),
    "not_sure": (NS, "q_co_visible_leak"),
}, {
    "thermostat_stuck": {"overheat_road": 0.85, "overheat_idle": 0.08, "coolant_loss": 0.03, "white_smoke": 0.02},
    "coolant_hose_leak": {"overheat_road": 0.15, "overheat_idle": 0.05, "coolant_loss": 0.75, "white_smoke": 0.02},
    "water_pump": {"overheat_road": 0.35, "overheat_idle": 0.1, "coolant_loss": 0.5, "white_smoke": 0.02},
    "radiator_fan": {"overheat_road": 0.05, "overheat_idle": 0.9, "coolant_loss": 0.02, "white_smoke": 0.01},
    "head_gasket": {"overheat_road": 0.2, "overheat_idle": 0.05, "coolant_loss": 0.25, "white_smoke": 0.5},
})
node("q_co_top_hose", "With the engine hot, is the top radiator hose hot too?", {
    "yes": ("Yes, the top hose is too hot to hold", "q_co_pump"),
    "no": ("No, the top hose stays cool or only warm", "thermostat_stuck"),
    "not_sure": (NS, "q_co_pump"),
}, {
    "thermostat_stuck": {"yes": 0.05, "no": 0.92},
    "coolant_hose_leak": {"yes": 0.85, "no": 0.1},
    "water_pump": {"yes": 0.75, "no": 0.2},
    "radiator_fan": {"yes": 0.9, "no": 0.05},
    "head_gasket": {"yes": 0.85, "no": 0.1},
})
node("q_co_pump", "Is there a whine or a grind from the water pump, play in its pulley, or coolant at its weep hole?", {
    "yes": ("Yes, noise, play or a wet weep hole", "water_pump"),
    "no": ("No, the pump is quiet and dry", "q_co_combustion_test"),
    "not_sure": (NS, "q_co_combustion_test"),
}, {
    "thermostat_stuck": {"yes": 0.05, "no": 0.9},
    "coolant_hose_leak": {"yes": 0.05, "no": 0.9},
    "water_pump": {"yes": 0.9, "no": 0.08},
    "radiator_fan": {"yes": 0.05, "no": 0.9},
    "head_gasket": {"yes": 0.05, "no": 0.9},
})
node("q_co_fan", "Does the radiator fan run when the engine is hot, or when the air conditioning is on?", {
    "yes": ("Yes, the fan runs", "q_co_pump"),
    "no": ("No, the fan does not run", "radiator_fan"),
    "not_sure": (NS, "q_co_pump"),
}, {
    "thermostat_stuck": {"yes": 0.9, "no": 0.05},
    "coolant_hose_leak": {"yes": 0.9, "no": 0.05},
    "water_pump": {"yes": 0.9, "no": 0.05},
    "radiator_fan": {"yes": 0.05, "no": 0.92},
    "head_gasket": {"yes": 0.9, "no": 0.05},
})
node("q_co_visible_leak", "Does a pressure test show a visible coolant leak, such as a wet hose, a crust at a clip, or a drip?", {
    "yes": ("Yes, a visible leak", "q_co_leak_place"),
    "no": ("No visible leak, the system holds pressure outside", "q_co_combustion_test"),
    "not_sure": (NS, "q_co_combustion_test"),
}, {
    "thermostat_stuck": {"yes": 0.1, "no": 0.85},
    "coolant_hose_leak": {"yes": 0.92, "no": 0.05},
    "water_pump": {"yes": 0.7, "no": 0.25},
    "radiator_fan": {"yes": 0.05, "no": 0.9},
    "head_gasket": {"yes": 0.05, "no": 0.9},
})
node("q_co_leak_place", "Where is the coolant leak?", {
    "hose": ("At a hose or a hose clip", "coolant_hose_leak"),
    "pump": ("At the water pump or its weep hole", "water_pump"),
    "other": ("At the radiator, the heater matrix or a different place", "specialist"),
    "not_sure": (NS, "specialist"),
}, {
    "thermostat_stuck": {"hose": 0.3, "pump": 0.2, "other": 0.4},
    "coolant_hose_leak": {"hose": 0.92, "pump": 0.02, "other": 0.04},
    "water_pump": {"hose": 0.05, "pump": 0.9, "other": 0.03},
    "radiator_fan": {"hose": 0.3, "pump": 0.2, "other": 0.4},
    "head_gasket": {"hose": 0.2, "pump": 0.1, "other": 0.6},
})
node("q_co_combustion_test", "Does a combustion leak test (block tester) show exhaust gas in the coolant?", {
    "yes": ("Yes, the test fluid changes color", "head_gasket"),
    "no": ("No, the test fluid does not change", "specialist"),
    "not_sure": (NS, "specialist"),
}, {
    "thermostat_stuck": {"yes": 0.05, "no": 0.9},
    "coolant_hose_leak": {"yes": 0.05, "no": 0.9},
    "water_pump": {"yes": 0.05, "no": 0.9},
    "radiator_fan": {"yes": 0.05, "no": 0.9},
    "head_gasket": {"yes": 0.92, "no": 0.05},
})

# ---------------------------------------------------------------- brakes
node("q_br_symptom", "What is the main brake complaint?", {
    "noise": ("A squeal, a squeak or a grind when the car brakes", "q_br_pads"),
    "vibration": ("The pedal or the steering wheel shakes when the car brakes", "q_br_runout"),
    "pull": ("The car pulls to one side, or one wheel smells hot", "q_br_wheel_temp"),
    "soft_pedal": ("The pedal feels soft or spongy, or goes low", "q_br_pedal_pump"),
    "not_sure": (NS, "q_br_pads"),
}, {
    "worn_pads": {"noise": 0.8, "vibration": 0.08, "pull": 0.05, "soft_pedal": 0.03},
    "warped_discs": {"noise": 0.1, "vibration": 0.8, "pull": 0.05, "soft_pedal": 0.02},
    "sticking_caliper": {"noise": 0.15, "vibration": 0.1, "pull": 0.7, "soft_pedal": 0.03},
    "air_in_brakes": {"noise": 0.02, "vibration": 0.02, "pull": 0.05, "soft_pedal": 0.9},
})
node("q_br_pads", "How thick is the pad material on the worst pad?", {
    "thin": ("3 mm or less, or the wear indicator touches the disc", "worn_pads"),
    "ok": ("More than 3 mm", "q_br_runout"),
    "not_sure": (NS, "q_br_runout"),
}, {
    "worn_pads": {"thin": 0.92, "ok": 0.05},
    "warped_discs": {"thin": 0.25, "ok": 0.7},
    "sticking_caliper": {"thin": 0.4, "ok": 0.55},
    "air_in_brakes": {"thin": 0.15, "ok": 0.8},
})
node("q_br_runout", "What is the disc run-out, measured with a dial gauge at the hub?", {
    "high": ("More than 0.05 mm, or the disc thickness varies", "warped_discs"),
    "ok": ("0.05 mm or less, and the thickness is even", "q_br_wheel_temp"),
    "not_sure": (NS, "q_br_wheel_temp"),
}, {
    "worn_pads": {"high": 0.1, "ok": 0.85},
    "warped_discs": {"high": 0.92, "ok": 0.05},
    "sticking_caliper": {"high": 0.25, "ok": 0.7},
    "air_in_brakes": {"high": 0.05, "ok": 0.9},
})
node("q_br_wheel_temp", "After a drive, is one wheel much hotter than the others, or does one wheel drag when turned by hand?", {
    "yes": ("Yes, one wheel is hot or drags", "sticking_caliper"),
    "no": ("No, the wheels are at a similar temperature and turn freely", "q_br_pedal_pump"),
    "not_sure": (NS, "q_br_pedal_pump"),
}, {
    "worn_pads": {"yes": 0.08, "no": 0.9},
    "warped_discs": {"yes": 0.1, "no": 0.85},
    "sticking_caliper": {"yes": 0.92, "no": 0.05},
    "air_in_brakes": {"yes": 0.05, "no": 0.9},
})
node("q_br_pedal_pump", "Does the pedal get firmer when it is pumped several times?", {
    "yes": ("Yes, the pedal gets firmer with each pump", "air_in_brakes"),
    "no": ("No, the pedal stays the same, or sinks slowly to the floor", "specialist"),
    "not_sure": (NS, "specialist"),
}, {
    "worn_pads": {"yes": 0.1, "no": 0.85},
    "warped_discs": {"yes": 0.1, "no": 0.85},
    "sticking_caliper": {"yes": 0.1, "no": 0.85},
    "air_in_brakes": {"yes": 0.9, "no": 0.08},
})

raw = {"systems": systems, "diagnoses": D, "nodes": N}
OUT.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
print(len(systems), len(D), len(N))
