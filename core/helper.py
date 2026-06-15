# core/helper.py

"""Convenience imports and small file-loading helpers for FAST users.

Most examples import from this module so beginners have one place to start.
Implementation details still live in focused modules such as json_io.py,
schema_builder.py, schema_validation.py, and output_structure.py.
"""

from pathlib import Path

from .json_io import (
    AIRCRAFT_JSON_PATH,
    DEFAULT_INPUT_DIR,
    INPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    JsonValidationError,
    OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    SCHEMA_DIR,
    build_json_data,
    get_json_path,
    is_json_number,
    load_json_data,
    nan,
    print_result,
    read_raw_json_file,
    require_json_object,
)
from .output_structure import (
    build_output_aircraft_structure,
    print_output_aircraft_structure,
    unwrap_printable_schema,
)
from .schema_builder import (
    apply_prop_arch_schema_contract,
    build_json_schema_from_value,
    json_schema_matlab_expression,
    json_schema_number,
    json_schema_prop_arch,
    merge_json_array_schemas,
    merge_json_object_schemas,
    merge_json_schemas,
    merge_json_schemas_without_specialization,
)
from .schema_validation import (
    is_json_schema_document,
    read_schema_file,
    require_json_list,
    require_json_number,
    require_json_string,
    resolve_json_schema_ref,
    validate_aircraft_json,
    validate_json_markers,
    validate_json_schema_document,
    validate_json_schema_number_limits,
    validate_json_schema_type,
    validate_json_schema_value,
    validate_mission_profile_json,
    validate_output_aircraft_json,
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
