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


def test_input_aircraft_contract_rejects_required_nan_field():
    """Reject required fields that use the FAST unspecified marker."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Weight"]["MTOW"] = "NaN"

    with pytest.raises(JsonValidationError, match="required|must be a number"):
        validate_aircraft_json(changed)


def test_mission_contract_rejects_missing_field():
    """Reject mission inputs that omit a committed contract field."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "Mission.json")
    changed = deepcopy(data)
    del changed["VelEnd"]

    with pytest.raises(JsonValidationError, match="missing required field"):
        validate_mission_json(changed)
