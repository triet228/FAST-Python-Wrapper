# main.py

from core.aircraft_contract import (
    clean_output_fields,
    extract_mission_profile,
    prepare_aircraft,
    prop_arch_type,
)
from core.matlab_bridge import (
    matlab_expr,
    python_to_matlab,
    resolve_fast_path,
    start_matlab,
    to_python_data,
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

    engine = start_matlab(resolve_fast_path(fast_path))

    try:
        try:
            aircraft_python = prepare_aircraft(input_aircraft)
            input_prop_arch_type = prop_arch_type(aircraft_python)
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
            fast_status = engine.workspace["fast_status"]
        except Exception:
            fast_status = "No"

        try:
            fast_result = engine.workspace["fast_result"]
        except Exception:
            fast_result = {}

        output = to_python_data(fast_result)

        if isinstance(output, dict):
            clean_output_fields(output, input_prop_arch_type)

        if not isinstance(output, dict) or not output:
            return {
                "status": "No",
                "log": log,
                "output": {},
            }

        if str(fast_status) != "Yes":
            return {
                "status": "No",
                "log": log,
                "output": output,
            }

        return {
            "status": "Yes",
            "log": log,
            "output": output,
        }
    finally:
        engine.quit()
