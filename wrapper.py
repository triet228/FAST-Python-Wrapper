# wrapper.py

import re
from copy import deepcopy
from pathlib import Path


VALID_STRUCT_FIELD = re.compile(r"^[A-Za-z]\w*$")
PROP_ARCH_TYPES = ("C", "E", "TE")
OUTPUT_FIELDS_TO_REMOVE = (
    ("Geometry", "Preset"),
    ("Mission", "ProfileFxn"),
    ("Settings", "Dir", "Size"),
)


def matlab_expr(value):
    """Return a marker for MATLAB expressions embedded in Python specs."""

    return {
        "_matlab_expression": value,
    }


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
            prop_arch_type = _prop_arch_type(aircraft)
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
            _clean_output_fields(output, prop_arch_type)

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
    """Start MATLAB Engine and add FAST packages/functions to the path.

    Inputs:
        fast_path: Validated FAST checkout containing Main.m.

    Outputs:
        A running MATLAB Engine object ready to evaluate FAST scripts.

    Side effects:
        Launches an external MATLAB process. wrap() is responsible for quitting
        it after the run finishes or fails.
    """

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
    """Resolve and validate the configured FAST checkout path.

    Inputs:
        fast_path: Path-like value pointing to a local FAST checkout.

    Outputs:
        Absolute Path to the checkout.

    Assumptions:
        Main.m is the stable FAST entry point used by this Python wrapper.
    """

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
    """Normalize InputAircraft without mutating the caller's dictionary.

    Inputs:
        aircraft: Python InputAircraft dictionary.

    Outputs:
        Deep-copied aircraft dictionary ready for MATLAB literal conversion.

    Assumptions:
        For now the wrapper only supports propulsion architecture types C, E,
        and TE. Any legacy PropArch companion fields are removed so stale graph
        architecture data cannot leak into a conventional run.
    """

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

    if arch_type not in PROP_ARCH_TYPES:
        joined_types = ", ".join(PROP_ARCH_TYPES)
        raise ValueError(f"PropArch.Type must be one of: {joined_types}.")

    propulsion["PropArch"] = {"Type": arch_type}

    for field_name in list(propulsion):
        if field_name.startswith("PropArch") and field_name != "PropArch":
            del propulsion[field_name]

    return aircraft


def _prop_arch_type(aircraft):
    """Return the supported PropArch type used to label cleaned FAST output."""

    try:
        arch_type = aircraft["Specs"]["Propulsion"]["PropArch"]["Type"]
    except (KeyError, TypeError):
        return None

    if not isinstance(arch_type, str):
        return None

    arch_type = arch_type.upper()

    if arch_type in PROP_ARCH_TYPES:
        return arch_type

    return None


def _extract_mission_profile(aircraft):
    """Remove and return the mission profile embedded in InputAircraft.

    Inputs:
        aircraft: Prepared aircraft dictionary that still contains Mission.

    Outputs:
        Mission.Profile dictionary passed into FAST's mission_profile handle.

    Side effects:
        Mutates the prepared copy by removing Mission before aircraft_spec is
        converted to MATLAB. FAST receives mission data through the function
        handle, not as a standalone top-level aircraft field.
    """

    try:
        mission_container = aircraft.pop("Mission")
        mission = mission_container["Profile"]
    except (KeyError, TypeError) as error:
        raise ValueError("InputAircraft must include Mission.Profile for FAST runs.") from error

    if not isinstance(mission, dict):
        raise ValueError("InputAircraft Mission.Profile must be an object.")

    return mission


def _to_matlab_literal(value):
    """Convert supported Python values into MATLAB literal source text.

    Inputs:
        value: JSON-like Python value or one of the explicit MATLAB marker
            dictionaries loaded from InputAircraft.json.

    Outputs:
        MATLAB source text safe to splice into the generated evalc script.

    Assumptions:
        This is intentionally narrow. Unsupported objects fail in Python so
        MATLAB does not receive malformed struct(...) source.
    """

    if isinstance(value, dict):
        keys = set(value)

        if keys == {"_matlab_expression"}:
            return value["_matlab_expression"]

        if keys == {"_matlab_row"}:
            return _to_matlab_row(value["_matlab_row"])

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
    """Convert Python list or tuple input into a MATLAB array literal.

    Assumptions:
        One-dimensional lists are column vectors because FAST mission arrays
        align by segment row. Nested lists are matrices whose inner lists are
        MATLAB rows. The _matlab_row marker is the explicit escape hatch for
        row vectors.
    """

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
    """Convert MATLAB Engine return values into ordinary Python data.

    Outputs:
        Nested dictionaries, lists, and scalars suitable for OutputAircraft.

    Assumptions:
        MATLAB Engine exposes structs and arrays with different Python shapes
        across releases, so detection is capability-based instead of importing
        concrete matlab.* classes.
    """

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
    """Recursively convert list-like values returned by MATLAB Engine.

    Assumptions:
        MATLAB scalar arrays often arrive as one-item containers. Collapsing
        those keeps scalar OutputAircraft fields as scalars in Python dicts.
    """

    items = [_to_python_data(item) for item in value]

    if len(items) == 1 and not isinstance(items[0], dict):
        return items[0]

    return items


def _clean_output_fields(output, prop_arch_type=None):
    """Remove FAST runtime fields from reusable OutputAircraft data.

    Inputs:
        output: Python dictionary converted from MATLAB OutputAircraft.
        prop_arch_type: Input PropArch type used when FAST returns an internal
            expanded architecture object instead of C, E, or TE.

    Side effects:
        Mutates output in place. The result is the public OutputAircraft dict
        returned by wrap() and used by the JSON fixtures.
    """

    for path in OUTPUT_FIELDS_TO_REMOVE:
        current = output

        for key in path[:-1]:
            if not isinstance(current, dict):
                current = None
                break

            current = current.get(key)

        if isinstance(current, dict):
            current.pop(path[-1], None)

    settings = output.get("Settings")

    if isinstance(settings, dict):
        for key in list(settings):
            key_text = key.lower()

            if key_text.startswith("narg") and "oper" in key_text:
                del settings[key]

    _clean_prop_arch_fields(output, prop_arch_type)


def _clean_prop_arch_fields(value, fallback_type=None):
    """Keep every PropArch object limited to Type for supported architectures.

    Assumptions:
        FAST may expand TE into internal graph-like data. The wrapper currently
        supports only the public architecture labels C, E, and TE, so expanded
        fields are intentionally removed from output.
    """

    if isinstance(value, dict):
        for key, item in list(value.items()):
            if key == "PropArch" and isinstance(item, dict):
                arch_type = item.get("Type")

                if isinstance(arch_type, str):
                    arch_type = arch_type.upper()

                if arch_type not in PROP_ARCH_TYPES:
                    arch_type = fallback_type

                if arch_type in PROP_ARCH_TYPES:
                    value[key] = {
                        "Type": arch_type,
                    }
                else:
                    value[key] = {}

                continue

            _clean_prop_arch_fields(item, fallback_type)

        return

    if isinstance(value, list):
        for item in value:
            _clean_prop_arch_fields(item, fallback_type)
