# tests/helpers.py

"""Helpers for comparing Python-wrapper and saved FAST JSON results.

The tests intentionally run MATLAB instead of mocking it. The wrapper exists
to preserve FAST behavior from Python-defined inputs, so the useful regression
boundary is the final FAST aircraft structure rather than isolated helper
methods.
"""

import ast
import importlib.util
import json
import math
import os
import pytest
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helper import build_json_data, load_json_data, read_raw_json_file
from wrapper import FastWrapper


IGNORED_OUTPUT_PATHS = {
    "Aircraft.Settings.Plotting",
}
UNPARSED_REPR = object()


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
    value = os.environ.get("FAST_PATH", "").strip()

    if not value or r"\path\to\\" in value or r"\path\to" in value:
        pytest.skip("Set FAST_PATH to a local FAST checkout to run integration tests.")

    return Path(value).resolve()


@pytest.fixture
def examples_path(monkeypatch):
    """Return the root examples path used by parity tests."""

    monkeypatch.delenv("FAST_MODELS_PATH", raising=False)
    return PROJECT_ROOT / "examples"


def load_example_input(examples_path, case_path):
    """Load an example JSON input fixture.

    Inputs:
        examples_path: Root path for examples.
        case_path: Case directory name, such as A320.

    Outputs:
        Python data accepted by FastWrapper.run().

    Assumptions:
        These fixture files intentionally mirror historical FAST MATLAB input
        functions, including marker objects for NaN, MATLAB expressions, and
        row vectors where MATLAB orientation matters.
    """

    path = examples_path / case_path / "InputAircraft.json"
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
            return compare_output_marker(actual, expected, path)

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
        if math.isnan(actual) and math.isnan(expected):
            return [], 1

        if math.isinf(actual) or math.isinf(expected):
            if actual == expected:
                return [], 1

            return [f"{path} numeric mismatch: {actual!r} != {expected!r}"], 1

        tolerance = 5e-5 + 1e-8 * abs(expected)

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


def compare_output_marker(actual, expected, path):
    """Compare saved output marker objects.

    Inputs:
        actual: Marker dictionary produced by build_json_data().
        expected: Marker dictionary from a saved FAST output fixture.
        path: Dotted path used in failure messages.

    Outputs:
        A tuple of failure messages and compared values.

    Assumptions:
        MATLAB Engine exposes some arrays as opaque objects, so build_json_data()
        stores their repr strings. Numeric repr payloads can vary by tiny
        floating-point amounts between MATLAB releases and machines, so parseable
        repr strings are compared recursively with the normal numeric tolerance.
    """

    if actual["_python_type"] != expected["_python_type"]:
        return [
            f"{path} Python type mismatch: "
            f"{actual['_python_type']!r} != {expected['_python_type']!r}"
        ], 1

    if actual["_python_type"] == "object":
        return [], 1

    actual_repr = parse_comparable_repr(actual["_repr"])
    expected_repr = parse_comparable_repr(expected["_repr"])

    if actual_repr is not UNPARSED_REPR and expected_repr is not UNPARSED_REPR:
        return compare_json_value(actual_repr, expected_repr, f"{path}._repr")

    if actual["_repr"] == expected["_repr"]:
        return [], 1

    return [
        f"{path} repr mismatch: "
        f"{actual['_repr'][:120]!r} != {expected['_repr'][:120]!r}"
    ], 1


def parse_comparable_repr(value):
    """Return a Python value when an output repr is safe to compare recursively."""

    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        parsed = parse_repr_expression(value)

    if not is_comparable_repr_value(parsed):
        return UNPARSED_REPR

    return parsed


def parse_repr_expression(value):
    """Parse repr lists that contain MATLAB-style nan or inf tokens."""

    try:
        tree = ast.parse(value, mode="eval")
    except SyntaxError:
        return UNPARSED_REPR

    try:
        return parse_repr_node(tree.body)
    except ValueError:
        return UNPARSED_REPR


def parse_repr_node(node):
    """Return a value from a narrow, literal-only repr syntax tree."""

    if isinstance(node, ast.List):
        return [parse_repr_node(item) for item in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(parse_repr_node(item) for item in node.elts)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id == "nan":
            return math.nan

        if node.id == "inf":
            return math.inf

    if isinstance(node, ast.UnaryOp):
        value = parse_repr_node(node.operand)

        if isinstance(node.op, ast.USub) and is_json_number(value):
            return -value

        if isinstance(node.op, ast.UAdd) and is_json_number(value):
            return value

    raise ValueError("Unsupported repr node.")


def is_comparable_repr_value(value):
    """Return True when a parsed repr contains only stable comparable values."""

    if value is None or isinstance(value, str) or isinstance(value, bool):
        return True

    if is_json_number(value):
        return True

    if isinstance(value, list) or isinstance(value, tuple):
        return all(is_comparable_repr_value(item) for item in value)

    return False


def assert_fast_model_wrapper_matches_saved_output(
    name,
    aircraft,
    saved,
    fast_path,
    examples_path,
    tmp_path,
):
    """Run one JSON fixture case through the wrapper and compare JSON output.

    Inputs:
        name: Aircraft case name used in failure output.
        aircraft: Python dictionary generated from the vendored merged aircraft
            JSON input fixture.
        saved: Case-relative path to the saved OutputAircraft.json baseline.
        fast_path: Local FAST checkout path.
        examples_path: Example fixture root.

    Outputs:
        None. Assertions fail when any comparable wrapper result field differs
        from the saved FAST output JSON field.

    Assumptions:
        The JSON fixture files provide merged aircraft and mission data for the
        wrapper, FAST runs, and the final aircraft is checked recursively.
    """

    if not examples_path.exists():
        pytest.skip(f"examples path not found: {examples_path}")

    with FastWrapper(fast_path) as fast:
        result = fast.run(input_aircraft=aircraft)

    assert result["status"] == "Yes", f"{name} FAST run failed:\n{result['log']}"

    actual = build_json_data(result["output"])
    expected = read_raw_json_file(examples_path / saved)
    failures, compared = compare_json_value(actual, expected)

    assert compared > 0, f"{name} did not compare any output fields"
    assert not failures, (
        f"{name} wrapper output differs from OutputAircraft.json:\n"
        + "\n".join(failures[:50])
    )
