# core/schema_contract.py

import json

from .json_io import (
    INPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    JsonValidationError,
    OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    SCHEMA_DIR,
    get_json_path,
    is_json_number,
    read_raw_json_file,
    require_json_object,
)
from .aircraft_contract import PROP_ARCH_TYPES


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


def json_schema_number():
    """Return the FAST numeric schema, including MATLAB expression markers.

    Assumptions:
        Input templates can still contain trusted MATLAB expressions for values
        defined by FAST packages, so numeric fields accept either JSON numbers
        or the explicit marker object.
    """

    return {
        "anyOf": [
            {
                "type": "number",
            },
            json_schema_matlab_expression(),
        ],
    }


def json_schema_prop_arch():
    """Return the supported propulsion architecture schema.

    Assumptions:
        The Python wrapper currently supports only public FAST architecture
        labels C and E. Graph-style architecture details are intentionally
        outside this schema.
    """

    return {
        "type": "object",
        "properties": {
            "Type": {
                "type": "string",
                "enum": list(PROP_ARCH_TYPES),
            },
        },
        "required": [
            "Type",
        ],
        "additionalProperties": False,
    }


def apply_prop_arch_schema_contract(schema):
    """Limit every PropArch schema branch to the supported Type field.

    Inputs:
        schema: Generated JSON Schema dictionary or subtree.

    Outputs:
        The same schema object after in-place normalization.

    Side effects:
        Mutates generated schemas so historical/reference output data cannot
        reintroduce internal PropArch graph fields.
    """

    if isinstance(schema, dict):
        properties = schema.get("properties")

        if isinstance(properties, dict):
            for key, item in list(properties.items()):
                if key == "PropArch":
                    properties[key] = json_schema_prop_arch()
                else:
                    apply_prop_arch_schema_contract(item)

        if "items" in schema:
            apply_prop_arch_schema_contract(schema["items"])

        if "anyOf" in schema:
            for item in schema["anyOf"]:
                apply_prop_arch_schema_contract(item)

    if isinstance(schema, list):
        for item in schema:
            apply_prop_arch_schema_contract(item)

    return schema


