# helper.py

import json
import re
from pathlib import Path

from wrapper import MatlabExpression, MatlabRow


# FAST unspecified input marker.
nan = float("nan")

# Default example run directories and file names. InputAircraft.json and
# Mission.json are required inputs; the OutputAircraft files are regenerated
# after each successful FAST run.
DEFAULT_INPUT_DIR = Path("examples/CeRAS/inputs")
DEFAULT_OUTPUT_DIR = Path("examples/CeRAS/outputs")
CONTRACTS_DIR = Path("contracts")
AIRCRAFT_JSON_PATH = Path("InputAircraft.json")
MISSION_JSON_PATH = Path("Mission.json")
INPUT_AIRCRAFT_STRUCTURE_JSON_PATH = Path("InputAircraftStructure.json")
MISSION_STRUCTURE_JSON_PATH = Path("MissionStructure.json")
OUTPUT_AIRCRAFT_JSON_PATH = Path("OutputAircraft.json")
OUTPUT_AIRCRAFT_STRUCTURE_JSON_PATH = Path("OutputAircraftStructure.json")


class JsonValidationError(ValueError):
    """Report an invalid FAST JSON input or output file."""


def build_input_json_paths(input_dir=None):
    """Return aircraft and mission input paths for a FAST run.

    Inputs:
        input_dir: Directory containing InputAircraft.json and Mission.json. A
            missing value uses the default inputs directory.

    Outputs:
        A tuple containing the aircraft JSON path and mission JSON path.

    Assumptions:
        FAST run inputs are grouped in one directory so callers can run several
        cases without renaming files in the project root.
    """

    if input_dir is None:
        base_path = DEFAULT_INPUT_DIR
    else:
        base_path = Path(input_dir)

    return (
        base_path / AIRCRAFT_JSON_PATH,
        base_path / MISSION_JSON_PATH,
    )


def build_output_json_paths(output_dir=None):
    """Return generated output paths for a FAST run.

    Inputs:
        output_dir: Directory where OutputAircraft JSON files should be written.
            A missing value uses the default outputs directory.

    Outputs:
        A tuple containing the full aircraft output path and structure output
        path.

    Assumptions:
        Both generated output files belong in the same run output directory.
    """

    if output_dir is None:
        base_path = DEFAULT_OUTPUT_DIR
    else:
        base_path = Path(output_dir)

    return (
        base_path / OUTPUT_AIRCRAFT_JSON_PATH,
        base_path / OUTPUT_AIRCRAFT_STRUCTURE_JSON_PATH,
    )


def print_result(result):
    """Print a cleaned FAST command-window log.

    Inputs:
        result: Dictionary returned by FastWrapper.run(), optionally containing
            a MATLAB command-window log under the "log" key.

    Outputs:
        None. The cleaned log is printed only when it is non-empty.

    Side effects:
        Writes to standard output for interactive runs.
    """

    # FAST logs can contain MATLAB backspace characters and HTML links from
    # command-window warnings. Strip those so terminal output is readable.
    log = result.get("log", "")
    log = log.replace("\x08", "")
    log = re.sub(r"<a\b[^>]*>", "", log)
    log = log.replace("</a>", "")
    log = log.strip()

    if log:
        print()
        print("FAST log:")
        print(log)


def build_json_data(value):
    """Return a JSON-safe copy of FAST data.

    Inputs:
        value: Python FAST data that may include MATLAB expression wrappers,
            MATLAB Engine arrays, NaN markers, nested dictionaries, or lists.

    Outputs:
        A JSON-serializable structure preserving field names and MATLAB source
        expressions. NaN is written as the string "NaN" because standard JSON
        has no portable NaN literal.

    Assumptions:
        Input files can be rehydrated by load_json_data(). Output files are for
        inspection, so unsupported MATLAB/Python objects are represented by
        their type and string form instead of being dropped.
    """

    if isinstance(value, MatlabExpression):
        return {"_matlab_expression": value.value}

    if isinstance(value, MatlabRow):
        return {"_matlab_row": build_json_data(value.value)}

    if isinstance(value, dict):
        return {
            key: build_json_data(item)
            for key, item in value.items()
        }

    if isinstance(value, list) or isinstance(value, tuple):
        return [build_json_data(item) for item in value]

    if isinstance(value, float) and value != value:
        return "NaN"

    if type(value).__module__.startswith("matlab.") and hasattr(value, "__iter__"):
        return [build_json_data(item) for item in value]

    if value is None or isinstance(value, str):
        return value

    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value

    return {
        "_python_type": type(value).__name__,
        "_repr": normalize_object_repr(str(value)),
    }


