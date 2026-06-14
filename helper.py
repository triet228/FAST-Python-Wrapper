# helper.py

import json
import re
from pathlib import Path

from wrapper import MatlabExpression, MatlabRow


# FAST unspecified input marker.
nan = float("nan")

# Default example run directories and file names. InputAircraft.json is the
# single required run input; the OutputAircraft files are regenerated after
# each successful FAST run.
DEFAULT_INPUT_DIR = Path("examples/CeRAS/inputs")
DEFAULT_OUTPUT_DIR = Path("examples/CeRAS/outputs")
CONTRACTS_DIR = Path("contracts")
AIRCRAFT_JSON_PATH = Path("InputAircraft.json")
INPUT_AIRCRAFT_SCHEMA_JSON_PATH = Path("InputAircraftSchema.json")
OUTPUT_AIRCRAFT_JSON_PATH = Path("OutputAircraft.json")
OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH = Path("OutputAircraftSchema.json")


class JsonValidationError(ValueError):
    """Report an invalid FAST JSON input or output file."""


def build_input_json_paths(input_dir=None):
    """Return the aircraft input path for a FAST run.

    Inputs:
        input_dir: Directory containing InputAircraft.json. A missing value
            uses the default inputs directory.

    Outputs:
        The aircraft JSON path.

    Assumptions:
        FAST run inputs are grouped in one directory so callers can run several
        cases without renaming files in the project root.
    """

    if input_dir is None:
        base_path = DEFAULT_INPUT_DIR
    else:
        base_path = Path(input_dir)

    return base_path / AIRCRAFT_JSON_PATH


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
        base_path / OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    )


def print_result(result):
    """Print a cleaned FAST command-window log.

    Inputs:
        result: Metadata dictionary from FastWrapper.run_with_metadata(),
            optionally containing a MATLAB command-window log under the "log"
            key.

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


def round_json_numbers(value):
    """Return JSON-compatible data with floating point numbers rounded."""

    if isinstance(value, dict):
        return {
            key: round_json_numbers(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [round_json_numbers(item) for item in value]

    if isinstance(value, bool) or isinstance(value, int):
        return value

    if isinstance(value, float):
        return round(value, 4)

    return value


def load_json_data(value):
    """Convert JSON FAST input data back into wrapper-ready Python data.

    Inputs:
        value: Data loaded from InputAircraft.json.

    Outputs:
        Python data accepted by FastWrapper.run(), including restored MATLAB
        expressions, MATLAB row-vector markers, and NaN values.

    Assumptions:
        The JSON files use the marker objects generated by build_json_data().
        Plain string "NaN" and JSON null are treated as the FAST unspecified
        input marker.
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

    if value is None:
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
        json.dumps(round_json_numbers(value), indent=2) + "\n",
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


def build_json_schema_defs():
    """Return reusable JSON Schema definitions for wrapper marker objects."""

    return {
        "matlabExpression": json_schema_matlab_expression(),
        "pythonMarker": json_schema_python_marker(),
        "numberOrExpression": {
            "anyOf": [
                {
                    "type": "number",
                },
                json_schema_matlab_expression(),
            ],
        },
        "optionalNumber": {
            "anyOf": [
                json_schema_number(),
                {
                    "const": "NaN",
                },
            ],
        },
        "optionalBoolean": {
            "anyOf": [
                {
                    "type": "boolean",
                },
                {
                    "const": "NaN",
                },
            ],
        },
        "optionalMatlabExpression": {
            "anyOf": [
                json_schema_matlab_expression(),
                {
                    "const": "NaN",
                },
            ],
        },
        "optionalPythonMarker": {
            "anyOf": [
                json_schema_python_marker(),
                {
                    "const": "NaN",
                },
            ],
        },
    }


def json_schema_matlab_expression():
    """Return the inline schema for a MATLAB expression marker."""

    return {
        "type": "object",
        "properties": {
            "_matlab_expression": {
                "type": "string",
            },
        },
        "required": [
            "_matlab_expression",
        ],
        "additionalProperties": False,
    }


def json_schema_python_marker():
    """Return the inline schema for an opaque Python output marker."""

    return {
        "type": "object",
        "properties": {
            "_python_type": {
                "type": "string",
            },
            "_repr": {
                "type": "string",
            },
        },
        "required": [
            "_python_type",
            "_repr",
        ],
        "additionalProperties": False,
    }