def build_json_schema_from_value(
    value,
    require_properties=False,
    require_lengths=False,
):
    """Infer a JSON Schema subtree from a JSON-safe FAST value.

    Inputs:
        value: Parsed or generated JSON value.
        require_properties: Whether object properties present in value should be
            listed as required in the schema.
        require_lengths: Whether observed list lengths should become minItems
            and maxItems constraints.
    Outputs:
        A JSON Schema subtree using standard Draft 2020-12 keywords.

    Assumptions:
        FAST arrays can mix finite values with non-finite string markers, so
        item schemas are merged across observed items. The string "NaN" is
        treated as FAST's numeric unspecified marker, matching load_json_data().
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

        properties = {
            key: build_json_schema_from_value(
                item,
                require_properties,
                require_lengths,
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
            schema["items"] = merge_json_schemas(
                [
                    build_json_schema_from_value(
                        item,
                        require_properties,
                        require_lengths,
                    )
                    for item in value
                ]
            )

        return schema

    if isinstance(value, bool):
        return {
            "type": "boolean",
        }

    if is_json_number(value):
        return json_schema_number()

    if value in ("NaN", "Inf", "-Inf"):
        return {
            "const": value,
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


def merge_json_schemas(schemas):
    """Return one schema accepting each schema in a list.

    Inputs:
        schemas: JSON Schema subtrees inferred from example values.

    Outputs:
        A merged schema that keeps shared object/array structure when possible
        and falls back to anyOf only when the observed shapes truly differ.
    """

    unique_schemas = []
    seen_schemas = set()

    for schema in schemas:
        key = json.dumps(schema, sort_keys=True)

        if key not in seen_schemas:
            unique_schemas.append(schema)
            seen_schemas.add(key)

    if len(unique_schemas) == 1:
        return unique_schemas[0]

    if all(schema.get("type") == "object" for schema in unique_schemas):
        return merge_json_object_schemas(unique_schemas)

    if all(schema.get("type") == "array" for schema in unique_schemas):
        return merge_json_array_schemas(unique_schemas)

    any_of = []

    for schema in unique_schemas:
        if set(schema.keys()) == {"anyOf"}:
            any_of.extend(schema["anyOf"])
        else:
            any_of.append(schema)

    return merge_json_schemas_without_specialization(any_of)


def merge_json_schemas_without_specialization(schemas):
    """Return an anyOf schema without recursively merging schema kinds.

    Assumptions:
        Mixed scalar/container observations should stay explicit so validation
        errors point at the accepted alternatives instead of a guessed shape.
    """

    unique_schemas = []
    seen_schemas = set()

    for schema in schemas:
        key = json.dumps(schema, sort_keys=True)

        if key not in seen_schemas:
            unique_schemas.append(schema)
            seen_schemas.add(key)

    if len(unique_schemas) == 1:
        return unique_schemas[0]

    return {
        "anyOf": unique_schemas,
    }


def merge_json_object_schemas(schemas):
    """Merge object schemas from multiple FAST output examples."""

    property_names = []
    property_name_set = set()
    required_sets = []

    for schema in schemas:
        properties = schema.get("properties", {})

        for key in properties:
            if key not in property_name_set:
                property_names.append(key)
                property_name_set.add(key)

        required_sets.append(set(schema.get("required", [])))

    merged_properties = {}

    for key in property_names:
        child_schemas = [
            schema["properties"][key]
            for schema in schemas
            if key in schema.get("properties", {})
        ]
        merged_properties[key] = merge_json_schemas(child_schemas)

    merged_schema = {
        "type": "object",
        "properties": merged_properties,
        "additionalProperties": False,
    }

    required = [
        key
        for key in property_names
        if required_sets and all(key in required_set for required_set in required_sets)
    ]

    if required:
        merged_schema["required"] = required

    return merged_schema


def merge_json_array_schemas(schemas):
    """Merge array schemas from multiple FAST output examples."""

    item_schemas = [
        schema["items"]
        for schema in schemas
        if "items" in schema
    ]
    merged_schema = {
        "type": "array",
    }

    if item_schemas:
        merged_schema["items"] = merge_json_schemas(item_schemas)

    return merged_schema


def read_schema_file(file_name):
    """Read a committed JSON schema from schema/.

    Inputs:
        file_name: Schema JSON file name.

    Outputs:
        Parsed schema document.

    Side effects:
        None.
    """

    path = SCHEMA_DIR / file_name

    if not path.exists():
        raise JsonValidationError(f"{path} is required for input validation.")

    return read_raw_json_file(path)


def validate_json_schema_document(data, schema, file_name, path=""):
    """Validate parsed JSON against a committed structure schema.

    Inputs:
        data: Parsed input JSON subtree.
        schema: JSON Schema document.
        file_name: Input file label used in validation errors.
        path: Current dotted JSON path.

    Outputs:
        None. Raises JsonValidationError when the input structure drifts from
        the committed schema.

    Assumptions:
        Required fields and optional null placeholders are declared directly in
        the schema files under schema/.
    """

    if not is_json_schema_document(schema):
        raise JsonValidationError(f"{file_name} schema must be a JSON Schema document.")

    validate_json_schema_value(
        data,
        schema,
        file_name,
        path or file_name,
        schema,
    )


def is_json_schema_document(schema):
    """Return True when a value is a standard JSON Schema document."""

    return (
        isinstance(schema, dict)
        and (
            "$schema" in schema
            or "properties" in schema
            or "anyOf" in schema
            or "const" in schema
        )
    )


def validate_json_schema_value(data, schema, file_name, label, root_schema):
    """Validate one JSON value against the generated JSON Schema subset.

    Inputs:
        data: Parsed JSON value being checked.
        schema: Schema subtree for this value.
        file_name: Source file label used in error messages.
        label: Dotted path to the current value.
        root_schema: Full schema document used for local $ref resolution.

    Outputs:
        None. Raises JsonValidationError with the concrete JSON path on drift.

    Assumptions:
        The project generates and consumes a small Draft 2020-12 subset; this
        validator implements only keywords used by the committed schemas.
    """

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


def require_json_number(data, keys, file_name):
    """Validate that a required nested field is numeric or a MATLAB expression.

    Assumptions:
        FAST templates sometimes store package-derived numeric values as
        explicit MATLAB expressions, so validation accepts that marker where a
        number would otherwise be required.
    """

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


def validate_json_markers(value, file_name, path=""):
    """Validate MATLAB marker objects used inside JSON files.

    Inputs:
        value: Parsed JSON subtree.
        file_name: File label used in validation errors.
        path: Current dotted JSON path.

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
                )
                return

            raise JsonValidationError(f"{label} contains invalid marker keys.")

        for key, item in value.items():
            child_path = key if not path else f"{path}.{key}"
            validate_json_markers(item, file_name, child_path)

        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            child_path = f"{path}[{index}]"
            validate_json_markers(item, file_name, child_path)


def validate_aircraft_json(data):
    """Validate InputAircraft.json before converting it into FAST input data."""

    require_json_object(data, "InputAircraft.json")
    validate_json_markers(data, "InputAircraft.json")
    validate_json_schema_document(
        data,
        read_schema_file(INPUT_AIRCRAFT_SCHEMA_JSON_PATH),
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

    targets = get_json_path(
        data,
        ["Target", "Valu"],
        "InputAircraft.json.Mission.Profile",
    )
    target_types = get_json_path(
        data,
        ["Target", "Type"],
        "InputAircraft.json.Mission.Profile",
    )

    if not isinstance(targets, list):
        targets = [targets]

    if not isinstance(target_types, list):
        target_types = [target_types]

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
    validate_json_markers(data, "OutputAircraft.json")
    validate_json_schema_document(
        data,
        read_schema_file(OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH),
        "OutputAircraft.json",
    )

    require_json_number(data, ["Specs", "Weight", "MTOW"], "OutputAircraft.json")
    require_json_number(data, ["Specs", "Weight", "Fuel"], "OutputAircraft.json")
    require_json_number(data, ["Specs", "Aero", "S"], "OutputAircraft.json")
    require_json_string(data, ["Specs", "TLAR", "Class"], "OutputAircraft.json")
    get_json_path(data, ["Mission", "Profile"], "OutputAircraft.json")
