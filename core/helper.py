# core/helper.py

"""Small file-loading helpers for FAST users."""

from pathlib import Path

from .json_io import (
    AIRCRAFT_JSON_PATH,
    DEFAULT_INPUT_DIR,
    JsonValidationError,
    load_json_data,
    read_raw_json_file,
)
from .schema_validation import (
    validate_aircraft_json,
)


def load_input_aircraft_json(input_dir=None):
    """Load the merged FAST aircraft input from InputAircraft.json.

    Inputs:
        input_dir: Directory containing InputAircraft.json. A missing value uses
            the default example directory.

    Outputs:
        Aircraft dictionary ready for FAST_Python_Wrapper().

    Assumptions:
        InputAircraft.json is a committed/template input file that users edit
        before running main.py.
    """

    if input_dir is None:
        base_path = DEFAULT_INPUT_DIR
    else:
        base_path = Path(input_dir)

    aircraft_json_path = base_path / AIRCRAFT_JSON_PATH

    if not aircraft_json_path.exists():
        raise JsonValidationError(
            f"{aircraft_json_path} is required. Edit or restore this input file, "
            "then call FAST_Python_Wrapper()."
        )

    data = read_raw_json_file(aircraft_json_path)
    validate_aircraft_json(data)
    return load_json_data(data)