def build_json_schema_document(schema, title, description=None):
    """Wrap a JSON Schema subtree in the project schema file format."""

    document = {
        "title": title,
    }

    if description is not None:
        document["description"] = description

    document.update(schema)
    return document


def json_schema_number():
    """Return the FAST numeric schema, including MATLAB expressions."""

    return {
        "anyOf": [
            {
                "type": "number",
            },
            json_schema_matlab_expression(),
        ],
    }


def json_schema_may_be_nan(schema):
    """Return a schema that also allows FAST's optional NaN marker."""

    if schema == {"type": "string"}:
        return schema

    if set(schema.keys()) == {"anyOf"}:
        return {
            "anyOf": schema["anyOf"] + [
                {
                    "const": "NaN",
                },
            ],
        }

    return {
        "anyOf": [
            schema,
            {
                "const": "NaN",
            },
        ],
    }


def json_schema_required_value(schema):
    """Return a schema that rejects FAST's NaN marker for required values."""

    if not json_schema_allows_nan_string(schema):
        return schema

    required_schema = dict(schema)
    required_schema["not"] = {
        "const": "NaN",
    }
    return required_schema


def json_schema_allows_nan_string(schema):
    """Return True when a required schema could otherwise accept string NaN."""

    if schema.get("type") == "string":
        return True

    if "anyOf" in schema:
        return any(json_schema_allows_nan_string(option) for option in schema["anyOf"])

    return False


def build_json_schema_from_value(
    value,
    require_properties=False,
    require_lengths=False,
    allow_output_markers=False,
):
    """Infer a JSON Schema subtree from a JSON-safe FAST value.

    Inputs:
        value: Parsed or generated JSON value.
        require_properties: Whether object properties present in value should be
            listed as required in the schema.
        require_lengths: Whether observed list lengths should become minItems
            and maxItems constraints.
        allow_output_markers: Whether output-only Python marker objects are
            expected.

    Outputs:
        A JSON Schema subtree using standard Draft 2020-12 keywords.

    Assumptions:
        FAST arrays are homogeneous enough that the first item describes the
        useful item schema. The string "NaN" is treated as FAST's numeric
        unspecified marker, matching load_json_data().
    """

    if isinstance(value, dict):
        keys = set(value.keys())

        if keys == {"_matlab_expression"}:
            return json_schema_matlab_expression()

        if keys == {"_matlab_row"}:
            row_schema = {
                "type": "array",
            }

            if isinstance(value["_matlab_row"], list):
                row_schema = build_json_schema_from_value(
                    value["_matlab_row"],
                    require_properties,
                    require_lengths,
                    allow_output_markers,
                )

            return {
                "type": "object",
                "properties": {
                    "_matlab_row": row_schema,
                },
                "required": [
                    "_matlab_row",
                ],
                "additionalProperties": False,
            }

        if allow_output_markers and keys == {"_python_type", "_repr"}:
            return json_schema_python_marker()

        properties = {
            key: build_json_schema_from_value(
                item,
                require_properties,
                require_lengths,
                allow_output_markers,
            )
            for key, item in value.items()
        }
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }

        if require_properties and properties:
            schema["required"] = list(properties)

        return schema

    if isinstance(value, list):
        schema = {
            "type": "array",
        }

        if require_lengths:
            schema["minItems"] = len(value)
            schema["maxItems"] = len(value)

        if value:
            schema["items"] = build_json_schema_from_value(
                value[0],
                require_properties,
                require_lengths,
                allow_output_markers,
            )

        return schema

    if isinstance(value, bool):
        return {
            "type": "boolean",
        }

    if is_json_number(value):
        return json_schema_number()

    if value == "NaN":
        return {
            "const": "NaN",
        }

    if isinstance(value, str):
        return {
            "type": "string",
        }

    if value is None:
        return {
            "type": "null",
        }

    return {
        "type": "string",
    }


def build_input_json_structure(value):
    """Return a standard JSON Schema document for FAST input JSON data.

    Inputs:
        value: Parsed JSON value from InputAircraft.json.

    Outputs:
        Draft 2020-12 JSON Schema document that preserves field names, broad
        JSON types, marker shapes, and list item schemas.

    Assumptions:
        Generated input schema fields are optional by default. Optional "NaN"
        placeholders are accepted by validation where a committed contract marks
        the field optional.
    """

    return build_json_schema_document(
        build_json_schema_from_value(value),
        "FAST input JSON schema",
        "Schema for FAST input JSON data.",
    )


