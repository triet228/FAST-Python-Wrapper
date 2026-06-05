# main.py
import os
import re
from shutil import copyfile
from pathlib import Path

from wrapper import FastWrapper, matlab_expr

PROJECT_ROOT = Path(__file__).resolve().parent


def load_env_file():
    env_path = PROJECT_ROOT / ".env"
    example_env_path = PROJECT_ROOT / ".env.example"

    if not env_path.exists():
        if example_env_path.exists():
            copyfile(example_env_path, env_path)
        else:
            return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def required_env_path(name):
    value = os.environ.get(name, "").strip()

    if not value or r"\path\to\\" in value or r"\path\to" in value:
        raise RuntimeError(
            f"{name} is required. Edit .env and set {name} for your machine."
        )

    return value


load_env_file()

# Local FAST checkout. This repo does not vendor FAST; the wrapper adds this
# folder and all subfolders to MATLAB's path before calling Main.m.
FAST_PATH = required_env_path("FAST_PATH")

# FAST uses NaN as a meaningful "leave this unspecified" marker in many spec
# fields. Keep one shared name so input blocks read like the MATLAB examples.
nan = float("nan")

# Short alias for MATLAB expressions. Anything wrapped in m("...") is evaluated
# inside MATLAB instead of being treated as a Python string literal.
m = matlab_expr


