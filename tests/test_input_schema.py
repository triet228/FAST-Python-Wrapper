# tests/test_input_schema.py

"""Check committed JSON files against the merged aircraft schemas."""

from copy import deepcopy

import pytest

from core.json_io import (
    JsonValidationError,
    build_json_data,
    read_raw_json_file,
)
from core.schema_validation import (
    validate_aircraft_json,
    validate_output_aircraft_json,
)
from tests.helpers import PROJECT_ROOT


DEFAULT_INPUT_DIR = PROJECT_ROOT / "examples" / "CeRAS"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
CASE_NAMES = ["A320", "AEA", "ATR42", "CeRAS"]


def test_input_aircraft_matches_schema_contract():
    """Validate the default merged aircraft input template contract."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")

    validate_aircraft_json(data)


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_example_input_aircraft_matches_schema_contract(case_name):
    """Validate each example aircraft input against the merged schema."""

    data = read_raw_json_file(
        EXAMPLES_DIR / case_name / "InputAircraft.json"
    )

    validate_aircraft_json(data)


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_example_cases_do_not_have_standalone_mission_files(case_name):
    """Keep mission data embedded under InputAircraft.json Mission.Profile."""

    input_dir = EXAMPLES_DIR / case_name

    assert not list(input_dir.glob("*Mission*.json"))


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_example_output_aircraft_matches_schema_contract(case_name):
    """Validate each example aircraft output against the output schema."""

    data = read_raw_json_file(EXAMPLES_DIR / case_name / "OutputAircraft.json")

    validate_output_aircraft_json(data)


def test_json_data_omits_object_memory_address():
    """Keep generated opaque object strings stable across Python processes."""

    data = build_json_data(object())

    assert " at 0x" not in data


def test_json_data_serializes_nonfinite_numbers_as_strings():
    """Write non-finite FAST numbers as portable JSON string markers."""

    data = build_json_data(
        [
            float("nan"),
            float("inf"),
            -float("inf"),
        ]
    )

    assert data == [
        "NaN",
        "Inf",
        "-Inf",
    ]


def test_input_aircraft_contract_rejects_unexpected_field():
    """Reject aircraft inputs that drift outside the committed schema."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Unexpected"] = {}

    with pytest.raises(JsonValidationError, match="unexpected field"):
        validate_aircraft_json(changed)


def test_input_aircraft_contract_rejects_unsupported_prop_arch():
    """Keep supported propulsion architectures limited to C and E."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Propulsion"]["PropArch"]["Type"] = "Unsupported"

    with pytest.raises(JsonValidationError, match="PropArch.Type"):
        validate_aircraft_json(changed)


def test_input_aircraft_contract_allows_missing_optional_field():
    """Allow omitted optional fields that are known in the schema."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    del changed["Settings"]["Table"]

    validate_aircraft_json(changed)


def test_input_aircraft_contract_rejects_missing_mission_profile():
    """Require mission data to live inside InputAircraft.json."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    del changed["Mission"]["Profile"]

    with pytest.raises(JsonValidationError, match="Mission.Profile"):
        validate_aircraft_json(changed)


def test_input_aircraft_contract_rejects_legacy_nan_marker():
    """Reject standalone input NaN marker strings at schema-defined fields."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Mission"]["Profile"]["ClbRate"][0] = "NaN"

    with pytest.raises(JsonValidationError, match="ClbRate"):
        validate_aircraft_json(changed)


def test_mission_profile_contract_rejects_mismatched_target_lengths():
    """Reject mission profiles whose target values and types do not align."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Mission"]["Profile"]["Target"]["Type"].append("Dist")

    with pytest.raises(JsonValidationError, match="same length"):
        validate_aircraft_json(changed)


def test_mission_profile_contract_rejects_missing_segment_field():
    """Reject mission profiles that omit a committed segment array."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    del changed["Mission"]["Profile"]["VelEnd"]

    with pytest.raises(JsonValidationError, match="missing required field VelEnd"):
        validate_aircraft_json(changed)
