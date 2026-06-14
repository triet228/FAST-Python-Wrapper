# core/output_structure.py

from .json_io import build_json_data
from .schema_contract import (
    apply_prop_arch_schema_contract,
    build_json_schema_from_value,
    is_json_schema_document,
)


def build_output_aircraft_structure(value):
    """Return a JSON Schema document for a FAST output value.

    Inputs:
        value: Python data converted from the MATLAB OutputAircraft struct.

    Outputs:
        Draft 2020-12 JSON Schema document that preserves struct field names
        and JSON value shapes.

    Assumptions:
        FAST output array lengths vary by aircraft and mission, so the schema
        validates item shape without locking one example's exact lengths.
        PropArch is post-processed to the public C/E contract even when FAST
        returns internal architecture expansion fields.
    """

    schema = {
        "title": "FAST Output Aircraft Schema",
        "description": "Schema for FAST output aircraft.",
    }
    schema.update(
        build_json_schema_from_value(
            build_json_data(value),
            require_properties=True,
            require_lengths=False,
        )
    )
    return apply_prop_arch_schema_contract(schema)


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
        if isinstance(value, dict) and value.get("type") == "array":
            length = ""

            if (
                value.get("minItems") == value.get("maxItems")
                and "minItems" in value
            ):
                length = str(value["minItems"])

            if length:
                print(f"{prefix}{name}: array[{length}] ...")
            else:
                print(f"{prefix}{name}: array ...")
        elif isinstance(value, dict):
            print(f"{prefix}{name}: object ...")
        else:
            print(f"{prefix}{name}: {value}")

        return

    if isinstance(value, dict) and value.get("type") == "array":
        length = ""

        if (
            value.get("minItems") == value.get("maxItems")
            and "minItems" in value
        ):
            length = str(value["minItems"])

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

    if isinstance(value, dict) and value.get("type") == "object":
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