# =============================================================================
# AIRCRAFT
# =============================================================================
# Edit this block for the aircraft-level FAST input structure.
#
# Notes:
# - Use plain Python numbers and strings for fixed values.
# - Use nan when a FAST field should be left for FAST preprocessing/regression.
# - Use m("...") when the value should be evaluated by MATLAB, such as
#   UnitConversionPkg calls or EngineModelPkg references.
# - Set Specs -> Propulsion -> PropArch to a FAST architecture code:
#   "C", "E", "PHE", "SHE", "TE", "PE", or "O".
# - When PropArch is "O", the graph-based propulsion block later in this file
#   is attached automatically as PropArchGraph.
AIRCRAFT = {
    "Specs": {
        "TLAR": {
            # Top-level aircraft requirements. FAST uses Class to select
            # propulsion/aero logic, so spelling must match FAST expectations.
            "EIS": 2005,
            "Class": "Turbofan",
            "MaxPax": 78,
        },
        "Aero": {
            # Lift-to-drag values and correction factors are supplied directly
            # here. Unit conversions are unnecessary because L/D is unitless.
            "L_D": {
                "ClbCF": 1.002,
                "CrsCF": 1.000,
                "Clb": 10.9773 * 1.002,
                "Crs": 15.2000 * 1.000,
                "Des": 10.9773 * 1.002,
            },
            "W_S": {
                # MATLAB performs the unit conversion so the expression can use
                # FAST's UnitConversionPkg exactly like a native FAST spec file.
                "SLS": m(
                    'UnitConversionPkg.ConvMass(109.25, "lbm", "kg") / '
                    '(UnitConversionPkg.ConvLength(1, "ft", "m")) ^ 2'
                ),
            },
        },
        "Battery": {
            # These names are case-sensitive MATLAB struct fields used by
            # BatteryPkg.Discharging and BatteryPkg.Charging.
            "NomVolCell": 3.6,
            "MaxExtVolCell": 4.0880,
            "CapCell": 3,
            "IntResist": 0.0199,
            "ExpVol": 0.0986,
            "ExpCap": 30,
            "MinSOC": 20,
            "BegSOC": 100,
            "MaxAllowCRate": 5,
            "Charging": 500 * 1000,
        },
        "Performance": {
            "Vels": {
                # Takeoff is given in knots and converted to m/s. Cruise remains
                # a Mach number because the corresponding Type fields use Mach.
                "Tko": m('UnitConversionPkg.ConvVel(135, "kts", "m/s")'),
                "Crs": 0.78,
            },
            "Alts": {
                "Tko": 0,
                "Crs": m('UnitConversionPkg.ConvLength(35000, "ft", "m")'),
            },
            "Range": m('UnitConversionPkg.ConvLength(2150, "naut mi", "m")'),
            "RCMax": m('UnitConversionPkg.ConvVel(2250, "ft/min", "m/s")'),
        },
        "Weight": {
            # MTOW and Fuel are the ERJ175LR baseline values converted from lbm.
            # EG, EM, and Batt are sizing variables for electrified components.
            "MTOW": m('UnitConversionPkg.ConvMass(85517, "lbm", "kg")'),
            "EG": nan,
            "EM": 0,
            "Fuel": m('UnitConversionPkg.ConvMass(20785, "lbm", "kg")'),
            "Batt": 0,
            "WairfCF": 1.018,
        },
        "Propulsion": {
            "MDotCF": 1.029,
            # "O" tells FAST to use the custom graph in GRAPH_BASED_PROPULSION.
            # Change this to "C", "E", "PHE", etc. to use FAST's built-in
            # CreatePropArch definitions instead.
            "PropArch": "O",
            "Engine": m("EngineModelPkg.EngineSpecsPkg.CF34_8E5"),
            "NumEngines": 2,
            "T_W": {
                "SLS": 0.3393,
            },
            "Thrust": {
                "SLS": m('UnitConversionPkg.ConvForce(2 * 14510, "lbf", "N")'),
            },
            "Eta": {
                "Prop": 0.8,
            },
        },
        "Power": {
            "SpecEnergy": {
                # Fuel is in kWh/kg-equivalent for FAST's energy accounting.
                # Battery specific energy drives battery mass when battery power
                # is used by the selected architecture.
                "Fuel": 12,
                "Batt": 0.25,
            },
            "Eta": {
                "EM": 0.96,
                "EG": nan,
            },
            "P_W": {
                "SLS": nan,
                "EM": 10,
                "EG": nan,
            },
            "LamUps": {
                # Lambda schedules control upstream power split behavior in the
                # graph function handles. Segment names match FAST mission phases.
                "SLS": 1,
                "Tko": 1,
                "Clb": 1,
                "Crs": 0,
                "Des": 0,
                "Lnd": 0,
            },
            "LamDwn": {
                # Downstream lambda values describe how demand is allocated back
                # through the propulsion graph during each phase.
                "SLS": 0.1,
                "Tko": 0.1,
                "Clb": 0.01,
                "Crs": 0,
                "Des": 0,
                "Lnd": 0,
            },
            "Battery": {
                # Detailed battery model cell configuration. NaN would ask FAST
                # to infer or ignore these depending on architecture and settings.
                "ParCells": 100,
                "SerCells": 62,
                "BegSOC": 100,
            },
        },
    },
    "Settings": {
        # NaN segment point counts let FAST use its own default discretization.
        "TkoPoints": nan,
        "ClbPoints": nan,
        "CrsPoints": nan,
        "DesPoints": nan,
        "OEW": {
            # Outer empty-weight sizing loop controls.
            "MaxIter": 50,
            "Tol": 0.001,
        },
        "Analysis": {
            # Type = 1 runs the sizing analysis used by this smoke-test example.
            "MaxIter": 30,
            "Type": 1,
        },
        # Plotting/Table/PrintOut mirror FAST settings. PrintOut = 1 keeps the
        # MATLAB iteration log visible in the Python result.
        "Degradation": 0,
        "PowerOpt": 0,
        "PowerStrat": -1,
        "ConSOC": 1,
        "Plotting": 0,
        "Table": 0,
        "PrintOut": 1,
    },
}


