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

# local FAST checkout
FAST_PATH = required_env_path("FAST_PATH")

# FAST unspecified input marker
nan = float("nan")

# MATLAB expression wrapper
m = matlab_expr


# %% INPUT VALUES %%
# %%%%%%%%%%%%%%%%%%

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# %                            %
# % aircraft specifications    %
# %                            %
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
AIRCRAFT = {
    "Specs": {
        "TLAR": {
            # expected entry-into-service year
            "EIS": 2005,

            # ** REQUIRED ** aircraft class, either:
            #     (1) "Piston"    = piston aircraft
            #     (2) "Turboprop" = turboprop
            #     (3) "Turbofan"  = turbojet or turbofan
            "Class": "Turbofan",

            # ** REQUIRED **: number of passengers
            "MaxPax": 78,
        },

        # ----------------------------------------------------------

        "Aero": {
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            # %                            %
            # % aerodynamic parameters     %
            # %                            %
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            "L_D": {
                # climb lift-drag correction factor
                "ClbCF": 1.002,

                # cruise lift-drag correction factor
                "CrsCF": 1.000,

                # lift-drag ratio at climb
                "Clb": 10.9773 * 1.002,

                # lift-drag ratio at cruise
                "Crs": 15.2000 * 1.000,

                # lift-drag ratio at descent
                "Des": 10.9773 * 1.002,
            },
            "W_S": {
                # maximum wing loading (kg/m^2)
                "SLS": m(
                    'UnitConversionPkg.ConvMass(109.25, "lbm", "kg") / '
                    '(UnitConversionPkg.ConvLength(1, "ft", "m")) ^ 2'
                ),
            },
        },

        # ----------------------------------------------------------

        "Battery": {
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            # %                            %
            # % battery model parameters   %
            # %                            %
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

            # nominal cell voltage (V)
            "NomVolCell": 3.6,

            # maximum extrapolated cell voltage (V)
            "MaxExtVolCell": 4.0880,

            # cell capacity (Ah)
            "CapCell": 3,

            # internal cell resistance (ohm)
            "IntResist": 0.0199,

            # exponential-zone voltage parameter (V)
            "ExpVol": 0.0986,

            # exponential-zone capacity parameter (Ah)
            "ExpCap": 30,

            # minimum state of charge (%)
            "MinSOC": 20,

            # beginning state of charge (%)
            "BegSOC": 100,

            # maximum allowable C-rate
            "MaxAllowCRate": 5,

            # charging power (W)
            "Charging": 500 * 1000,
        },

        # ----------------------------------------------------------

        "Performance": {
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            # %                            %
            # % performance parameters     %
            # %                            %
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            "Vels": {
                # takeoff speed (m/s)
                "Tko": m('UnitConversionPkg.ConvVel(135, "kts", "m/s")'),

                # cruise speed (mach)
                "Crs": 0.78,
            },
            "Alts": {
                # takeoff altitude (m)
                "Tko": 0,

                # cruise altitude (m)
                "Crs": m('UnitConversionPkg.ConvLength(35000, "ft", "m")'),
            },

            # ** REQUIRED **: design range (m)
            "Range": m('UnitConversionPkg.ConvLength(2150, "naut mi", "m")'),

            # maximum rate-of-climb (m/s)
            "RCMax": m('UnitConversionPkg.ConvVel(2250, "ft/min", "m/s")'),
        },

        # ----------------------------------------------------------

        "Weight": {
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            # %                            %
            # % weights                    %
            # %                            %
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

            # maximum takeoff weight (kg)
            "MTOW": m('UnitConversionPkg.ConvMass(85517, "lbm", "kg")'),

            # electric generator weight (kg)
            "EG": nan,

            # electric motor weight (kg)
            "EM": 0,

            # block fuel (kg)
            "Fuel": m('UnitConversionPkg.ConvMass(20785, "lbm", "kg")'),

            # battery weight (kg)
            "Batt": 0,

            # airframe weight correction factor
            "WairfCF": 1.018,
        },

        # ----------------------------------------------------------

        "Propulsion": {
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            # %                            %
            # % propulsion parameters      %
            # %                            %
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

            # mass-flow correction factor
            "MDotCF": 1.029,

            # ** REQUIRED ** propulsion system architecture, either:
            #     (1) "C"   = conventional
            #     (2) "E"   = fully electric
            #     (3) "TE"  = fully turboelectric
            #     (4) "PE"  = partially turboelectric
            #     (5) "PHE" = parallel hybrid electric
            #     (6) "SHE" = series hybrid electric
            #     (7) "O"   = other architecture (specified by the user)
            "PropArch": "O",

            # engine (defined in EngineModelPkg)
            "Engine": m("EngineModelPkg.EngineSpecsPkg.CF34_8E5"),

            # number of engines
            "NumEngines": 2,
            "T_W": {
                # aircraft thrust-weight ratio
                "SLS": 0.3393,
            },
            "Thrust": {
                # total sea-level static thrust (N)
                "SLS": m('UnitConversionPkg.ConvForce(2 * 14510, "lbf", "N")'),
            },
            "Eta": {
                # engine propulsive efficiency
                "Prop": 0.8,
            },
        },

        # ----------------------------------------------------------

        "Power": {
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            # %                            %
            # % power specifications       %
            # %                            %
            # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            "SpecEnergy": {
                # gravimetric specific energy of combustible fuel (kWh/kg)
                "Fuel": 12,

                # gravimetric specific energy of battery (kWh/kg)
                "Batt": 0.25,
            },
            "Eta": {
                # electric motor efficiency
                "EM": 0.96,

                # electric generator efficiency
                "EG": nan,
            },
            "P_W": {
                # aircraft power-weight ratio (kW/kg)
                "SLS": nan,

                # electric motor power-weight ratio (kW/kg)
                "EM": 10,

                # electric generator power-weight ratio (kW/kg)
                "EG": nan,
            },
            "LamUps": {
                # upstream power split by mission phase
                "SLS": 1,
                "Tko": 1,
                "Clb": 1,
                "Crs": 0,
                "Des": 0,
                "Lnd": 0,
            },
            "LamDwn": {
                # downstream power split by mission phase
                "SLS": 0.1,
                "Tko": 0.1,
                "Clb": 0.01,
                "Crs": 0,
                "Des": 0,
                "Lnd": 0,
            },
            "Battery": {
                # battery parallel cell count
                "ParCells": 100,

                # battery series cell count
                "SerCells": 62,

                # initial battery state of charge (%)
                "BegSOC": 100,
            },
        },
    },

    # ----------------------------------------------------------

    "Settings": {
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # %                            %
        # % mission analysis           %
        # % properties                 %
        # %                            %
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        # takeoff segment discretization points
        "TkoPoints": nan,

        # climb segment discretization points
        "ClbPoints": nan,

        # cruise segment discretization points
        "CrsPoints": nan,

        # descent segment discretization points
        "DesPoints": nan,
        "OEW": {
            # maximum outer empty-weight iterations
            "MaxIter": 50,

            # outer empty-weight convergence tolerance
            "Tol": 0.001,
        },
        "Analysis": {
            # maximum analysis iterations
            "MaxIter": 30,

            # on design/off design analysis
            # +1 = on design
            # -1 = off design
            "Type": 1,
        },

        # include degradation analysis
        "Degradation": 0,

        # optimize power profile
        "PowerOpt": 0,

        # power strategy setting
        "PowerStrat": -1,

        # conserve battery state of charge
        "ConSOC": 1,

        # plot results or not
        # 0 = no plotting
        # 1 = plotting
        "Plotting": 0,

        # print result table or not
        "Table": 0,

        # print FAST output or not
        "PrintOut": 1,
    },
}