def convert_contract_to_json_schema(contract, title):
    """Convert the legacy FAST contract format into standard JSON Schema."""

    return build_json_schema_document(
        convert_contract_node_to_json_schema(contract, force_required=True),
        title,
    )


def convert_contract_node_to_json_schema(contract, force_required=None):
    """Convert one legacy type/required/fields node into JSON Schema."""

    node_required = contract.get("required", False)

    if force_required is not None:
        node_required = force_required

    expected_types = contract.get("type")

    if isinstance(expected_types, list):
        schema = {
            "anyOf": [
                convert_contract_type_to_json_schema(contract, expected_type)
                for expected_type in expected_types
            ],
        }
    else:
        schema = convert_contract_type_to_json_schema(contract, expected_types)

    if node_required:
        return json_schema_required_value(schema)

    return json_schema_may_be_nan(schema)


def convert_contract_type_to_json_schema(contract, expected_type):
    """Convert one legacy FAST contract type into a JSON Schema subtree."""

    if expected_type == "object":
        fields = contract.get("fields", {})
        properties = {}
        required = []

        for key, child_contract in fields.items():
            properties[key] = convert_contract_node_to_json_schema(child_contract)

            if child_contract.get("required", False):
                required.append(key)

        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }

        if required:
            schema["required"] = required

        return schema

    if expected_type == "list":
        schema = {
            "type": "array",
        }
        item_contract = contract.get("items")

        if item_contract is not None:
            schema["items"] = convert_contract_node_to_json_schema(item_contract)

        return schema

    if expected_type == "matlab_row":
        row_schema = {
            "type": "array",
        }
        item_contract = contract.get("items")

        if item_contract is not None:
            row_schema = convert_contract_node_to_json_schema(
                item_contract,
                force_required=True,
            )

        return {
            "type": "object",
            "properties": {
                "_matlab_row": row_schema,
            },
            "required": [
                "_matlab_row",
            ],
            "additionalProperties": False,
        }

    if expected_type == "matlab_expression":
        return json_schema_matlab_expression()

    if expected_type == "python_marker":
        return json_schema_python_marker()

    if expected_type == "number":
        return json_schema_number()

    if expected_type == "string":
        return {
            "type": "string",
        }

    if expected_type == "bool":
        return {
            "type": "boolean",
        }

    if expected_type == "null":
        return {
            "type": "null",
        }

    return {
        "type": "string",
    }


def read_contract_structure(file_name):
    """Read a committed JSON contract from contracts/.

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
    """Validate parsed JSON against a committed structure schema.

    Inputs:
        data: Parsed input JSON subtree.
        contract: JSON Schema document or legacy contract subtree.
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

    if is_json_schema_document(contract):
        validate_json_schema_value(data, contract, file_name, path or file_name, contract)
        return

    validate_contract_value(data, contract, file_name, path or file_name)


def is_json_schema_document(contract):
    """Return True when a contract is a standard JSON Schema document."""

    return (
        isinstance(contract, dict)
        and (
            "$schema" in contract
            or "properties" in contract
            or "anyOf" in contract
            or "const" in contract
        )
    )