# =============================================================================
# MISSION
# =============================================================================
# Edit this block for the mission profile that FAST attaches to Aircraft.
#
# The mission arrays are aligned by row. For each segment index, Segs, ID,
# AltBeg, AltEnd, VelBeg, VelEnd, TypeBeg, TypeEnd, and ClbRate describe the
# same mission segment. Target.Valu and Target.Type describe the distance/time
# goals for each mission ID.
MISSION = {
    "Target": {
        # Mission ID 1 flies the aircraft design range, ID 2 is a 100 nmi
        # diversion, and ID 3 is a 45 minute loiter/time target.
        "Valu": [
            m("Aircraft.Specs.Performance.Range"),
            m('UnitConversionPkg.ConvLength(100, "naut mi", "m")'),
            45,
        ],
        "Type": ["Dist", "Dist", "Time"],
    },
    "Segs": [
        # Each entry below is one mission segment. All other arrays in this
        # mission block must have this same length and order.
        "Takeoff", "Climb", "Climb", "Climb",
        "Cruise", "Descent", "Descent", "Descent",
        "Climb", "Climb", "Climb", "Cruise",
        "Cruise", "Descent", "Descent", "Descent", "Landing",
    ],
    "ID": [
        # IDs group segments into the target definitions above.
        1, 1, 1, 1,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3, 3,
    ],
    "AltBeg": [
        # Beginning altitude for each segment. Expressions can reference the
        # Aircraft struct because FAST evaluates the mission profile after the
        # aircraft spec has been created.
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(1500, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Tko"),
    ],
    "AltEnd": [
        # Ending altitude for each segment, aligned with Segs by index.
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(1500, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m("Aircraft.Specs.Performance.Alts.Tko"),
    ],
    "VelBeg": [
        # Beginning speed for each segment. TypeBeg says whether the numeric
        # value is TAS, EAS, or Mach.
        0,
        m("Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
    ],
    "VelEnd": [
        # Ending speed for each segment. TypeEnd supplies the matching speed
        # interpretation for every value.
        m("Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
        0,
    ],
    "TypeBeg": [
        # FAST accepts speed type labels such as TAS, EAS, and Mach.
        "TAS", "TAS", "EAS", "EAS",
        "Mach", "Mach", "EAS", "EAS",
        "TAS", "EAS", "EAS", "TAS",
        "TAS", "TAS", "EAS", "EAS", "TAS",
    ],
    "TypeEnd": [
        # Keep this list aligned with VelEnd. A mismatch can produce confusing
        # mission analysis errors in MATLAB.
        "TAS", "EAS", "EAS", "Mach",
        "Mach", "EAS", "EAS", "TAS",
        "EAS", "EAS", "TAS", "TAS",
        "TAS", "EAS", "EAS", "TAS", "TAS",
    ],
    "ClbRate": [
        # NaN leaves climb/descent rates to FAST where not explicitly prescribed.
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan, nan,
    ],
}


# =============================================================================
# PROPULSION GRAPH
# =============================================================================
# Edit this block only when AIRCRAFT["Specs"]["Propulsion"]["PropArch"] is "O".
#
# FAST's graph-based propulsion architecture uses:
# - Arch: adjacency matrix for source, transmitter, and sink connections.
# - OperUps / OperDwn: MATLAB function handles that define upstream/downstream
#   power split matrices. The lambda argument is supplied by FAST during the
#   power-flow analysis.
# - EtaUps / EtaDwn: efficiency matrices for upstream/downstream propagation.
# - SrcType: source component types, where FAST uses 1 for fuel and 0 for
#   battery in CreatePropArch.
# - TrnType: transmitter component types, where FAST uses 1 for engine,
#   0 for electric motor, 2 for propeller/fan, and 3 for electric generator.
FAN_EFFICIENCY = 0.99
EM_EFFICIENCY = 0.96
GRAPH_BASED_PROPULSION = {
    "Arch": [
        # Component order is:
        # 0 fuel source, 1 battery source,
        # 2-3 gas-turbine engines, 4-5 electric motors,
        # 6-7 fans, 8 sink.
        # A 1 at row i, column j means component i can power component j.
        [0, 0, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
    "OperUps": m(
        # Upstream operation maps available power from sources toward the sink.
        # lam is supplied by FAST from Settings/Power schedules for each phase.
        "@(lam) ["
        "0, 0, 1/2, 1/2, 0, 0, 0, 0, 0; "
        "0, 0, 0, 0, 1/2, 1/2, 0, 0, 0; "
        "0, 0, 0, 0, 0, 0, 1, 0, 0; "
        "0, 0, 0, 0, 0, 0, 0, 1, 0; "
        "0, 0, 0, 0, 0, 0, lam, 0, 0; "
        "0, 0, 0, 0, 0, 0, 0, lam, 0; "
        "0, 0, 0, 0, 0, 0, 0, 0, 1; "
        "0, 0, 0, 0, 0, 0, 0, 0, 1; "
        "0, 0, 0, 0, 0, 0, 0, 0, 0]"
    ),
    "OperDwn": m(
        # Downstream operation maps required sink power back toward sources.
        # The lam terms split fan demand between engine and electric motor paths.
        "@(lam) ["
        "0, 0, 0, 0, 0, 0, 0, 0, 0; "
        "0, 0, 0, 0, 0, 0, 0, 0, 0; "
        "1, 0, 0, 0, 0, 0, 0, 0, 0; "
        "1, 0, 0, 0, 0, 0, 0, 0, 0; "
        "0, 1, 0, 0, 0, 0, 0, 0, 0; "
        "0, 1, 0, 0, 0, 0, 0, 0, 0; "
        "0, 0, 1-lam, 0, lam, 0, 0, 0, 0; "
        "0, 0, 0, 1-lam, 0, lam, 0, 0, 0; "
        "0, 0, 0, 0, 0, 0, 1/2, 1/2, 0]"
    ),
    "EtaUps": [
        # Eta matrices apply component efficiencies along allowed power paths.
        # Entries left as 1 represent no loss on that connection.
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, EM_EFFICIENCY, EM_EFFICIENCY, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1],
        [1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ],
    "EtaDwn": [
        # Downstream efficiencies mirror the demand-flow direction used by FAST.
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, EM_EFFICIENCY, 1, 1, 1, 1, 1, 1, 1],
        [1, EM_EFFICIENCY, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, FAN_EFFICIENCY, 1, FAN_EFFICIENCY, 1, 1, 1, 1],
        [1, 1, 1, FAN_EFFICIENCY, 1, FAN_EFFICIENCY, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ],
    # Source and transmitter type vectors must be MATLAB row vectors. wrapper.py
    # handles that conversion specially when PropArch is "O".
    "SrcType": [1, 0],
    "TrnType": [1, 1, 0, 0, 2, 2],
}


# Attach the graph definition only for the custom "O" architecture. Built-in
# FAST architectures such as "C" or "E" ignore this graph.
if AIRCRAFT["Specs"]["Propulsion"]["PropArch"].upper() == "O":
    AIRCRAFT["Specs"]["Propulsion"]["PropArchGraph"] = GRAPH_BASED_PROPULSION


# =============================================================================
# RUN
# =============================================================================
def clean_matlab_log(log):
    # MATLAB warning output can include command-window backspace markers and
    # clickable HTML anchors. Strip those so terminal output stays readable.
    log = log.replace("\x08", "")
    log = re.sub(r"<a\b[^>]*>", "", log)
    log = log.replace("</a>", "")
    return log.strip()


def print_result(result):
    log = clean_matlab_log(result.get("log", ""))

    if log:
        print()
        print("FAST log:")
        print(log)


def main():
    # The context manager starts MATLAB, runs FAST, and shuts MATLAB down even
    # if FAST raises an error.
    with FastWrapper(FAST_PATH) as fast:
        result = fast.run(aircraft=AIRCRAFT, mission=MISSION)

    # Custom print from result
    print(f"Status: {result['status']}")
    print(f"MTOW: {result['mtow']:.6f} kg")

    # Keep FastWrapper.run's dictionary return value unchanged for downstream
    # code, but display the local script result as terminal-friendly text.
    print_result(result)


if __name__ == "__main__":
    main()
