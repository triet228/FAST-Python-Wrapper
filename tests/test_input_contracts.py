# tests/test_input_contracts.py

"""Check committed input JSON files against structure contracts."""

from copy import deepcopy

import pytest

from helper import (
    JsonValidationError,
    build_json_data,
    read_raw_json_file,
    validate_aircraft_json,
    validate_mission_json,
    validate_output_aircraft_json,
)
from tests.helpers import PROJECT_ROOT


DEFAULT_INPUT_DIR = PROJECT_ROOT / "examples" / "CeRAS" / "inputs"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
REQUIRED_NAN_REJECT_PATHS = {
    "InputAircraft.json": {
        "Specs.Performance.Range",
        "Specs.Performance.Vels.Type",
        "Specs.Propulsion.PropArch",
        "Specs.Propulsion.PropArch.Type",
        "Specs.TLAR.Class",
        "Specs.TLAR.MaxPax",
    },
    "Mission.json": {
        "Segs[]",
        "Target.Type",
        "Target.Type[]",
        "Target.Valu",
        "Target.Valu[]",
        "TypeBeg[]",
        "TypeEnd[]",
    },
}


def iter_leaf_paths(value, path=()):
    """Yield every scalar path in a nested JSON-compatible value."""

    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_leaf_paths(item, path + (key,))
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_leaf_paths(item, path + (index,))
        return

    yield path, value


def set_nested_path(data, path, value):
    """Replace a nested value in copied JSON fixture data."""

    item = data

    for key in path[:-1]:
        item = item[key]

    item[path[-1]] = value


def format_leaf_path(path):
    """Return a stable dotted path for scalar fields and array entries."""

    parts = []

    for item in path:
        if isinstance(item, int):
            parts[-1] = parts[-1] + "[]"
        else:
            parts.append(item)

    return ".".join(parts)


def is_nan_marker_candidate(value):
    """Return True when a scalar uses a type that may carry a NaN marker."""

    if value == "NaN":
        return True

    if isinstance(value, bool):
        return True

    if (isinstance(value, int) or isinstance(value, float)) and not isinstance(
        value,
        bool,
    ):
        return True

    return isinstance(value, dict) and set(value) == {"_matlab_expression"}


def test_input_aircraft_matches_structure_contract():
    """Validate the default aircraft input template contract."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")

    validate_aircraft_json(data)


@pytest.mark.parametrize("case_name", ["A320", "AEA", "ATR42", "CeRAS"])
def test_example_input_aircraft_matches_structure_contract(case_name):
    """Validate each example aircraft input against the full field catalog."""

    data = read_raw_json_file(
        EXAMPLES_DIR / case_name / "inputs" / "InputAircraft.json"
    )

    validate_aircraft_json(data)


def test_mission_matches_structure_contract():
    """Validate the default mission input template contract."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "Mission.json")

    validate_mission_json(data)


@pytest.mark.parametrize("case_name", ["A320", "AEA", "ATR42", "CeRAS"])
def test_example_mission_matches_structure_contract(case_name):
    """Validate each example mission against the full field catalog."""

    data = read_raw_json_file(EXAMPLES_DIR / case_name / "inputs" / "Mission.json")

    validate_mission_json(data)


@pytest.mark.parametrize("case_name", ["A320", "AEA", "ATR42", "CeRAS"])
def test_example_output_aircraft_matches_structure_contract(case_name):
    """Validate each example aircraft output against the full field catalog."""

    data = read_raw_json_file(EXAMPLES_DIR / case_name / "outputs" / "OutputAircraft.json")

    validate_output_aircraft_json(data)


def test_output_object_repr_omits_memory_address():
    """Keep generated opaque object markers stable across Python processes."""

    data = build_json_data(object())

    assert " at 0x" not in data["_repr"]


def test_input_aircraft_contract_rejects_unexpected_field():
    """Reject aircraft inputs that drift outside the committed contract."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Unexpected"] = {}

    with pytest.raises(JsonValidationError, match="unexpected field"):
        validate_aircraft_json(changed)


def test_input_aircraft_contract_allows_missing_optional_field():
    """Allow omitted optional fields that are known in the contract."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    del changed["Settings"]["Table"]

    validate_aircraft_json(changed)


def test_input_aircraft_contract_allows_optional_nan_field():
    """Allow optional known fields to use the FAST unspecified marker."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Settings"]["Table"] = "NaN"

    validate_aircraft_json(changed)


def test_input_aircraft_contract_allows_mtow_nan_field():
    """Allow input MTOW to use the FAST unspecified marker."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Weight"]["MTOW"] = "NaN"

    validate_aircraft_json(changed)


def test_input_aircraft_contract_rejects_missing_mtow_field():
    """Require the MTOW key even when FAST is allowed to size the value."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    del changed["Specs"]["Weight"]["MTOW"]

    with pytest.raises(JsonValidationError, match="missing required field MTOW"):
        validate_aircraft_json(changed)


def test_mission_contract_rejects_missing_field():
    """Reject mission inputs that omit a committed contract field."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "Mission.json")
    changed = deepcopy(data)
    del changed["VelEnd"]

    with pytest.raises(JsonValidationError, match="missing required field"):
        validate_mission_json(changed)


@pytest.mark.parametrize(
    ("file_name", "validator"),
    [
        ("InputAircraft.json", validate_aircraft_json),
        ("Mission.json", validate_mission_json),
    ],
)
def test_fast_input_nan_marker_candidates_accept_nan(file_name, validator):
    """Guard required and optional FAST input NaN marker behavior."""

    unexpected_accepts = []
    unexpected_rejects = []
    checked_paths = set()
    required_reject_paths = REQUIRED_NAN_REJECT_PATHS[file_name]

    for case_dir in sorted(EXAMPLES_DIR.iterdir()):
        data = read_raw_json_file(case_dir / "inputs" / file_name)

        for leaf_path, value in iter_leaf_paths(data):
            label = format_leaf_path(leaf_path)

            if label not in required_reject_paths and not is_nan_marker_candidate(value):
                continue

            changed = deepcopy(data)
            set_nested_path(changed, leaf_path, "NaN")

            try:
                validator(changed)
            except JsonValidationError as error:
                if label not in required_reject_paths:
                    unexpected_rejects.append(f"{case_dir.name} {label}: {error}")
            else:
                if label in required_reject_paths:
                    unexpected_accepts.append(f"{case_dir.name} {label}")

            checked_paths.add(label)

    assert checked_paths
    assert required_reject_paths <= checked_paths
    assert not unexpected_accepts
    assert not unexpected_rejects
