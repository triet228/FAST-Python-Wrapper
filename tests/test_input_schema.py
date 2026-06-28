# tests/test_input_schema.py

"""Check committed JSON files against the merged aircraft schemas."""

from copy import deepcopy

import pytest

from core.aircraft_contract import prepare_aircraft
from core.json_io import (
    INPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    JsonValidationError,
    build_json_data,
    read_raw_json_file,
)
from core.matlab_bridge import python_to_matlab
from core.schema_validation import (
    read_schema_file,
    validate_aircraft_json,
    validate_json_schema_document,
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
    """Reject propulsion architecture labels outside the wrapper contract."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Propulsion"]["PropArch"]["Type"] = "Unsupported"

    with pytest.raises(JsonValidationError, match="PropArch"):
        validate_aircraft_json(changed)


@pytest.mark.parametrize("arch_type", ["C", "E", "PHE", "SHE", "TE", "PE"])
def test_input_aircraft_contract_accepts_fast_preset_prop_arch(arch_type):
    """Accept every preset propulsion architecture implemented by FAST."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Propulsion"]["PropArch"]["Type"] = arch_type

    validate_aircraft_json(changed)


@pytest.mark.parametrize("arch_type", ["phe", "she", "te", "pe"])
def test_prepare_aircraft_normalizes_fast_preset_prop_arch(arch_type):
    """Normalize FAST preset labels before converting input to MATLAB."""

    prepared = prepare_aircraft(
        {
            "Specs": {
                "Propulsion": {
                    "PropArch": {
                        "Type": arch_type,
                    },
                    "PropArchLegacy": "drop",
                },
            },
        }
    )

    assert prepared["Specs"]["Propulsion"]["PropArch"] == {
        "Type": arch_type.upper(),
    }
    assert "PropArchLegacy" not in prepared["Specs"]["Propulsion"]


def test_input_aircraft_contract_accepts_fixed_numeric_custom_prop_arch():
    """Allow O propulsion architectures with fixed numeric matrix fields."""

    validate_json_schema_document(
        fixed_custom_prop_arch(),
        prop_arch_schema(),
        "InputAircraft.json.Specs.Propulsion.PropArch",
    )


def test_input_aircraft_contract_rejects_custom_prop_arch_variables():
    """Reject MATLAB markers and variable-like values inside O matrices."""

    prop_arch = fixed_custom_prop_arch()
    prop_arch["OperUps"][0][0] = {
        "_matlab_expression": "lambda"
    }

    with pytest.raises(JsonValidationError, match="PropArch"):
        validate_json_schema_document(
            prop_arch,
            prop_arch_schema(),
            "InputAircraft.json.Specs.Propulsion.PropArch",
        )


def test_prepare_aircraft_preserves_fixed_numeric_custom_prop_arch():
    """Keep O architecture matrix fields for MATLAB instead of collapsing Type."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Propulsion"]["PropArch"] = fixed_custom_prop_arch()

    prepared = prepare_aircraft(changed)

    assert prepared["Specs"]["Propulsion"]["PropArch"] == fixed_custom_prop_arch()


def test_prepare_aircraft_converts_custom_oper_matrices_directly():
    """Send fixed O operational matrices as MATLAB arrays, not functions."""

    prepared = prepare_aircraft(
        {
            "Specs": {
                "Propulsion": {
                    "PropArch": fixed_custom_prop_arch(),
                },
            },
        }
    )

    matlab_source = python_to_matlab(prepared["Specs"]["Propulsion"]["PropArch"])

    assert '"OperUps", [1, 0; 0, 1]' in matlab_source
    assert '"OperDwn", [1, 0; 0, 1]' in matlab_source


def test_prepare_aircraft_rejects_custom_prop_arch_variables():
    """Reject direct Python calls with nonnumeric values in O matrices."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    prop_arch = fixed_custom_prop_arch()
    prop_arch["OperDwn"][0][0] = "lambda"
    changed["Specs"]["Propulsion"]["PropArch"] = prop_arch

    with pytest.raises(ValueError, match="PropArch.OperDwn"):
        prepare_aircraft(changed)


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

    with pytest.raises(JsonValidationError, match="Mission.*Profile"):
        validate_aircraft_json(changed)


def fixed_custom_prop_arch():
    """Return the minimal fixed numeric O architecture used by contract tests."""

    return {
        "Type": "O",
        "Arch": [
            [1, 0],
            [0, 1],
        ],
        "OperUps": [
            [1, 0],
            [0, 1],
        ],
        "OperDwn": [
            [1, 0],
            [0, 1],
        ],
        "EtaUps": [
            [1, 0],
            [0, 1],
        ],
        "EtaDwn": [
            [1, 0],
            [0, 1],
        ],
        "SrcType": [
            1,
        ],
        "TrnType": [
            1,
            2,
        ],
    }


def prop_arch_schema():
    """Return the committed input PropArch schema branch."""

    schema = read_schema_file(INPUT_AIRCRAFT_SCHEMA_JSON_PATH)

    return schema["properties"]["Specs"]["properties"]["Propulsion"]["properties"][
        "PropArch"
    ]


def test_input_aircraft_contract_rejects_missing_mission():
    """Require the merged mission block in InputAircraft.json."""

    data = read_raw_json_file(DEFAULT_INPUT_DIR / "InputAircraft.json")
    changed = deepcopy(data)
    del changed["Mission"]

    with pytest.raises(JsonValidationError, match="missing required field Mission"):
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
