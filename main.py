# main.py

from pathlib import Path
from math import nan

from core.aircraft_contract import (
    clean_output_fields,
    extract_mission_profile,
    prepare_aircraft,
)
from core.matlab_bridge import (
    matlab_expr,
    python_to_matlab,
    resolve_fast_path,
    start_matlab,
    matlab_to_python,
)


def FAST_Python_Wrapper(input_aircraft, fast_path):
    """Run FAST once from a Python InputAircraft dictionary.

    Inputs:
        input_aircraft: Nested dictionary matching InputAircraftSchema, with
            Mission.Profile holding the mission profile fields.
        fast_path: Local FAST checkout path containing Main.m.

    Outputs:
        Dictionary containing:
        - status: "Yes" when FAST returns OutputAircraft, otherwise "No".
        - log: MATLAB stdout captured during the run.
        - output: Python dictionary equivalent of FAST OutputAircraft, or an
            empty dictionary when FAST does not produce one.

    Side effects:
        Starts MATLAB Engine, adds FAST to the MATLAB path, runs Main.m, and
        quits MATLAB before returning.
    """
    # Start MATLAB Engine
    engine = start_matlab(resolve_fast_path(fast_path))

    try:
        try:
            # Convert Python Dictionary to MATLAB struct
            aircraft_python = prepare_aircraft(input_aircraft)
            mission_python = extract_mission_profile(aircraft_python)
            aircraft_matlab = python_to_matlab(aircraft_python)
            mission_matlab = python_to_matlab(mission_python)
        except Exception as error:
            return {
                "status": "No",
                "log": str(error),
                "output": {},
            }

        try:
            # Run FAST in MATLAB
            log = engine.evalc(
                f"""
                aircraft_spec = {aircraft_matlab};
                mission_profile = @(Aircraft) setfield(Aircraft, "Mission", "Profile", {mission_matlab});
                fast_result = struct();
                fast_status = 'No';
                try
                    fast_result = Main(aircraft_spec, mission_profile);
                    fast_status = 'Yes';
                catch fast_exception
                    disp(getReport(fast_exception, 'extended', 'hyperlinks', 'off'));
                end
                """,
                nargout=1,
            )
        except Exception as error:
            return {
                "status": "No",
                "log": str(error),
                "output": {},
            }

        try:
            # Extract FAST run status
            fast_status = engine.workspace["fast_status"]
        except Exception:
            fast_status = "No"

        try:
            # Extract OutputAircraft
            fast_result = engine.workspace["fast_result"]
            # Convert MATLAB struct to Python dictionary
            output = matlab_to_python(fast_result)
        except Exception:
            output = {}

        # Clean OutputAircraft fields that are too specific (like local file paths)
        if isinstance(output, dict):
            clean_output_fields(output)

        # FAST ran successfully and produced an output
        if str(fast_status) == "Yes":
            return {
                "status": "Yes",
                "log": log,
                "output": output,
            }
        else:
            return {
                "status": "No",
                "log": log,
                "output": output,
            }
    finally:
        # Quit MATLAB Engine
        engine.quit()


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    fast_dir = project_dir.parent / "FAST"

    input_aircraft = {
        "Specs": {
            "TLAR": {
                "EIS": 2005,
                "Class": "Turbofan",
                "MaxPax": 218.8828,
            },
            "Aero": {
                "L_D": {
                    "ClbCF": 1,
                    "CrsCF": 1,
                    "Clb": 13,
                    "Crs": 17,
                    "Des": 13,
                },
                "W_S": {
                    "SLS": 739.8499,
                },
            },
            "Propulsion": {
                "MDotCF": 1.2,
                "PropArch": {
                    "Type": "C",
                },
                "Engine": {
                    "Mach": 0.05,
                    "Alt": 0,
                    "OPR": 24.5,
                    "FPR": 1.6,
                    "BPR": 4,
                    "Tt4Max": 1711,
                    "TempLimit": {
                        "Val": nan,
                        "Type": nan,
                    },
                    "DesignThrust": 64543.6956,
                    "NoSpools": 2,
                    "RPMs": {
                        "_matlab_row": [
                            7400,
                            17820,
                        ],
                    },
                    "FanGearRatio": nan,
                    "FanBoosters": False,
                    "CoreFlow": {
                        "PaxBleed": 0.03,
                        "Leakage": 0.01,
                        "Cooling": 0,
                    },
                    "MaxIter": 300,
                    "EtaPoly": {
                        "Inlet": 0.99,
                        "Diffusers": 0.99,
                        "Fan": 0.99,
                        "Compressors": 0.94,
                        "BypassNozzle": 0.99,
                        "Combustor": 0.995,
                        "Turbines": 0.94,
                        "CoreNozzle": 0.99,
                        "Nozzles": 0.99,
                        "Mixing": 0,
                    },
                    "PerElec": 0,
                    "Cff3": 0.299,
                    "Cff2": -0.346,
                    "Cff1": 0.701,
                    "Cffch": 0,
                    "HEcoeff": 1,
                },
                "NumEngines": 2,
                "T_W": {
                    "SLS": 0.3,
                },
                "Eta": {
                    "Prop": 0.8,
                },
            },
            "Weight": {
                "WairfCF": 1,
                "MTOW": 86182.5503,
                "EM": 0,
                "Fuel": 9427.9174,
                "Batt": 0,
            },
            "Performance": {
                "Vels": {
                    "Tko": 69.45,
                    "Crs": 0.78,
                },
                "Alts": {
                    "Tko": 0,
                    "Crs": 10668,
                },
                "Range": 4630000,
                "RCMax": 11.43,
            },
            "Power": {
                "SpecEnergy": {
                    "Fuel": 12,
                    "Batt": 0.25,
                },
                "Eta": {
                    "EM": 0.96,
                    "EG": 0.96,
                },
                "P_W": {
                    "EM": 10,
                },
            },
        },
        "Settings": {
            "OEW": {
                "MaxIter": 50,
                "Tol": 0.001,
            },
            "Analysis": {
                "MaxIter": 50,
                "Type": 1,
            },
            "Plotting": 0,
            "Table": 0,
        },
        "Mission": {
            "Profile": {
                "Target": {
                    "Valu": [
                        1620500,
                        3009500,
                    ],
                    "Type": [
                        "Dist",
                        "Dist",
                    ],
                },
                "Segs": [
                    "Climb",
                    "Cruise",
                    "Climb",
                    "Cruise",
                    "Descent",
                ],
                "ID": [
                    1,
                    1,
                    2,
                    2,
                    2,
                ],
                "AltBeg": [
                    0,
                    10058.4,
                    10058.4,
                    10668,
                    10668,
                ],
                "AltEnd": [
                    10058.4,
                    10058.4,
                    10668,
                    10668,
                    0,
                ],
                "VelBeg": [
                    0.2,
                    0.78,
                    0.78,
                    0.78,
                    0.78,
                ],
                "VelEnd": [
                    0.78,
                    0.78,
                    0.78,
                    0.78,
                    0.2,
                ],
                "TypeBeg": [
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                ],
                "TypeEnd": [
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                ],
                "ClbRate": [
                    nan,
                    nan,
                    nan,
                    nan,
                    nan,
                ],
            },
        },
    }

    result = FAST_Python_Wrapper(input_aircraft, fast_dir)

    print("Run success:" + str(result["status"]))
    print(result["log"])
    print("MTOW:" + str(result["output"]["Specs"]["Weight"]["MTOW"]))
    