# %% DEFINE THE MISSION TARGETS %%
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
MISSION = {
    "Target": {
        # define the targets (in m or min)
        "Valu": [
            m("Aircraft.Specs.Performance.Range"),
            m('UnitConversionPkg.ConvLength(100, "naut mi", "m")'),
            45,
        ],

        # define the target types ("Dist" or "Time")
        "Type": ["Dist", "Dist", "Time"],
    },

    # %% DEFINE THE MISSION SEGMENTS %%
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    "Segs": [
        # define the segments
        "Takeoff", "Climb", "Climb", "Climb",
        "Cruise", "Descent", "Descent", "Descent",
        "Climb", "Climb", "Climb", "Cruise",
        "Cruise", "Descent", "Descent", "Descent", "Landing",
    ],
    "ID": [
        # define the mission id (segments in same mission must be consecutive)
        1, 1, 1, 1,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3, 3,
    ],
    "AltBeg": [
        # define the starting altitudes (in m)
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
        # define the ending altitudes (in m)
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
        # define the starting speeds (in m/s or mach)
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
        # define the ending speeds (in m/s or mach)
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
        # define the starting speed types (either "TAS", "EAS", or "Mach")
        "TAS", "TAS", "EAS", "EAS",
        "Mach", "Mach", "EAS", "EAS",
        "TAS", "EAS", "EAS", "TAS",
        "TAS", "TAS", "EAS", "EAS", "TAS",
    ],
    "TypeEnd": [
        # define the ending speed types (either "TAS", "EAS", or "Mach")
        "TAS", "EAS", "EAS", "Mach",
        "Mach", "EAS", "EAS", "TAS",
        "EAS", "EAS", "TAS", "TAS",
        "TAS", "EAS", "EAS", "TAS", "TAS",
    ],
    "ClbRate": [
        # define the rate of climb/descent (in m/s)
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan, nan,
    ],
}

# %% REMEMBER THE MISSION PROFILE %%
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


# ----------------------------------------------------------

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# %                            %
# % graph-based propulsion     %
# % architecture               %
# %                            %
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# fan efficiency
FAN_EFFICIENCY = 0.99

# electric motor efficiency
EM_EFFICIENCY = 0.96
GRAPH_BASED_PROPULSION = {
    "Arch": [
        # propulsion architecture adjacency matrix
        # components: fuel, battery, engines, electric motors, fans, sink
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
        # upstream operation matrix as a function of lambda
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
        # downstream operation matrix as a function of lambda
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
        # upstream efficiency matrix
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
        # downstream efficiency matrix
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

    # source component type vector
    # 1 = fuel, 0 = battery
    "SrcType": [1, 0],

    # transmitter component type vector
    # 1 = engine, 0 = electric motor, 2 = propeller/fan
    "TrnType": [1, 1, 0, 0, 2, 2],
}


# attach user-specified architecture when PropArch is "O"
if AIRCRAFT["Specs"]["Propulsion"]["PropArch"].upper() == "O":
    AIRCRAFT["Specs"]["Propulsion"]["PropArchGraph"] = GRAPH_BASED_PROPULSION


# ----------------------------------------------------------

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# %                            %
# % run FAST                   %
# %                            %
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def clean_matlab_log(log):
    # clean MATLAB command-window artifacts from captured FAST log
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
    # start MATLAB, run FAST, and shut MATLAB down
    with FastWrapper(FAST_PATH) as fast:
        result = fast.run(aircraft=AIRCRAFT, mission=MISSION)

    # print run status
    print(f"Status: {result['status']}")

    # print maximum takeoff weight (kg)
    print(f"MTOW: {result['mtow']:.6f} kg")

    # print FAST log
    print_result(result)


if __name__ == "__main__":
    main()
