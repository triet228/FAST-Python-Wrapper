# wrapper.py

import re
from copy import deepcopy
from pathlib import Path


VALID_STRUCT_FIELD = re.compile(r"^[A-Za-z]\w*$")
OUTPUT_FIELDS_TO_REMOVE = (
    ("Geometry", "Preset"),
    ("Specs", "Propulsion", "PropArch", "OperUps"),
    ("Specs", "Propulsion", "PropArch", "OperDwn"),
    ("Mission", "ProfileFxn"),
    ("Settings", "Dir", "Size"),
)


class MatlabExpression:
    """Store trusted MATLAB code inserted directly into generated source."""

    def __init__(self, value):
        self.value = value


class MatlabRow:
    """Mark a Python sequence that must become a MATLAB row vector."""

    def __init__(self, value):
        self.value = value


def matlab_expr(value):
    """Return a MATLAB expression marker for Python-defined specs."""

    return MatlabExpression(value)


def wrap(input_aircraft, fast_path):
    """Run FAST once from a Python InputAircraft dictionary.

    Inputs:
        input_aircraft: Nested dictionary matching InputAircraftSchema, with
            Mission.Profile holding the mission profile fields.
        fast_path: Local FAST checkout path containing Main.m.

    Outputs:
        Dictionary containing:
        - status: "Yes" when FAST returns OutputAircraft, otherwise "No".
        - log: MATLAB stdout captured during the run.
        - output: Python dictionary equivalent of FAST OutputAircraft, or an
            empty dictionary when FAST does not produce one.

    Side effects:
        Starts MATLAB Engine, adds FAST to the MATLAB path, runs Main.m, and
        quits MATLAB before returning.
    """

    engine = _start_matlab(_resolve_fast_path(fast_path))

    try:
        try:
            aircraft = _prepare_aircraft(input_aircraft)
            mission = _extract_mission_profile(aircraft)
            aircraft_literal = _to_matlab_literal(aircraft)
            mission_literal = _to_matlab_literal(mission)
        except Exception as error:
            return {
                "status": "No",
                "log": str(error),
                "output": {},
            }

        try:
            log = engine.evalc(
                f"""
                aircraft_spec = {aircraft_literal};
                mission_profile = @(Aircraft) setfield(Aircraft, "Mission", "Profile", {mission_literal});
                fast_result = struct();
                fast_status = 'No';
                try
                    fast_result = Main(aircraft_spec, mission_profile);
                    fast_status = 'Yes';
                catch fast_exception
                    disp(getReport(fast_exception, 'extended', 'hyperlinks', 'off'));
                end
                """,
                nargout=1,
            )
        except Exception as error:
            return {
                "status": "No",
                "log": str(error),
                "output": {},
            }

        try:
            fast_status = engine.workspace["fast_status"]
        except Exception:
            fast_status = "No"

        try:
            fast_result = engine.workspace["fast_result"]
        except Exception:
            fast_result = {}

        output = _to_python_data(fast_result)

        if isinstance(output, dict):
            _drop_output_fields(output)

        if not isinstance(output, dict) or not output:
            return {
                "status": "No",
                "log": log,
                "output": {},
            }

        if str(fast_status) != "Yes":
            return {
                "status": "No",
                "log": log,
                "output": output,
            }

        return {
            "status": "Yes",
            "log": log,
            "output": output,
        }
    finally:
        engine.quit()


def _start_matlab(fast_path):
    """Start MATLAB Engine and add the FAST checkout to MATLAB's path."""

    try:
        import matlab.engine
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "MATLAB Engine for Python is not installed in this environment."
        ) from error

    engine = matlab.engine.start_matlab()
    engine.addpath(engine.genpath(str(fast_path)), nargout=0)
    return engine


def _resolve_fast_path(fast_path):
    """Resolve and validate the configured FAST checkout path."""

    if not fast_path:
        raise RuntimeError("FAST path is required.")

    path = Path(fast_path).expanduser().resolve()
    _validate_fast_path(path)
    return path


def _validate_fast_path(path):
    """Check that the FAST checkout has the entry point used by this module."""

    if not path.exists() or not path.is_dir():
        raise RuntimeError(f"FAST path does not exist: {path}")

    required_paths = [path / "Main.m"]
    missing_paths = [str(item) for item in required_paths if not item.exists()]

    if missing_paths:
        joined_paths = ", ".join(missing_paths)
        raise RuntimeError(f"FAST path is missing required files: {joined_paths}")


def _prepare_aircraft(aircraft):
    """Normalize Python aircraft input into the structure expected by FAST."""

    if not isinstance(aircraft, dict):
        return aircraft

    aircraft = deepcopy(aircraft)

    try:
        propulsion = aircraft["Specs"]["Propulsion"]
    except KeyError:
        return aircraft

    prop_arch = propulsion.get("PropArch")

    if isinstance(prop_arch, dict):
        arch_type = prop_arch.get("Type")
    else:
        arch_type = prop_arch

    if not isinstance(arch_type, str):
        return aircraft

    arch_type = arch_type.upper()

    if arch_type == "O":
        graph = propulsion.get("PropArchGraph")

        if graph is None:
            raise ValueError('PropArchGraph is required when "PropArch" is "O".')

        prop_arch = deepcopy(graph)
        prop_arch["Type"] = "O"

        for field_name in ("SrcType", "TrnType"):
            if field_name in prop_arch:
                value = prop_arch[field_name]

                if (
                    not isinstance(value, MatlabRow)
                    and (isinstance(value, list) or isinstance(value, tuple))
                ):
                    prop_arch[field_name] = MatlabRow(prop_arch[field_name])

        propulsion["PropArch"] = prop_arch
        del propulsion["PropArchGraph"]
        return aircraft

    propulsion["PropArch"] = {"Type": arch_type}
    propulsion.pop("PropArchGraph", None)
    return aircraft


