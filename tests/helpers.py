# tests/helpers.py

"""Helpers for comparing Python-wrapper and saved MATLAB FAST results.

The tests intentionally run MATLAB instead of mocking it. The wrapper exists
to preserve FAST behavior from Python-defined inputs, so the useful regression
boundary is the final FAST aircraft structure rather than isolated helper
methods.
"""

import importlib.util
import json
import math
import pytest
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as wrapper_main
from wrapper import FastWrapper, load_env_file, required_env_path


WRAPPER_METRICS = {
    "mtow_kg": ["Specs", "Weight", "MTOW"],
    "fuel_kg": ["Specs", "Weight", "Fuel"],
    "battery_kg": ["Specs", "Weight", "Batt"],
    "electric_motor_kg": ["Specs", "Weight", "EM"],
    "electric_generator_kg": ["Specs", "Weight", "EG"],
}

SAVED_MODEL_METRICS = {
    "mtow_kg": ["Specs", "Weight", "MTOW"],
    "fuel_kg": ["Specs", "Weight", "Fuel"],
}

MATLAB_COMPARE_SCRIPT = r'''
saved_data = load(saved_path);
saved_names = fieldnames(saved_data);
saved = saved_data.(saved_names{1});
ignored_paths = [
    "Aircraft.Mission.ProfileFxn"
    "Aircraft.Settings.Dir.Size"
    "Aircraft.Settings.Plotting"
];
[failures, skipped, compared] = compare_value(fast_result, saved, "Aircraft", ignored_paths);
report = struct();
report.compared = compared;
report.failures = failures;
report.skipped = skipped;
fid = fopen(report_path, "w");
fprintf(fid, "%s", jsonencode(report));
fclose(fid);

function [failures, skipped, compared] = compare_value(actual, expected, path, ignored_paths)
    failures = {};
    skipped = {};
    compared = 0;

    if any(path == ignored_paths)
        skipped{end + 1} = char(path + " skipped: expected wrapper-specific or machine-specific value");
        return;
    end

    if (ischar(actual) || isstring(actual)) && (ischar(expected) || isstring(expected))
        compared = compared + 1;

        if ~isequal(string(actual), string(expected))
            failures{end + 1} = char(path + " text mismatch");
        end
        return;
    end

    if ~strcmp(class(actual), class(expected))
        failures{end + 1} = char(path + " class mismatch: " + class(actual) + " != " + class(expected));
        return;
    end

    if isstruct(actual)
        actual_fields = string(fieldnames(actual));
        expected_fields = string(fieldnames(expected));

        missing_from_actual = setdiff(expected_fields, actual_fields);
        missing_from_expected = setdiff(actual_fields, expected_fields);

        for idx = 1:numel(missing_from_actual)
            failures{end + 1} = char(path + "." + missing_from_actual(idx) + " missing from wrapper output");
        end

        for idx = 1:numel(missing_from_expected)
            failures{end + 1} = char(path + "." + missing_from_expected(idx) + " missing from saved output");
        end

        shared_fields = intersect(actual_fields, expected_fields);

        for idx = 1:numel(shared_fields)
            field = shared_fields(idx);
            [child_failures, child_skipped, child_compared] = compare_value( ...
                actual.(field), ...
                expected.(field), ...
                path + "." + field, ...
                ignored_paths ...
            );
            failures = [failures, child_failures];
            skipped = [skipped, child_skipped];
            compared = compared + child_compared;
        end
        return;
    end

    if iscell(actual)
        if ~isequal(size(actual), size(expected))
            failures{end + 1} = char(path + " cell size mismatch");
            return;
        end

        for idx = 1:numel(actual)
            [child_failures, child_skipped, child_compared] = compare_value( ...
                actual{idx}, ...
                expected{idx}, ...
                path + "{" + idx + "}", ...
                ignored_paths ...
            );
            failures = [failures, child_failures];
            skipped = [skipped, child_skipped];
            compared = compared + child_compared;
        end
        return;
    end

    if isnumeric(actual) || islogical(actual)
        compared = compared + 1;

        if ~isequal(size(actual), size(expected))
            failures{end + 1} = char(path + " numeric/logical size mismatch");
            return;
        end

        if isempty(actual)
            return;
        end

        if isnumeric(actual)
            same_nan = isnan(actual) & isnan(expected);
            same_inf = isinf(actual) & isinf(expected) & (sign(actual) == sign(expected));
            delta = abs(actual - expected);
            tolerance = 1e-6 + 1e-8 .* abs(expected);
            matches = same_nan | same_inf | (delta <= tolerance);

            if ~all(matches(:))
                max_delta = max(delta(~same_nan), [], "all");
                failures{end + 1} = char(path + " numeric mismatch, max delta " + string(max_delta));
            end
        elseif ~isequal(actual, expected)
            failures{end + 1} = char(path + " logical mismatch");
        end
        return;
    end

    if isa(actual, "function_handle")
        compared = compared + 1;

        if ~strcmp(func2str(actual), func2str(expected))
            failures{end + 1} = char(path + " function handle mismatch");
        end
        return;
    end

    compared = compared + 1;

    try
        if ~isequaln(actual, expected)
            failures{end + 1} = char(path + " " + class(actual) + " value mismatch");
        end
    catch
        skipped{end + 1} = char(path + " skipped: " + class(actual) + " cannot be compared with isequaln");
        compared = compared - 1;
    end
end
'''


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
def fast_models_path(monkeypatch):
    """Return the vendored FAST-model fixtures path used by parity tests."""

    monkeypatch.delenv("FAST_MODELS_PATH", raising=False)
    return PROJECT_ROOT / "tests" / "FAST-models"