def normalize_object_repr(value):
    """Return object repr text without process-specific memory addresses."""

    return re.sub(r" at 0x[0-9A-Fa-f]+(?=>)", "", value)


def load_json_data(value):
    """Convert JSON FAST input data back into wrapper-ready Python data.

    Inputs:
        value: Data loaded from InputAircraft.json or Mission.json.

    Outputs:
        Python data accepted by FastWrapper.run(), including restored MATLAB
        expressions, MATLAB row-vector markers, and NaN values.

    Assumptions:
        The JSON files use the marker objects generated by build_json_data().
        Plain string "NaN" is treated as the FAST unspecified input marker.
    """

    if isinstance(value, dict):
        if set(value.keys()) == {"_matlab_expression"}:
            return MatlabExpression(value["_matlab_expression"])

        if set(value.keys()) == {"_matlab_row"}:
            return MatlabRow(load_json_data(value["_matlab_row"]))

        return {
            key: load_json_data(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [load_json_data(item) for item in value]

    if value == "NaN":
        return nan

    return value


def write_json_file(path, value):
    """Write a generated JSON file with stable formatting.

    Inputs:
        path: Destination path in the project root.
        value: JSON-serializable data.

    Outputs:
        None. The destination file is overwritten.

    Side effects:
        Rewrites generated inspection files after each FAST run so stale
        structures do not linger beside a newer case.
    """

    path.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )


def read_raw_json_file(path):
    """Parse a JSON file and report file-specific syntax errors.

    Inputs:
        path: JSON file path to read.

    Outputs:
        Data returned by json.loads().

    Side effects:
        None.
    """

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise JsonValidationError(
            f"{path} is not valid JSON: {error.msg} at line "
            f"{error.lineno}, column {error.colno}."
        ) from error


def require_json_object(value, path):
    """Return value when it is a JSON object, otherwise fail.

    Inputs:
        value: Parsed JSON value.
        path: Human-readable location used in the error message.

    Outputs:
        The original value when it is a dictionary.

    Assumptions:
        FAST aircraft, mission, and OutputAircraft files are object roots.
    """

    if not isinstance(value, dict):
        raise JsonValidationError(f"{path} must be a JSON object.")

    return value


def get_json_path(data, keys, file_name):
    """Read a required nested JSON field.

    Inputs:
        data: Parsed JSON object.
        keys: List of nested field names.
        file_name: File label used in validation errors.

    Outputs:
        The nested value.
    """

    current = data
    walked = []

    for key in keys:
        walked.append(key)

        if not isinstance(current, dict) or key not in current:
            joined = ".".join(walked)
            raise JsonValidationError(f"{file_name} is missing required field {joined}.")

        current = current[key]

    return current


def is_json_number(value):
    """Return True for JSON numeric values that are not booleans."""

    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(
        value,
        bool,
    )


def build_input_json_structure(value):
    """Return a recursive optional contract for FAST input JSON data.

    Inputs:
        value: Parsed JSON value from InputAircraft.json or Mission.json.

    Outputs:
        Contract nodes that preserve field names, broad JSON types, marker
        shapes, and list item contracts.

    Assumptions:
        Generated contract fields are optional by default. Optional "NaN"
        placeholders are accepted by validation regardless of the declared
        field type.
    """

    if isinstance(value, dict):
        keys = set(value.keys())

        if keys == {"_matlab_expression"}:
            return {
                "type": "matlab_expression",
                "required": False,
            }

        if keys == {"_matlab_row"}:
            return {
                "type": "matlab_row",
                "required": False,
                "items": build_input_json_structure(value["_matlab_row"]),
            }

        return {
            "type": "object",
            "required": False,
            "fields": {
                key: build_input_json_structure(item)
                for key, item in value.items()
            },
        }

    if isinstance(value, list):
        item_structure = None

        if value:
            item_structure = build_input_json_structure(value[0])

        return {
            "type": "list",
            "required": False,
            "items": item_structure,
        }

    if is_json_number(value) or value == "NaN":
        return {
            "type": "number",
            "required": False,
        }

    if isinstance(value, str):
        return {
            "type": "string",
            "required": False,
        }

    if isinstance(value, bool):
        return {
            "type": "bool",
            "required": False,
        }

    if value is None:
        return {
            "type": "null",
            "required": False,
        }

    return {
        "type": type(value).__name__,
        "required": False,
    }


def read_contract_structure(file_name):
    """Read a committed input structure contract from contracts/.

    Inputs:
        file_name: Contract JSON file name.

    Outputs:
        Parsed contract structure.

    Side effects:
        None.
    """

    path = CONTRACTS_DIR / file_name

    if not path.exists():
        raise JsonValidationError(f"{path} is required for input validation.")

    return read_raw_json_file(path)


def validate_json_structure_contract(data, contract, file_name, path=""):
    """Validate parsed JSON against a committed optional field contract.

    Inputs:
        data: Parsed input JSON subtree.
        contract: Contract subtree generated by build_input_json_structure().
        file_name: Input file label used in validation errors.
        path: Current dotted JSON path.

    Outputs:
        None. Raises JsonValidationError when the input structure drifts from
        the committed contract.

    Assumptions:
        Missing fields and "NaN" placeholders are accepted only for optional
        contract nodes. Required nodes must be present and contain a real value
        of the declared type.
    """

    validate_contract_value(data, contract, file_name, path or file_name)


def validate_contract_value(data, contract, file_name, label):
    """Validate one JSON value against either the new or legacy contract form."""

    if is_new_contract_node(contract):
        validate_new_contract_value(data, contract, file_name, label)
        return

    validate_legacy_contract_value(data, contract, file_name, label)


def is_new_contract_node(contract):
    """Return True when a contract node uses the optional field schema."""

    return isinstance(contract, dict) and "type" in contract


def validate_new_contract_value(data, contract, file_name, label):
    """Validate one JSON value against a type/required/fields contract node."""

    if data == "NaN":
        if contract.get("required", False):
            raise JsonValidationError(f"{label} is required and cannot be \"NaN\".")
        return

    expected_types = contract.get("type")

    if isinstance(expected_types, str):
        expected_types = [expected_types]

    if len(expected_types) == 1:
        validate_new_contract_type(
            data,
            contract,
            expected_types[0],
            file_name,
            label,
        )
        return

    errors = []

    for expected_type in expected_types:
        try:
            validate_new_contract_type(
                data,
                contract,
                expected_type,
                file_name,
                label,
            )
            return
        except JsonValidationError as error:
            errors.append(str(error))

    if errors:
        expected = ", ".join(expected_types)
        raise JsonValidationError(f"{label} must match type {expected}.")

    raise JsonValidationError(f"{label} has no valid contract type.")


def validate_new_contract_type(data, contract, expected_type, file_name, label):
    """Validate data against one concrete type inside a possibly union contract."""

    if expected_type == "object":
        if not isinstance(data, dict):
            raise JsonValidationError(f"{label} must be a JSON object.")

        fields = contract.get("fields", {})
        expected_keys = set(fields)
        actual_keys = set(data)

        for key in sorted(actual_keys - expected_keys):
            raise JsonValidationError(f"{label} contains unexpected field {key}.")

        for key in sorted(expected_keys):
            child_label = f"{label}.{key}"
            child_contract = fields[key]

            if key not in data:
                if child_contract.get("required", False):
                    raise JsonValidationError(
                        f"{label} is missing required field {key}."
                    )
                continue

            validate_contract_value(
                data[key],
                child_contract,
                file_name,
                child_label,
            )

        return

    if expected_type == "list":
        if not isinstance(data, list):
            raise JsonValidationError(f"{label} must be a JSON array.")

        item_contract = contract.get("items")

        if item_contract is not None:
            for index, item in enumerate(data):
                validate_contract_value(
                    item,
                    item_contract,
                    file_name,
                    f"{label}[{index}]",
                )

        return

    if expected_type == "matlab_row":
        if not (
            isinstance(data, dict)
            and set(data.keys()) == {"_matlab_row"}
            and isinstance(data["_matlab_row"], list)
        ):
            raise JsonValidationError(f"{label} must be a _matlab_row marker.")

        item_contract = contract.get("items")

        if item_contract is not None:
            validate_contract_value(
                data["_matlab_row"],
                item_contract,
                file_name,
                f"{label}._matlab_row",
            )

        return

    if expected_type == "matlab_expression":
        if (
            isinstance(data, dict)
            and set(data.keys()) == {"_matlab_expression"}
            and isinstance(data["_matlab_expression"], str)
        ):
            return

        raise JsonValidationError(f"{label} must be a _matlab_expression marker.")

    if expected_type == "python_marker":
        if (
            isinstance(data, dict)
            and set(data.keys()) == {"_python_type", "_repr"}
            and isinstance(data["_python_type"], str)
            and isinstance(data["_repr"], str)
        ):
            return

        raise JsonValidationError(f"{label} must be a Python output marker.")

    if expected_type == "number":
        if is_json_number(data):
            return

        if (
            isinstance(data, dict)
            and set(data.keys()) == {"_matlab_expression"}
            and isinstance(data["_matlab_expression"], str)
        ):
            return

        raise JsonValidationError(
            f"{label} must be a number or a _matlab_expression marker."
        )

    if expected_type == "string":
        if isinstance(data, str):
            return

        raise JsonValidationError(f"{label} must be a string.")

    if expected_type == "bool":
        if isinstance(data, bool):
            return

        raise JsonValidationError(f"{label} must be true or false.")

    if expected_type == "null":
        if data is None:
            return

        raise JsonValidationError(f"{label} must be null.")

    raise JsonValidationError(f"{label} uses unknown contract type {expected_type}.")


def validate_legacy_contract_value(data, contract, file_name, label):
    """Validate one JSON value against the original structure-only contract."""

    if isinstance(contract, dict) and contract.get("_type") == "list":
        if not isinstance(data, list):
            raise JsonValidationError(f"{label} must be a JSON array.")

        item_contract = contract.get("_items")

        if item_contract is not None:
            for index, item in enumerate(data):
                validate_json_structure_contract(
                    item,
                    item_contract,
                    file_name,
                    f"{label}[{index}]",
                )

        return

    if isinstance(contract, dict):
        if not isinstance(data, dict):
            raise JsonValidationError(f"{label} must be a JSON object.")

        expected_keys = set(contract)
        actual_keys = set(data)

        for key in sorted(expected_keys - actual_keys):
            raise JsonValidationError(f"{label} is missing required field {key}.")

        for key in sorted(actual_keys - expected_keys):
            raise JsonValidationError(f"{label} contains unexpected field {key}.")

        for key in sorted(expected_keys):
            child_label = f"{label}.{key}"
            validate_json_structure_contract(
                data[key],
                contract[key],
                file_name,
                child_label,
            )

        return

    if contract == "number":
        if is_json_number(data) or data == "NaN":
            return

        if (
            isinstance(data, dict)
            and set(data.keys()) == {"_matlab_expression"}
            and isinstance(data["_matlab_expression"], str)
        ):
            return

        raise JsonValidationError(
            f"{label} must be a number, \"NaN\", or a _matlab_expression marker."
        )

    if contract == "string":
        if isinstance(data, str):
            return

        raise JsonValidationError(f"{label} must be a string.")

    if contract == "bool":
        if isinstance(data, bool):
            return

        raise JsonValidationError(f"{label} must be true or false.")

    if contract == "null":
        if data is None:
            return

        raise JsonValidationError(f"{label} must be null.")

    if type(data).__name__ != contract:
        raise JsonValidationError(f"{label} must match contract type {contract}.")


def require_json_number(data, keys, file_name):
    """Validate that a required nested field is numeric or a MATLAB expression."""

    value = get_json_path(data, keys, file_name)

    if is_json_number(value):
        return

    if (
        isinstance(value, dict)
        and set(value.keys()) == {"_matlab_expression"}
        and isinstance(value["_matlab_expression"], str)
    ):
        return

    joined = ".".join(keys)
    raise JsonValidationError(
        f"{file_name}.{joined} must be a number or a _matlab_expression marker."
    )


def require_json_string(data, keys, file_name):
    """Validate that a required nested field is a string."""

    value = get_json_path(data, keys, file_name)

    if isinstance(value, str):
        return

    joined = ".".join(keys)
    raise JsonValidationError(f"{file_name}.{joined} must be a string.")


def require_json_list(data, keys, file_name):
    """Validate that a required nested field is a list and return it."""

    value = get_json_path(data, keys, file_name)

    if isinstance(value, list):
        return value

    joined = ".".join(keys)
    raise JsonValidationError(f"{file_name}.{joined} must be a JSON array.")


def require_json_list_or_scalar_list(data, keys, file_name):
    """Return a list view of a required field that may be scalar or list."""

    value = get_json_path(data, keys, file_name)

    if isinstance(value, list):
        return value

    return [value]


def validate_json_markers(value, file_name, path="", allow_output_markers=False):
    """Validate wrapper marker objects used inside JSON files.

    Inputs:
        value: Parsed JSON subtree.
        file_name: File label used in validation errors.
        path: Current dotted JSON path.
        allow_output_markers: Whether output-only object markers are accepted.

    Outputs:
        None. Raises JsonValidationError on invalid markers.

    Assumptions:
        Marker dictionaries reserve keys beginning with "_". User data should
        not mix marker keys with normal FAST fields.
    """

    if isinstance(value, dict):
        keys = set(value.keys())
        label = path or file_name
        marker_keys = [key for key in keys if key.startswith("_")]

        if marker_keys:
            if keys == {"_matlab_expression"}:
                if not isinstance(value["_matlab_expression"], str):
                    raise JsonValidationError(
                        f"{label}._matlab_expression must be a string."
                    )
                return

            if keys == {"_matlab_row"}:
                if not isinstance(value["_matlab_row"], list):
                    raise JsonValidationError(f"{label}._matlab_row must be an array.")
                validate_json_markers(
                    value["_matlab_row"],
                    file_name,
                    f"{label}._matlab_row",
                    allow_output_markers,
                )
                return

            if allow_output_markers and keys == {"_python_type", "_repr"}:
                if not isinstance(value["_python_type"], str):
                    raise JsonValidationError(f"{label}._python_type must be a string.")
                if not isinstance(value["_repr"], str):
                    raise JsonValidationError(f"{label}._repr must be a string.")
                return

            raise JsonValidationError(f"{label} contains invalid marker keys.")

        for key, item in value.items():
            child_path = key if not path else f"{path}.{key}"
            validate_json_markers(item, file_name, child_path, allow_output_markers)

        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            child_path = f"{path}[{index}]"
            validate_json_markers(item, file_name, child_path, allow_output_markers)


def validate_aircraft_json(data):
    """Validate InputAircraft.json before converting it into FAST input data."""

    require_json_object(data, "InputAircraft.json")
    validate_json_markers(data, "InputAircraft.json")
    validate_json_structure_contract(
        data,
        read_contract_structure(INPUT_AIRCRAFT_STRUCTURE_JSON_PATH),
        "InputAircraft.json",
    )

    require_json_string(data, ["Specs", "TLAR", "Class"], "InputAircraft.json")
    require_json_number(data, ["Specs", "TLAR", "MaxPax"], "InputAircraft.json")
    require_json_number(data, ["Specs", "Performance", "Range"], "InputAircraft.json")
    require_json_number(data, ["Specs", "Weight", "MTOW"], "InputAircraft.json")

    get_json_path(data, ["Specs", "Propulsion", "PropArch"], "InputAircraft.json")
    get_json_path(data, ["Settings"], "InputAircraft.json")


def validate_mission_json(data):
    """Validate Mission.json before converting it into FAST input data."""

    require_json_object(data, "Mission.json")
    validate_json_markers(data, "Mission.json")
    validate_json_structure_contract(
        data,
        read_contract_structure(MISSION_STRUCTURE_JSON_PATH),
        "Mission.json",
    )

    targets = require_json_list_or_scalar_list(
        data,
        ["Target", "Valu"],
        "Mission.json",
    )
    target_types = require_json_list_or_scalar_list(
        data,
        ["Target", "Type"],
        "Mission.json",
    )

    if len(targets) != len(target_types):
        raise JsonValidationError(
            "Mission.json Target.Valu and Target.Type must have the same length."
        )

    for index, target_type in enumerate(target_types):
        if target_type not in ("Dist", "Time"):
            raise JsonValidationError(
                f"Mission.json Target.Type[{index}] must be \"Dist\" or \"Time\"."
            )

    segment_fields = [
        "Segs",
        "ID",
        "AltBeg",
        "AltEnd",
        "VelBeg",
        "VelEnd",
        "TypeBeg",
        "TypeEnd",
        "ClbRate",
    ]
    segment_lengths = {}

    for field_name in segment_fields:
        segment_lengths[field_name] = len(
            require_json_list(data, [field_name], "Mission.json")
        )

    expected_length = segment_lengths["Segs"]

    for field_name, length in segment_lengths.items():
        if length != expected_length:
            raise JsonValidationError(
                "Mission.json segment arrays must have the same length: "
                f"Segs has {expected_length}, {field_name} has {length}."
            )

    for index, segment_name in enumerate(data["Segs"]):
        if not isinstance(segment_name, str):
            raise JsonValidationError(f"Mission.json Segs[{index}] must be a string.")


def validate_output_aircraft_json(data):
    """Validate OutputAircraft.json after writing FAST output data."""

    require_json_object(data, "OutputAircraft.json")
    validate_json_markers(data, "OutputAircraft.json", allow_output_markers=True)
    validate_json_structure_contract(
        data,
        read_contract_structure(OUTPUT_AIRCRAFT_STRUCTURE_JSON_PATH),
        "OutputAircraft.json",
    )

    require_json_number(data, ["Specs", "Weight", "MTOW"], "OutputAircraft.json")
    require_json_number(data, ["Specs", "Weight", "Fuel"], "OutputAircraft.json")
    require_json_number(data, ["Specs", "Aero", "S"], "OutputAircraft.json")
    require_json_string(data, ["Specs", "TLAR", "Class"], "OutputAircraft.json")
    get_json_path(data, ["Mission", "Profile"], "OutputAircraft.json")


def validate_output_structure_json(data):
    """Validate OutputAircraftStructure.json after writing structure data."""

    require_json_object(data, "OutputAircraftStructure.json")

    for field_name in ("Specs", "Mission"):
        if field_name not in data:
            raise JsonValidationError(
                f"OutputAircraftStructure.json is missing required field {field_name}."
            )


def read_json_file(path, validator=None):
    """Read and validate a JSON file, then restore FAST marker values.

    Inputs:
        path: InputAircraft.json or Mission.json path.
        validator: Optional validator function for the parsed JSON value.

    Outputs:
        Wrapper-ready Python data.

    Side effects:
        None.
    """

    data = read_raw_json_file(path)

    if validator:
        validator(data)

    return load_json_data(data)


def require_input_json_file(path):
    """Fail when a required FAST JSON input file is missing.

    Inputs:
        path: Required input JSON path.

    Outputs:
        None.

    Assumptions:
        InputAircraft.json and Mission.json are committed/template input files
        that users edit before running main.py.
    """

    if not path.exists():
        raise JsonValidationError(
            f"{path} is required. Edit or restore this input file, then rerun "
            "python main.py."
        )


def load_input_json_files(input_dir=None):
    """Load FAST aircraft and mission inputs from JSON files.

    Inputs:
        input_dir: Directory containing InputAircraft.json and Mission.json. A
            missing value uses the default inputs directory.

    Outputs:
        A tuple of aircraft and mission dictionaries ready for FastWrapper.run().

    Side effects:
        None.
    """

    aircraft_json_path, mission_json_path = build_input_json_paths(input_dir)

    require_input_json_file(aircraft_json_path)
    require_input_json_file(mission_json_path)

    return (
        read_json_file(aircraft_json_path, validate_aircraft_json),
        read_json_file(mission_json_path, validate_mission_json),
    )


def build_output_aircraft_structure(value):
    """Return a recursive structure map for a FAST output value.

    Inputs:
        value: Python data converted from the MATLAB OutputAircraft struct.

    Outputs:
        Nested dictionaries that preserve struct field names. Lists include
        their length and the shape of the first item; scalar leaves show their
        Python type.

    Assumptions:
        FAST arrays are usually homogeneous, so the first list item is enough
        to show the useful structure without duplicating every mission point.
    """

    if isinstance(value, dict):
        return {
            key: build_output_aircraft_structure(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        item_structure = None

        if value:
            item_structure = build_output_aircraft_structure(value[0])

        return {
            "_type": "list",
            "_length": len(value),
            "_items": item_structure,
        }

    return type(value).__name__


def save_output_aircraft(value, output_dir=None):
    """Write the FAST OutputAircraft result to JSON.

    Inputs:
        value: Python dictionary converted from the MATLAB OutputAircraft
            struct returned by FAST.
        output_dir: Directory where OutputAircraft.json should be written. A
            missing value uses the default outputs directory.

    Outputs:
        Destination path written.

    Side effects:
        Creates the output directory when needed and rewrites
        OutputAircraft.json after each successful FAST run.
    """

    output_aircraft_path, _ = build_output_json_paths(output_dir)
    output_aircraft_path.parent.mkdir(parents=True, exist_ok=True)

    write_json_file(output_aircraft_path, build_json_data(value))
    validate_output_aircraft_json(read_raw_json_file(output_aircraft_path))
    return output_aircraft_path


def save_output_aircraft_structure(value, output_dir=None):
    """Write the complete OutputAircraft structure map to JSON.

    Inputs:
        value: Structure map from build_output_aircraft_structure().
        output_dir: Directory where OutputAircraftStructure.json should be
            written. A missing value uses the default outputs directory.

    Outputs:
        Destination path written.

    Side effects:
        Creates the output directory when needed and rewrites the generated JSON
        structure file. The file contains schema-like output only, not the full
        FAST numeric data.
    """

    _, output_structure_path = build_output_json_paths(output_dir)
    output_structure_path.parent.mkdir(parents=True, exist_ok=True)

    write_json_file(output_structure_path, value)
    validate_output_structure_json(read_raw_json_file(output_structure_path))
    return output_structure_path


def print_output_aircraft_structure(
    value,
    name="OutputAircraft",
    indent=0,
    depth=0,
    max_depth=None,
    max_items=None,
):
    """Print the recursive OutputAircraft structure tree.

    Inputs:
        value: Structure map from build_output_aircraft_structure().
        name: Current field label to print.
        indent: Number of leading spaces for nested fields.
        depth: Current recursion depth.
        max_depth: Optional maximum recursion depth for console output.
        max_items: Optional maximum fields printed per dictionary.

    Outputs:
        None. The tree is printed to standard output.

    Side effects:
        Writes a compact structure view to the console for interactive runs.
    """

    prefix = " " * indent

    if max_depth is not None and depth >= max_depth:
        if isinstance(value, dict) and value.get("_type") == "list":
            print(f"{prefix}{name}: list[{value['_length']}] ...")
        elif isinstance(value, dict):
            print(f"{prefix}{name}: dict ...")
        else:
            print(f"{prefix}{name}: {value}")

        return

    if isinstance(value, dict) and value.get("_type") == "list":
        print(f"{prefix}{name}: list[{value['_length']}]")

        if value["_items"] is not None:
            print_output_aircraft_structure(
                value["_items"],
                "[0]",
                indent + 2,
                depth + 1,
                max_depth,
                max_items,
            )

        return

    if isinstance(value, dict):
        print(f"{prefix}{name}: dict")

        items = list(value.items())

        if max_items is None:
            printed_items = items
        else:
            printed_items = items[:max_items]

        for key, item in printed_items:
            print_output_aircraft_structure(
                item,
                key,
                indent + 2,
                depth + 1,
                max_depth,
                max_items,
            )

        if max_items is not None and len(items) > max_items:
            remaining = len(items) - max_items
            print(f"{prefix}  ... {remaining} more fields in JSON file")

        return

    print(f"{prefix}{name}: {value}")
