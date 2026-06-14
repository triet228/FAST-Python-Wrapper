# main.py

from pathlib import Path
from helper import (
    build_output_aircraft_structure,
    load_input_aircraft_json,
    print_output_aircraft_structure,
    print_result,
)
from wrapper import FastWrapper


# Python dictionary equivalent of FAST MATLAB OutputAircraft.
#
# The wrapper populates this after Main.m returns. It is intentionally mutated
# in place, so code that imports OUTPUT_AIRCRAFT keeps a live reference to the
# latest FAST output dictionary instead of a stale pre-run object.
OUTPUT_AIRCRAFT = {}

# Recursive shape of OUTPUT_AIRCRAFT with field names, list lengths, and scalar
# types. This is useful when exploring FAST output without printing every value.
OUTPUT_AIRCRAFT_STRUCTURE = {}

# Structure output controls. The console preview is capped because FAST can
# attach large reference data.
PRINT_OUTPUT_AIRCRAFT_STRUCTURE = True
PRINT_OUTPUT_AIRCRAFT_STRUCTURE_DEPTH = 3
PRINT_OUTPUT_AIRCRAFT_STRUCTURE_ITEMS = 20

# Runtime input supplied as a Python dictionary.
INPUT_AIRCRAFT = {}


def main(INPUT_AIRCRAFT_DICT, FAST_DIR):
    """Run FAST from a Python InputAircraft dictionary.

    Inputs:
        INPUT_AIRCRAFT_DICT: Python dictionary matching InputAircraftSchema.
        FAST_DIR: Local FAST checkout path containing Main.m.

    Outputs:
        Dictionary containing status, MATLAB stdout log, and OutputAircraft.

    Side effects:
        Starts MATLAB Engine, runs FAST, populates module globals for
        interactive inspection, and prints status, MTOW, output structure, and
        FAST log text.
    """

    global INPUT_AIRCRAFT

    INPUT_AIRCRAFT = INPUT_AIRCRAFT_DICT

    # Start MATLAB, run FAST, and shut MATLAB down.
    with FastWrapper(FAST_DIR) as fast:
        result = fast.run(input_aircraft=INPUT_AIRCRAFT)

    # Populate the Python equivalent of MATLAB's OutputAircraft struct.
    OUTPUT_AIRCRAFT.clear()
    OUTPUT_AIRCRAFT.update(result["output"])
    OUTPUT_AIRCRAFT_STRUCTURE.clear()

    if OUTPUT_AIRCRAFT:
        OUTPUT_AIRCRAFT_STRUCTURE.update(
            build_output_aircraft_structure(OUTPUT_AIRCRAFT)
        )

    print(f"Status: {result['status']}")

    if OUTPUT_AIRCRAFT:
        mtow = OUTPUT_AIRCRAFT.get("Specs", {}).get("Weight", {}).get("MTOW")

        if mtow is not None:
            print(f"MTOW: {mtow:.6f} kg")
    else:
        print("OutputAircraft: not produced")

    if PRINT_OUTPUT_AIRCRAFT_STRUCTURE and OUTPUT_AIRCRAFT_STRUCTURE:
        print()
        print(
            "OutputAircraft structure "
            f"(first {PRINT_OUTPUT_AIRCRAFT_STRUCTURE_DEPTH} levels):"
        )
        print_output_aircraft_structure(
            OUTPUT_AIRCRAFT_STRUCTURE,
            max_depth=PRINT_OUTPUT_AIRCRAFT_STRUCTURE_DEPTH,
            max_items=PRINT_OUTPUT_AIRCRAFT_STRUCTURE_ITEMS,
        )

    print_result(result)

    return result


if __name__ == "__main__":
    ROOT_DIR = Path(__file__).resolve().parent
    INPUT_DIR = ROOT_DIR / "examples" / "CeRAS"
    FAST_DIR = ROOT_DIR.parent / "FAST"
    INPUT_AIRCRAFT_DICT = load_input_aircraft_json(INPUT_DIR)

    main(INPUT_AIRCRAFT_DICT, FAST_DIR)
