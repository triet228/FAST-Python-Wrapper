# main.py

from core.fast_runner import run_fast
from core.matlab_bridge import matlab_expr


def FAST_Python_Wrapper(input_aircraft, fast_path):
    """Run FAST from a Python InputAircraft dictionary.

    Inputs:
        input_aircraft: Nested dictionary matching InputAircraftSchema.
        fast_path: Local FAST checkout path containing Main.m.

    Outputs:
        Dictionary containing status, MATLAB stdout log, and OutputAircraft.

    Side effects:
        Starts MATLAB Engine, adds FAST to the MATLAB path, runs Main.m, and
        quits MATLAB before returning.
    """

    return run_fast(input_aircraft, fast_path)