def _extract_mission_profile(aircraft):
    """Remove and return the mission profile embedded in aircraft input."""

    try:
        mission_container = aircraft.pop("Mission")
        mission = mission_container["Profile"]
    except (KeyError, TypeError) as error:
        raise ValueError("InputAircraft must include Mission.Profile for FAST runs.") from error

    if not isinstance(mission, dict):
        raise ValueError("InputAircraft Mission.Profile must be an object.")

    return mission


def _to_matlab_literal(value):
    """Convert supported Python values into MATLAB literal source text."""

    if isinstance(value, MatlabExpression):
        return value.value

    if isinstance(value, MatlabRow):
        return _to_matlab_row(value.value)

    if isinstance(value, dict):
        fields = []

        for key, item in value.items():
            if not VALID_STRUCT_FIELD.match(key):
                raise ValueError(f"Invalid MATLAB struct field name: {key}")

            fields.append(f'"{key}", {_to_matlab_literal(item)}')

        if not fields:
            return "struct()"

        return f"struct({', '.join(fields)})"

    if isinstance(value, str):
        escaped_value = value.replace('"', '""')
        return f'"{escaped_value}"'

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int) or isinstance(value, float):
        if value != value:
            return "NaN"

        return repr(value)

    if value is None:
        return "[]"

    if isinstance(value, list) or isinstance(value, tuple):
        return _to_matlab_array(value)

    raise TypeError(f"Unsupported MATLAB literal value: {value!r}")


def _to_matlab_array(value):
    """Convert Python list or tuple input into a MATLAB array literal."""

    if not value:
        return "[]"

    if all(isinstance(item, str) for item in value):
        rows = [_to_matlab_literal(item) for item in value]
        return "[" + "; ".join(rows) + "]"

    if all(not isinstance(item, list) and not isinstance(item, tuple) for item in value):
        rows = [_to_matlab_literal(item) for item in value]
        return "[" + "; ".join(rows) + "]"

    rows = []

    for row in value:
        if not isinstance(row, list) and not isinstance(row, tuple):
            raise TypeError("MATLAB matrix rows must all be lists or tuples.")

        rows.append(", ".join(_to_matlab_literal(item) for item in row))

    return "[" + "; ".join(rows) + "]"


def _to_matlab_row(value):
    """Convert a one-dimensional Python sequence into a MATLAB row vector."""

    if not value:
        return "[]"

    if any(isinstance(item, list) or isinstance(item, tuple) for item in value):
        raise TypeError("MATLAB row values must be one-dimensional.")

    return "[" + ", ".join(_to_matlab_literal(item) for item in value) + "]"


def _to_python_data(value):
    """Convert MATLAB Engine return values into ordinary Python data."""

    if value is None or isinstance(value, str):
        return value

    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value

    if isinstance(value, dict):
        return {
            key: _to_python_data(item)
            for key, item in value.items()
        }

    struct_fields = _matlab_struct_fields(value)

    if struct_fields is not None:
        return {
            key: _to_python_data(value[key])
            for key in struct_fields
        }

    if isinstance(value, list) or isinstance(value, tuple):
        return _convert_sequence(value)

    if _looks_like_matlab_array(value):
        return _convert_sequence(list(value))

    return value


def _matlab_struct_fields(value):
    """Return MATLAB struct field names when value behaves like a struct."""

    if not hasattr(value, "__getitem__"):
        return None

    keys = None

    if hasattr(value, "keys"):
        try:
            keys = list(value.keys())
        except TypeError:
            keys = None

    for attribute_name in ("fieldnames", "_fieldnames"):
        if keys is not None or not hasattr(value, attribute_name):
            continue

        attribute = getattr(value, attribute_name)

        try:
            if callable(attribute):
                keys = list(attribute())
            else:
                keys = list(attribute)
        except TypeError:
            keys = None

    if keys is None:
        return None

    if not all(isinstance(key, str) for key in keys):
        return None

    return keys


def _looks_like_matlab_array(value):
    """Detect MATLAB Engine array containers without importing matlab types."""

    module_name = type(value).__module__

    return (
        (module_name == "matlab" or module_name.startswith("matlab."))
        and hasattr(value, "__iter__")
        and not isinstance(value, str)
    )


def _convert_sequence(value):
    """Recursively convert list-like values returned by MATLAB Engine."""

    items = [_to_python_data(item) for item in value]

    if len(items) == 1 and not isinstance(items[0], dict):
        return items[0]

    return items


def _drop_output_fields(output):
    """Remove FAST fields that are not part of reusable OutputAircraft data."""

    for path in OUTPUT_FIELDS_TO_REMOVE:
        current = output

        for key in path[:-1]:
            if not isinstance(current, dict):
                current = None
                break

            current = current.get(key)

        if isinstance(current, dict):
            current.pop(path[-1], None)
