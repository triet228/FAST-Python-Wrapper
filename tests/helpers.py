# tests/helpers.py

"""Helpers for comparing Python-wrapper and saved FAST JSON results.

The tests intentionally run MATLAB instead of mocking it. The wrapper exists
to preserve FAST behavior from Python-defined inputs, so the useful regression
boundary is the final FAST aircraft structure rather than isolated helper
methods.
"""

import importlib.util
import json
import pytest
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helper import build_json_data, load_json_data, read_raw_json_file
from wrapper import FastWrapper, load_env_file, required_env_path


IGNORED_OUTPUT_PATHS = {
    "Aircraft.Mission.ProfileFxn",
    "Aircraft.Settings.Dir.Size",
    "Aircraft.Settings.Plotting",
}


def skip_unless_matlab_available():
    """Skip integration tests when MATLAB or MATLAB Engine is unavailable."""

    if shutil.which("matlab") is None:
        pytest.skip("MATLAB executable is not available on PATH.")

    try:
        matlab_engine_spec = importlib.util.find_spec("matlab.engine")
    except ModuleNotFoundError:
        matlab_engine_spec = None

    if matlab_engine_spec is None:
        pytest.skip("MATLAB Engine for Python is not installed.")


@pytest.fixture
def fast_path():
    """Return the configured FAST checkout path for integration tests."""

    skip_unless_matlab_available()
    load_env_file()
    return Path(required_env_path("FAST_PATH")).resolve()


@pytest.fixture
def examples_path(monkeypatch):
    """Return the root examples path used by parity tests."""

    monkeypatch.delenv("FAST_MODELS_PATH", raising=False)
    return PROJECT_ROOT / "examples"


def load_example_input(examples_path, case_path, file_name):
    """Load an example JSON input fixture.

    Inputs:
        examples_path: Root path for examples.
        case_path: Case directory name, such as A320.
        file_name: InputAircraft.json or Mission.json.

    Outputs:
        Python data accepted by FastWrapper.run().

    Assumptions:
        These fixture files intentionally mirror historical FAST MATLAB input
        functions, including marker objects for NaN, MATLAB expressions, and
        row vectors where MATLAB orientation matters.
    """

    path = examples_path / case_path / "inputs" / file_name
    return load_json_data(read_raw_json_file(path))


def compare_json_value(actual, expected, path="Aircraft"):
    """Return recursive JSON comparison failures.

    Inputs:
        actual: JSON-safe wrapper output.
        expected: Saved JSON fixture output.
        path: Dotted path used in failure messages.

    Outputs:
        A tuple of failure messages and scalar/container values compared.

    Assumptions:
        Numeric FAST output can vary slightly between MATLAB runs, so numbers
        are compared with the same tolerance used by the previous MATLAB
        parity check. Machine-specific and wrapper-specific fields are ignored.
    """

    if path in IGNORED_OUTPUT_PATHS:
        return [], 0

    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual) == {"_python_type", "_repr"} and set(expected) == {
            "_python_type",
            "_repr",
        }:
            if actual["_python_type"] != expected["_python_type"]:
                return [
                    f"{path} Python type mismatch: "
                    f"{actual['_python_type']!r} != {expected['_python_type']!r}"
                ], 1

            if actual["_python_type"] == "object":
                return [], 1

        failures = []
        compared = 1
        actual_keys = set(actual)
        expected_keys = set(expected)

        for key in sorted(expected_keys - actual_keys):
            failures.append(f"{path}.{key} missing from wrapper output")

        for key in sorted(actual_keys - expected_keys):
            failures.append(f"{path}.{key} missing from saved output")

        for key in sorted(actual_keys & expected_keys):
            child_failures, child_compared = compare_json_value(
                actual[key],
                expected[key],
                f"{path}.{key}",
            )
            failures.extend(child_failures)
            compared += child_compared

        return failures, compared

    if isinstance(actual, list) and isinstance(expected, list):
        failures = []
        compared = 1

        if len(actual) != len(expected):
            return [f"{path} list length mismatch: {len(actual)} != {len(expected)}"], compared

        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            child_failures, child_compared = compare_json_value(
                actual_item,
                expected_item,
                f"{path}[{index}]",
            )
            failures.extend(child_failures)
            compared += child_compared

        return failures, compared

    if is_json_number(actual) and is_json_number(expected):
        tolerance = 1e-6 + 1e-8 * abs(expected)

        if abs(actual - expected) <= tolerance:
            return [], 1

        return [f"{path} numeric mismatch: {actual!r} != {expected!r}"], 1

    if actual == expected:
        return [], 1

    return [f"{path} value mismatch: {actual!r} != {expected!r}"], 1


def is_json_number(value):
    """Return True for JSON numeric values that are not booleans."""

    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(
        value,
        bool,
    )


def assert_fast_model_wrapper_matches_saved_output(
    name,
    aircraft,
    mission,
    saved,
    fast_path,
    examples_path,
    tmp_path,
):
    """Run one JSON fixture case through the wrapper and compare JSON output.

    Inputs:
        name: Aircraft case name used in failure output.
        aircraft: Python dictionary generated from the vendored aircraft JSON
            input fixture.
        mission: Python dictionary generated from the vendored mission JSON
            input fixture.
        saved: Case-relative path to the saved OutputAircraft.json baseline.
        fast_path: Local FAST checkout path.
        examples_path: Example fixture root.

    Outputs:
        None. Assertions fail when any comparable wrapper result field differs
        from the saved FAST output JSON field.

    Assumptions:
        The JSON fixture files mirror the historical FAST aircraft and mission
        definitions. This keeps the tests on the
        same user-facing path as main.py: Python data goes into the wrapper,
        FAST runs, and the final aircraft is checked recursively.
    """

    if not examples_path.exists():
        pytest.skip(f"examples path not found: {examples_path}")

    with FastWrapper(fast_path) as fast:
        result = fast.run(aircraft=aircraft, mission=mission)

    actual = build_json_data(result["aircraft"])
    expected = read_raw_json_file(examples_path / saved)
    failures, compared = compare_json_value(actual, expected)

    assert compared > 0, f"{name} did not compare any output fields"
    assert not failures, (
        f"{name} wrapper output differs from OutputAircraft.json:\n"
        + "\n".join(failures[:50])
    )
