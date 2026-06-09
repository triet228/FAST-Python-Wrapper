# tests/test_input_contracts.py

"""Check committed input JSON files against structure contracts."""

from copy import deepcopy

import pytest

from helper import (
    JsonValidationError,
    read_raw_json_file,
    validate_aircraft_json,
    validate_mission_json,
)
from tests.helpers import PROJECT_ROOT


def test_input_aircraft_matches_structure_contract():
    """Validate the default aircraft input template contract."""

    data = read_raw_json_file(PROJECT_ROOT / "inputs" / "InputAircraft.json")

    validate_aircraft_json(data)


def test_mission_matches_structure_contract():
    """Validate the default mission input template contract."""

    data = read_raw_json_file(PROJECT_ROOT / "inputs" / "Mission.json")

    validate_mission_json(data)


def test_input_aircraft_contract_rejects_unexpected_field():
    """Reject aircraft inputs that drift outside the committed contract."""

    data = read_raw_json_file(PROJECT_ROOT / "inputs" / "InputAircraft.json")
    changed = deepcopy(data)
    changed["Specs"]["Unexpected"] = {}

    with pytest.raises(JsonValidationError, match="unexpected field"):
        validate_aircraft_json(changed)


def test_mission_contract_rejects_missing_field():
    """Reject mission inputs that omit a committed contract field."""

    data = read_raw_json_file(PROJECT_ROOT / "inputs" / "Mission.json")
    changed = deepcopy(data)
    del changed["VelEnd"]

    with pytest.raises(JsonValidationError, match="missing required field"):
        validate_mission_json(changed)
