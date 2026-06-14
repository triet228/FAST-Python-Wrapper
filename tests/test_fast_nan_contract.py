# tests/test_fast_nan_contract.py

"""Check merged input handling for FAST unspecified mission values."""

from math import isnan

import pytest

from helper import (
    JsonValidationError,
    load_json_data,
    read_raw_json_file,
    validate_aircraft_json,
)
from tests.helpers import PROJECT_ROOT
from wrapper import FastWrapper


DEFAULT_INPUT_PATH = PROJECT_ROOT / "examples" / "CeRAS" / "InputAircraft.json"


def test_json_null_values_load_as_fast_nan():
    """Convert schema-level null placeholders into FAST NaN inputs."""

    data = {
        "Mission": {
            "Profile": {
                "ClbRate": [
                    None,
                ],
            },
        },
    }

    loaded = load_json_data(data)

    assert isnan(loaded["Mission"]["Profile"]["ClbRate"][0])


def test_schema_rejects_legacy_nan_string_in_mission_profile():
    """Keep mission profile NaN placeholders as JSON null, not strings."""

    data = read_raw_json_file(DEFAULT_INPUT_PATH)
    data["Mission"]["Profile"]["ClbRate"][0] = "NaN"

    with pytest.raises(JsonValidationError, match="ClbRate"):
        validate_aircraft_json(data)


def test_wrapper_extracts_embedded_mission_profile():
    """Pass FAST a mission profile sourced from InputAircraft.json."""

    wrapper = FastWrapper.__new__(FastWrapper)
    aircraft = {
        "Specs": {},
        "Mission": {
            "Profile": {
                "Segs": [],
            },
        },
    }

    mission = wrapper._extract_mission_profile(aircraft)

    assert mission == {"Segs": []}
    assert "Mission" not in aircraft


def test_wrapper_run_returns_status_log_output_dict():
    """Keep FastWrapper.run as the status/log/output API."""

    class FakeEngine:
        def __init__(self):
            self.workspace = {}

        def evalc(self, script, nargout=1):
            self.workspace["fast_status"] = "Yes"
            self.workspace["fast_result"] = {
                "Specs": {
                    "Weight": {
                        "MTOW": 123.4567,
                    },
                },
                "Mission": {
                    "Profile": {},
                },
            }
            return "fake log"

    wrapper = FastWrapper.__new__(FastWrapper)
    wrapper.engine = FakeEngine()
    input_aircraft = {
        "Specs": {
            "Propulsion": {
                "PropArch": {
                    "Type": "C",
                },
            },
        },
        "Mission": {
            "Profile": {},
        },
    }

    result = wrapper.run(input_aircraft)

    assert result["status"] == "Yes"
    assert result["log"] == "fake log"
    assert result["output"]["Specs"]["Weight"]["MTOW"] == 123.4567


def test_wrapper_run_reports_no_when_output_is_missing():
    """Return a No status instead of assuming FAST produced OutputAircraft."""

    class FakeEngine:
        def __init__(self):
            self.workspace = {}

        def evalc(self, script, nargout=1):
            self.workspace["fast_status"] = "No"
            self.workspace["fast_result"] = {}
            return "FAST did not converge"

    wrapper = FastWrapper.__new__(FastWrapper)
    wrapper.engine = FakeEngine()
    input_aircraft = {
        "Specs": {},
        "Mission": {
            "Profile": {},
        },
    }

    result = wrapper.run(input_aircraft)

    assert result == {
        "status": "No",
        "log": "FAST did not converge",
        "output": {},
    }


def test_wrapper_run_removes_matlab_specific_output_fields():
    """Keep wrapper output focused on reusable aircraft data."""

    class FakeEngine:
        def __init__(self):
            self.workspace = {}

        def evalc(self, script, nargout=1):
            self.workspace["fast_status"] = "Yes"
            self.workspace["fast_result"] = {
                "Geometry": {
                    "Preset": "drop",
                    "LengthSet": 1,
                },
                "Specs": {
                    "Propulsion": {
                        "PropArch": {
                            "Type": "C",
                            "OperUps": "drop",
                            "OperDwn": "drop",
                        },
                    },
                },
                "Mission": {
                    "Profile": {},
                    "ProfileFxn": "drop",
                },
                "Settings": {
                    "Dir": {
                        "Size": "drop",
                        "Oper": "keep",
                    },
                },
            }
            return "fake log"

    wrapper = FastWrapper.__new__(FastWrapper)
    wrapper.engine = FakeEngine()
    input_aircraft = {
        "Specs": {},
        "Mission": {
            "Profile": {},
        },
    }

    result = wrapper.run(input_aircraft)
    output = result["output"]

    assert "Preset" not in output["Geometry"]
    assert output["Geometry"]["LengthSet"] == 1
    assert "OperUps" not in output["Specs"]["Propulsion"]["PropArch"]
    assert "OperDwn" not in output["Specs"]["Propulsion"]["PropArch"]
    assert "ProfileFxn" not in output["Mission"]
    assert "Size" not in output["Settings"]["Dir"]
    assert output["Settings"]["Dir"]["Oper"] == "keep"
