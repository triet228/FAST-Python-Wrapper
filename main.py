# main.py

from helper import (
    build_output_aircraft_structure,
    load_input_json_files,
    print_output_aircraft_structure,
    print_result,
    save_output_aircraft,
    save_output_aircraft_structure,
)
from wrapper import FastWrapper, load_env_file, required_env_path


# Python dictionary equivalent of FAST MATLAB OutputAircraft.
#
# The wrapper populates this after Main.m returns. It is intentionally mutated
# in place, so code that imports OUTPUT_AIRCRAFT keeps a live reference to the
# latest FAST output dictionary instead of a stale pre-run object.
OUTPUT_AIRCRAFT = {}

# Recursive shape of OUTPUT_AIRCRAFT with field names, list lengths, and scalar
# types. This is useful when exploring FAST output without printing every value.
OUTPUT_AIRCRAFT_STRUCTURE = {}

# Structure output controls. The complete output tree is saved to JSON, while
# the console preview is capped because FAST can attach large reference data.
PRINT_OUTPUT_AIRCRAFT_STRUCTURE = True
PRINT_OUTPUT_AIRCRAFT_STRUCTURE_DEPTH = 3
PRINT_OUTPUT_AIRCRAFT_STRUCTURE_ITEMS = 20

# Runtime inputs loaded from InputAircraft.json and Mission.json.
AIRCRAFT = {}
MISSION = {}


def main(INPUT_DIR=".", OUTPUT_DIR="."):
    """Run FAST from JSON inputs and save the converted OutputAircraft result.

    Inputs:
        INPUT_DIR: Directory containing InputAircraft.json and Mission.json.
        OUTPUT_DIR: Directory where generated OutputAircraft files are written.
        FAST_PATH is read from local environment configuration.

    Outputs:
        The result dictionary returned by FastWrapper.run().

    Side effects:
        Starts MATLAB Engine, runs FAST, rewrites generated OutputAircraft JSON
        files in OUTPUT_DIR, and prints status, MTOW, output structure, and FAST
        log text.
    """

    global AIRCRAFT
    global MISSION

    load_env_file()
    fast_path = required_env_path("FAST_PATH")

    # InputAircraft.json and Mission.json are the user-editable run inputs. They
    # are validated before MATLAB starts so input mistakes fail quickly.
    AIRCRAFT, MISSION = load_input_json_files(INPUT_DIR)

    # Start MATLAB, run FAST, and shut MATLAB down.
    with FastWrapper(fast_path) as fast:
        result = fast.run(aircraft=AIRCRAFT, mission=MISSION)

    # Populate the Python equivalent of MATLAB's saved OutputAircraft struct.
    OUTPUT_AIRCRAFT.clear()
    OUTPUT_AIRCRAFT.update(result["aircraft"])
    OUTPUT_AIRCRAFT_STRUCTURE.clear()
    OUTPUT_AIRCRAFT_STRUCTURE.update(
        build_output_aircraft_structure(OUTPUT_AIRCRAFT)
    )
    output_aircraft_path = save_output_aircraft(OUTPUT_AIRCRAFT, OUTPUT_DIR)
    output_structure_path = save_output_aircraft_structure(
        OUTPUT_AIRCRAFT_STRUCTURE,
        OUTPUT_DIR,
    )

    print(f"Status: {result['status']}")
    print(f"MTOW: {result['mtow']:.6f} kg")

    if PRINT_OUTPUT_AIRCRAFT_STRUCTURE:
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
        print(f"Output saved to {output_aircraft_path}")
        print(f"Full structure saved to {output_structure_path}")

    print_result(result)

    return result


if __name__ == "__main__":
    main()