def validate_json_schema_value(data, schema, file_name, label, root_schema):
    """Validate one JSON value against the generated JSON Schema subset."""

    if "$ref" in schema:
        validate_json_schema_value(
            data,
            resolve_json_schema_ref(schema["$ref"], root_schema),
            file_name,
            label,
            root_schema,
        )
        schema = {
            key: value
            for key, value in schema.items()
            if key != "$ref"
        }

        if not schema:
            return

    if "not" in schema:
        try:
            validate_json_schema_value(
                data,
                schema["not"],
                file_name,
                label,
                root_schema,
            )
        except JsonValidationError:
            pass
        else:
            if schema["not"].get("const") == "NaN":
                raise JsonValidationError(f"{label} is required and cannot be \"NaN\".")

            raise JsonValidationError(f"{label} must not match excluded schema.")

    if "const" in schema:
        if data != schema["const"]:
            raise JsonValidationError(f"{label} must equal {schema['const']!r}.")

    if "enum" in schema and data not in schema["enum"]:
        allowed = ", ".join(repr(item) for item in schema["enum"])
        raise JsonValidationError(f"{label} must be one of: {allowed}.")

    if "anyOf" in schema:
        errors = []

        for option in schema["anyOf"]:
            try:
                validate_json_schema_value(data, option, file_name, label, root_schema)
                return
            except JsonValidationError as error:
                errors.append(str(error))

        if errors:
            if data == "NaN":
                raise JsonValidationError(f"{label} is required and cannot be \"NaN\".")

            raise JsonValidationError(f"{label} must match at least one allowed schema.")

        raise JsonValidationError(f"{label} has no allowed schema.")

    if "type" not in schema:
        return

    expected_types = schema["type"]

    if isinstance(expected_types, str):
        expected_types = [
            expected_types,
        ]

    errors = []

    for expected_type in expected_types:
        try:
            validate_json_schema_type(
                data,
                schema,
                expected_type,
                file_name,
                label,
                root_schema,
            )
            return
        except JsonValidationError as error:
            errors.append(str(error))

    if len(errors) == 1:
        raise JsonValidationError(errors[0])

    expected = ", ".join(expected_types)
    raise JsonValidationError(f"{label} must match type {expected}.")


def resolve_json_schema_ref(ref, root_schema):
    """Resolve a local JSON Schema reference from the root document."""

    prefix = "#/$defs/"

    if not ref.startswith(prefix):
        raise JsonValidationError(f"Unsupported JSON Schema reference {ref}.")

    key = ref[len(prefix):]

    try:
        return root_schema["$defs"][key]
    except KeyError as error:
        raise JsonValidationError(f"Missing JSON Schema definition {key}.") from error


def validate_json_schema_type(data, schema, expected_type, file_name, label, root_schema):
    """Validate data against one standard JSON Schema type."""

    if expected_type == "object":
        if not isinstance(data, dict):
            raise JsonValidationError(f"{label} must be a JSON object.")

        properties = schema.get("properties", {})
        required = schema.get("required", [])
        actual_keys = set(data)
        expected_keys = set(properties)

        if schema.get("additionalProperties") is False:
            for key in sorted(actual_keys - expected_keys):
                raise JsonValidationError(f"{label} contains unexpected field {key}.")

        for key in required:
            if key not in data:
                raise JsonValidationError(f"{label} is missing required field {key}.")

        for key in sorted(actual_keys & expected_keys):
            validate_json_schema_value(
                data[key],
                properties[key],
                file_name,
                f"{label}.{key}",
                root_schema,
            )

        return

    if expected_type == "array":
        if not isinstance(data, list):
            raise JsonValidationError(f"{label} must be a JSON array.")

        if "minItems" in schema and len(data) < schema["minItems"]:
            raise JsonValidationError(
                f"{label} must contain at least {schema['minItems']} items."
            )

        if "maxItems" in schema and len(data) > schema["maxItems"]:
            raise JsonValidationError(
                f"{label} must contain at most {schema['maxItems']} items."
            )

        item_schema = schema.get("items")

        if item_schema is not None:
            for index, item in enumerate(data):
                validate_json_schema_value(
                    item,
                    item_schema,
                    file_name,
                    f"{label}[{index}]",
                    root_schema,
                )

        return

    if expected_type == "number":
        if is_json_number(data):
            validate_json_schema_number_limits(data, schema, label)
            return

        raise JsonValidationError(f"{label} must be a number.")

    if expected_type == "integer":
        if isinstance(data, int) and not isinstance(data, bool):
            validate_json_schema_number_limits(data, schema, label)
            return

        raise JsonValidationError(f"{label} must be an integer.")

    if expected_type == "string":
        if isinstance(data, str):
            return

        raise JsonValidationError(f"{label} must be a string.")

    if expected_type == "boolean":
        if isinstance(data, bool):
            return

        raise JsonValidationError(f"{label} must be true or false.")

    if expected_type == "null":
        if data is None:
            return

        raise JsonValidationError(f"{label} must be null.")

    raise JsonValidationError(f"{label} uses unknown JSON Schema type {expected_type}.")


