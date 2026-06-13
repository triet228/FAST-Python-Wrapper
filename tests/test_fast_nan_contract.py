# tests/test_fast_nan_contract.py

"""Compare NaN input validation against real MATLAB FAST behavior."""

from copy import deepcopy
from math import isfinite

from helper import (
    JsonValidationError,
    load_json_data,
    read_raw_json_file,
    validate_aircraft_json,
    validate_mission_json,
)
from tests.helpers import PROJECT_ROOT, fast_path
from wrapper import FastWrapper


INPUT_FILES = [
    ("InputAircraft.json", validate_aircraft_json),
    ("Mission.json", validate_mission_json),
]


def is_matlab_expression_marker(value):
    """Return True when a JSON object represents one scalar MATLAB expression."""

    return isinstance(value, dict) and set(value) == {"_matlab_expression"}


def iter_variable_paths(value, path=()):
    """Yield scalar variable paths, treating marker objects as scalar values."""

    if is_matlab_expression_marker(value):
        yield path
        return

    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_variable_paths(item, path + (key,))
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_variable_paths(item, path + (index,))
        return

    yield path


def format_path(path):
    """Return a stable dotted path for fields and representative array entries."""

    parts = []

    for item in path:
        if isinstance(item, int):
            parts[-1] = parts[-1] + "[]"
        else:
            parts.append(item)

    return ".".join(parts)


def set_path(data, path, value):
    """Replace a nested JSON value in copied fixture data."""

    item = data

    for key in path[:-1]:
        item = item[key]

    item[path[-1]] = value


def collect_variable_cases(file_name):
    """Return one representative example case for each input variable path."""

    cases = {}

    for case_dir in sorted((PROJECT_ROOT / "examples").iterdir()):
        data = read_raw_json_file(case_dir / "inputs" / file_name)

        for path in iter_variable_paths(data):
            label = format_path(path)

            if label not in cases:
                cases[label] = (case_dir.name, path)

    return cases


def validator_accepts_nan(file_name, validator, case_name, path):
    """Return whether the JSON validator accepts NaN at one variable path."""

    data = read_raw_json_file(
        PROJECT_ROOT / "examples" / case_name / "inputs" / file_name
    )
    changed = deepcopy(data)
    set_path(changed, path, "NaN")

    try:
        validator(changed)
    except JsonValidationError as error:
        return False, str(error)

    return True, ""


def fast_accepts_nan(fast, file_name, case_name, path):
    """Return whether FAST completes with finite MTOW for one NaN mutation."""

    aircraft = read_raw_json_file(
        PROJECT_ROOT / "examples" / case_name / "inputs" / "InputAircraft.json"
    )
    mission = read_raw_json_file(
        PROJECT_ROOT / "examples" / case_name / "inputs" / "Mission.json"
    )
    changed = deepcopy(aircraft if file_name == "InputAircraft.json" else mission)
    set_path(changed, path, "NaN")

    if file_name == "InputAircraft.json":
        aircraft = changed
    else:
        mission = changed

    try:
        result = fast.run(
            aircraft=load_json_data(aircraft),
            mission=load_json_data(mission),
        )
    except Exception as error:
        message = str(error).splitlines()[0]
        return False, f"{type(error).__name__}: {message}"

    mtow = result["mtow"]

    if not isfinite(mtow):
        return False, f"nonfinite mtow={mtow}"

    return True, f"mtow={mtow}"


def test_nan_input_validation_matches_matlab_fast(fast_path):
    """Check every input variable path against actual FAST NaN behavior."""

    mismatches = []

    with FastWrapper(fast_path).start() as fast:
        for file_name, validator in INPUT_FILES:
            for label, (case_name, path) in sorted(
                collect_variable_cases(file_name).items()
            ):
                validator_ok, validator_message = validator_accepts_nan(
                    file_name,
                    validator,
                    case_name,
                    path,
                )
                fast_ok, fast_message = fast_accepts_nan(
                    fast,
                    file_name,
                    case_name,
                    path,
                )

                if validator_ok != fast_ok:
                    mismatches.append(
                        f"{file_name} {label} ({case_name}): "
                        f"validator={validator_ok} {validator_message}; "
                        f"FAST={fast_ok} {fast_message}"
                    )

    assert not mismatches