def get_nested(data, path):
    """Read a nested output field using the same path in Python and MATLAB."""

    current = data

    for key in path:
        current = current[key]

    return current


def normalize_number(value):
    """Convert MATLAB/Python numeric values into comparable floats."""

    if isinstance(value, list):
        if len(value) == 1:
            return normalize_number(value[0])

        raise AssertionError(f"Expected scalar output, got list: {value!r}")

    return float(value)


def python_metrics(aircraft):
    """Collect stable scalar metrics from a Python-converted FAST aircraft."""

    metrics = {}

    for name, path in WRAPPER_METRICS.items():
        metrics[name] = normalize_number(get_nested(aircraft, path))

    return metrics


def collect_metrics(aircraft, metric_paths):
    """Collect selected scalar metrics from a Python FAST aircraft structure."""

    metrics = {}

    for name, path in metric_paths.items():
        metrics[name] = normalize_number(get_nested(aircraft, path))

    return metrics


def assert_close_numbers(actual, expected, name):
    """Compare numeric FAST metrics with tolerance for MATLAB run noise."""

    if math.isnan(actual) and math.isnan(expected):
        return

    assert math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-6), (
        f"{name}: Python wrapper {actual!r} != MATLAB {expected!r}"
    )


def write_text(path, text):
    """Write generated MATLAB scripts in one place for easier cleanup."""

    path.write_text(text, encoding="utf-8")


def matlab_string(value):
    """Return a MATLAB double-quoted string literal for a local path."""

    return '"' + str(value).replace("\\", "/").replace('"', '""') + '"'


def run_matlab_script(script_path):
    """Run a MATLAB script through batch mode and fail with captured output."""

    command = ["matlab", "-batch", f"run('{script_path.as_posix()}')"]
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def assert_wrapper_case_matches_matlab(fast_path, tmp_path):
    """Run main.py's JSON input case and compare it with direct MATLAB FAST."""

    aircraft, mission = wrapper_main.load_input_json_files()

    with FastWrapper(fast_path) as fast:
        python_result = fast.run(
            aircraft=aircraft,
            mission=mission,
        )
        python_output = python_metrics(python_result["aircraft"])

        aircraft = fast._prepare_aircraft(aircraft)
        aircraft_literal = fast._to_matlab_literal(aircraft)
        mission_literal = fast._to_matlab_literal(mission)

    output_path = tmp_path / "wrapper_case_metrics.json"
    script_path = tmp_path / "run_wrapper_case.m"
    script = f"""
addpath(genpath({matlab_string(fast_path)}));
aircraft_spec = {aircraft_literal};
mission_profile = @(Aircraft) setfield(Aircraft, "Mission", "Profile", {mission_literal});
fast_result = Main(aircraft_spec, mission_profile);
metrics = struct();
metrics.mtow_kg = fast_result.Specs.Weight.MTOW;
metrics.fuel_kg = fast_result.Specs.Weight.Fuel;
metrics.battery_kg = fast_result.Specs.Weight.Batt;
metrics.electric_motor_kg = fast_result.Specs.Weight.EM;
metrics.electric_generator_kg = fast_result.Specs.Weight.EG;
fid = fopen({matlab_string(output_path)}, "w");
fprintf(fid, "%s", jsonencode(metrics));
fclose(fid);
"""
    write_text(script_path, script)
    run_matlab_script(script_path)
    matlab_output = json.loads(output_path.read_text(encoding="utf-8"))

    for name, actual in python_output.items():
        expected = normalize_number(matlab_output[name])
        assert_close_numbers(actual, expected, name)


def assert_fast_model_wrapper_matches_saved_output(
    name,
    aircraft,
    mission,
    saved,
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Run one Python fixture case through the wrapper and compare .mat.

    Inputs:
        name: Aircraft case name used in failure output.
        aircraft: Python dictionary generated from the vendored aircraft `.m`
            input fixture.
        mission: Python dictionary generated from the vendored mission `.m`
            input fixture.
        saved: Case-relative path to the saved OutputAircraft.mat baseline.
        fast_path: Local FAST checkout path.
        fast_models_path: Vendored test fixture root.

    Outputs:
        None. Assertions fail when any comparable wrapper result field differs
        from the saved MATLAB FAST output field.

    Assumptions:
        The explicit dictionaries in each test file were generated from the
        vendored aircraft and mission `.m` files. This keeps the tests on the
        same user-facing path as main.py: Python data goes into the wrapper,
        FAST runs, and the final aircraft is checked recursively.
    """

    if not fast_models_path.exists():
        pytest.skip(f"FAST-models path not found: {fast_models_path}")

    saved_path = fast_models_path / saved
    report_path = tmp_path / f"{name.lower()}_comparison.json"
    script_path = tmp_path / f"compare_{name.lower()}.m"
    write_text(script_path, MATLAB_COMPARE_SCRIPT)

    with FastWrapper(fast_path) as fast:
        fast.engine.workspace["saved_path"] = str(saved_path)
        fast.engine.workspace["report_path"] = str(report_path)
        fast.run(aircraft=aircraft, mission=mission)
        fast.engine.evalc(f"run('{script_path.as_posix()}')", nargout=1)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures = report.get("failures", [])
    compared = report.get("compared", 0)

    assert compared > 0, f"{name} did not compare any output fields"
    assert not failures, (
        f"{name} wrapper output differs from OutputAircraft.mat:\n"
        + "\n".join(failures[:50])
    )