def validate_json_schema_number_limits(data, schema, label):
    """Validate minimum and maximum constraints for JSON number schemas."""

    if "minimum" in schema and data < schema["minimum"]:
        raise JsonValidationError(f"{label} must be at least {schema['minimum']}.")

    if "maximum" in schema and data > schema["maximum"]:
        raise JsonValidationError(f"{label} must be at most {schema['maximum']}.")


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


def require_json_number_or_nan(data, keys, file_name):
    """Validate that a required numeric field also accepts FAST's NaN marker."""

    value = get_json_path(data, keys, file_name)

    if value == "NaN":
        return

    require_json_number(data, keys, file_name)


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
        read_contract_structure(INPUT_AIRCRAFT_SCHEMA_JSON_PATH),
        "InputAircraft.json",
    )

    mission_profile = get_json_path(
        data,
        ["Mission", "Profile"],
        "InputAircraft.json",
    )
    validate_mission_profile_json(mission_profile)


def validate_mission_profile_json(data):
    """Validate the Mission.Profile object embedded in InputAircraft.json."""

    require_json_object(data, "InputAircraft.json.Mission.Profile")

    targets = require_json_list_or_scalar_list(
        data,
        ["Target", "Valu"],
        "InputAircraft.json.Mission.Profile",
    )
    target_types = require_json_list_or_scalar_list(
        data,
        ["Target", "Type"],
        "InputAircraft.json.Mission.Profile",
    )

    if len(targets) != len(target_types):
        raise JsonValidationError(
            "InputAircraft.json Mission.Profile Target.Valu and Target.Type "
            "must have the same length."
        )

    for index, target_type in enumerate(target_types):
        if target_type not in ("Dist", "Time"):
            raise JsonValidationError(
                "InputAircraft.json Mission.Profile Target.Type"
                f"[{index}] must be \"Dist\" or \"Time\"."
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
            require_json_list(
                data,
                [field_name],
                "InputAircraft.json.Mission.Profile",
            )
        )

    expected_length = segment_lengths["Segs"]

    for field_name, length in segment_lengths.items():
        if length != expected_length:
            raise JsonValidationError(
                "InputAircraft.json Mission.Profile segment arrays must have "
                "the same length: "
                f"Segs has {expected_length}, {field_name} has {length}."
            )

    for index, segment_name in enumerate(data["Segs"]):
        if not isinstance(segment_name, str):
            raise JsonValidationError(
                "InputAircraft.json Mission.Profile Segs"
                f"[{index}] must be a string."
            )


def validate_output_aircraft_json(data):
    """Validate OutputAircraft.json after writing FAST output data."""

    require_json_object(data, "OutputAircraft.json")
    validate_json_markers(data, "OutputAircraft.json", allow_output_markers=True)
    validate_json_structure_contract(
        data,
        read_contract_structure(OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH),
        "OutputAircraft.json",
    )

    require_json_number(data, ["Specs", "Weight", "MTOW"], "OutputAircraft.json")
    require_json_number(data, ["Specs", "Weight", "Fuel"], "OutputAircraft.json")
    require_json_number(data, ["Specs", "Aero", "S"], "OutputAircraft.json")
    require_json_string(data, ["Specs", "TLAR", "Class"], "OutputAircraft.json")
    get_json_path(data, ["Mission", "Profile"], "OutputAircraft.json")


def validate_output_schema_json(data):
    """Validate OutputAircraftSchema.json after writing structure data."""

    require_json_object(data, "OutputAircraftSchema.json")

    if is_json_schema_document(data):
        properties = data.get("properties", {})

        for field_name in ("Specs", "Mission"):
            if field_name not in properties:
                raise JsonValidationError(
                    "OutputAircraftSchema.json is missing required property "
                    f"{field_name}."
                )

        return

    for field_name in ("Specs", "Mission"):
        if field_name not in data:
            raise JsonValidationError(
                f"OutputAircraftSchema.json is missing required field {field_name}."
            )


def read_json_file(path, validator=None):
    """Read and validate a JSON file, then restore FAST marker values.

    Inputs:
        path: JSON path.
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
        InputAircraft.json is a committed/template input file that users edit
        before running main.py.
    """

    if not path.exists():
        raise JsonValidationError(
            f"{path} is required. Edit or restore this input file, then rerun "
            "python main.py."
        )


