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
import wrapper as wrapper_module
from wrapper import wrap


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


def test_wrap_requires_embedded_mission_profile(monkeypatch, tmp_path):
    """Require mission data to be embedded in InputAircraft."""

    class FakeEngine:
        def __init__(self):
            self.workspace = {}

        def evalc(self, script, nargout=1):
            raise AssertionError("FAST should not run without Mission.Profile")

        def quit(self):
            pass

    fast_path = tmp_path / "FAST"
    fast_path.mkdir()
    (fast_path / "Main.m").write_text("", encoding="utf-8")
    monkeypatch.setattr(wrapper_module, "_start_matlab", lambda path: FakeEngine())

    result = wrap({"Specs": {}}, fast_path)

    assert result["status"] == "No"
    assert "Mission.Profile" in result["log"]
    assert result["output"] == {}


def test_wrap_returns_status_log_output_dict(monkeypatch, tmp_path):
    """Keep wrap() as the status/log/output API."""

    class FakeEngine:
        def __init__(self):
            self.workspace = {}
            self.quit_called = False

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

        def quit(self):
            self.quit_called = True

    fake_engine = FakeEngine()
    fast_path = tmp_path / "FAST"
    fast_path.mkdir()
    (fast_path / "Main.m").write_text("", encoding="utf-8")
    monkeypatch.setattr(wrapper_module, "_start_matlab", lambda path: fake_engine)
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

    result = wrap(input_aircraft, fast_path)

    assert result["status"] == "Yes"
    assert result["log"] == "fake log"
    assert result["output"]["Specs"]["Weight"]["MTOW"] == 123.4567
    assert fake_engine.quit_called


def test_wrap_reports_no_when_output_is_missing(monkeypatch, tmp_path):
    """Return a No status instead of assuming FAST produced OutputAircraft."""

    class FakeEngine:
        def __init__(self):
            self.workspace = {}

        def evalc(self, script, nargout=1):
            self.workspace["fast_status"] = "No"
            self.workspace["fast_result"] = {}
            return "FAST did not converge"

        def quit(self):
            pass

    fast_path = tmp_path / "FAST"
    fast_path.mkdir()
    (fast_path / "Main.m").write_text("", encoding="utf-8")
    monkeypatch.setattr(wrapper_module, "_start_matlab", lambda path: FakeEngine())
    input_aircraft = {
        "Specs": {},
        "Mission": {
            "Profile": {},
        },
    }

    result = wrap(input_aircraft, fast_path)

    assert result == {
        "status": "No",
        "log": "FAST did not converge",
        "output": {},
    }


def test_wrap_keeps_only_supported_prop_arch_output(monkeypatch, tmp_path):
    """Keep output focused on reusable aircraft data."""

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
                            "Type": "FAST internal",
                            "Unexpected": "drop",
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

        def quit(self):
            pass

    fast_path = tmp_path / "FAST"
    fast_path.mkdir()
    (fast_path / "Main.m").write_text("", encoding="utf-8")
    monkeypatch.setattr(wrapper_module, "_start_matlab", lambda path: FakeEngine())
    input_aircraft = {
        "Specs": {
            "Propulsion": {
                "PropArch": {
                    "Type": "TE",
                },
            },
        },
        "Mission": {
            "Profile": {},
        },
    }

    result = wrap(input_aircraft, fast_path)
    output = result["output"]

    assert "Preset" not in output["Geometry"]
    assert output["Geometry"]["LengthSet"] == 1
    assert output["Specs"]["Propulsion"]["PropArch"] == {"Type": "TE"}
    assert "ProfileFxn" not in output["Mission"]
    assert "Size" not in output["Settings"]["Dir"]
    assert output["Settings"]["Dir"]["Oper"] == "keep"