def load_input_json_files(input_dir=None):
    """Load the merged FAST aircraft input from JSON.

    Inputs:
        input_dir: Directory containing InputAircraft.json. A missing value uses
            the default inputs directory.

    Outputs:
        Aircraft dictionary ready for FastWrapper.run().

    Side effects:
        None.
    """

    aircraft_json_path = build_input_json_paths(input_dir)

    require_input_json_file(aircraft_json_path)

    return read_json_file(aircraft_json_path, validate_aircraft_json)


def load_input_aircraft_json(input_dir=None):
    """Load the merged FAST aircraft input from InputAircraft.json."""

    return load_input_json_files(input_dir)


def build_output_aircraft_structure(value):
    """Return a JSON Schema document for a FAST output value.

    Inputs:
        value: Python data converted from the MATLAB OutputAircraft struct.

    Outputs:
        Draft 2020-12 JSON Schema document that preserves struct field names,
        marker object shapes, and observed list lengths.

    Assumptions:
        FAST arrays are usually homogeneous, so the first list item is enough
        to show the useful item schema without duplicating every mission point.
    """

    return build_json_schema_document(
        build_json_schema_from_value(
            build_json_data(value),
            require_properties=True,
            require_lengths=True,
            allow_output_markers=True,
        ),
        "FAST Output Aircraft Schema",
        "Schema for FAST output aircraft.",
    )


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
    """Write the complete OutputAircraft schema to JSON.

    Inputs:
        value: Structure map from build_output_aircraft_structure().
        output_dir: Directory where OutputAircraftSchema.json should be
            written. A missing value uses the default outputs directory.

    Outputs:
        Destination path written.

    Side effects:
        Creates the output directory when needed and rewrites the generated JSON
        schema file. The file contains schema-like output only, not the full
        FAST numeric data.
    """

    _, output_structure_path = build_output_json_paths(output_dir)
    output_structure_path.parent.mkdir(parents=True, exist_ok=True)

    write_json_file(output_structure_path, value)
    validate_output_schema_json(read_raw_json_file(output_structure_path))
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
        value: JSON Schema document from build_output_aircraft_structure().
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

    if is_json_schema_document(value):
        value = {
            key: item
            for key, item in value.items()
            if key not in ("$schema", "$defs", "title", "description")
        }

    value = unwrap_printable_schema(value)
    prefix = " " * indent

    if max_depth is not None and depth >= max_depth:
        if is_array_schema(value):
            length = format_schema_array_length(value)

            if length:
                print(f"{prefix}{name}: array[{length}] ...")
            else:
                print(f"{prefix}{name}: array ...")
        elif isinstance(value, dict):
            print(f"{prefix}{name}: object ...")
        else:
            print(f"{prefix}{name}: {value}")

        return

    if is_array_schema(value):
        length = format_schema_array_length(value)

        if length:
            print(f"{prefix}{name}: array[{length}]")
        else:
            print(f"{prefix}{name}: array")

        if "items" in value:
            print_output_aircraft_structure(
                value["items"],
                "[0]",
                indent + 2,
                depth + 1,
                max_depth,
                max_items,
            )

        return

    if is_object_schema(value):
        print(f"{prefix}{name}: object")

        properties = value.get("properties", {})
        items = list(properties.items())

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
            print(f"{prefix}  ... {remaining} more fields in JSON schema")

        return

    if isinstance(value, dict):
        print(f"{prefix}{name}: object")

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


def unwrap_printable_schema(value):
    """Return the most useful branch of a schema for structure printing."""

    if not isinstance(value, dict):
        return value

    if "anyOf" in value and value["anyOf"]:
        for option in value["anyOf"]:
            if option.get("const") != "NaN":
                return unwrap_printable_schema(option)

    if "$ref" in value:
        return value["$ref"].split("/")[-1]

    return value


def is_array_schema(value):
    """Return True when a printable schema describes a JSON array."""

    return isinstance(value, dict) and value.get("type") == "array"


def is_object_schema(value):
    """Return True when a printable schema describes a JSON object."""

    return isinstance(value, dict) and value.get("type") == "object"


def format_schema_array_length(value):
    """Return an exact array length string when the schema has one."""

    if value.get("minItems") == value.get("maxItems") and "minItems" in value:
        return str(value["minItems"])

    return ""
