# wrapper.py
import os
import re
from copy import deepcopy
from shutil import copyfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VALID_STRUCT_FIELD = re.compile(r"^[A-Za-z]\w*$")


class MatlabExpression:
    """Store MATLAB code that should be inserted as an expression.

    Inputs:
        value: MATLAB expression text, such as a UnitConversionPkg call.

    Outputs:
        A wrapper object consumed by FastWrapper._to_matlab_literal().

    Assumptions:
        The caller provides trusted MATLAB code. This class intentionally does
        not escape or validate the expression because it is meant to preserve
        native FAST syntax.
    """

    # Values wrapped in this class are copied into the MATLAB script as code.
    # Use it for expressions such as UnitConversionPkg.ConvLength(...) or
    # EngineModelPkg.EngineSpecsPkg.CF34_8E5 that must be evaluated by MATLAB.
    def __init__(self, value):
        self.value = value


class MatlabRow:
    """Mark a Python sequence that must become a MATLAB row vector.

    Inputs:
        value: One-dimensional list or tuple.

    Outputs:
        A wrapper object consumed by FastWrapper._to_matlab_literal().

    Assumptions:
        FAST mission arrays normally use column vectors, so row vectors are only
        requested explicitly for graph metadata fields that MATLAB compares by
        component index.
    """

    # Most Python lists become MATLAB column vectors because FAST mission
    # arrays are column-oriented. A few graph metadata fields must stay as row
    # vectors, so this wrapper marks those lists before literal conversion.
    def __init__(self, value):
        self.value = value


def matlab_expr(value):
    """Return a MATLAB expression wrapper for values defined in Python specs."""

    # Public helper used by main.py as m("...").
    return MatlabExpression(value)


def load_env_file():
    """Load local environment variables from the project .env file.

    Inputs:
        None. The project root is inferred from this file location.

    Outputs:
        None. os.environ is updated for keys that are not already set.

    Side effects:
        Copies .env.example to .env when .env is missing and the example file
        exists. Existing process environment variables take priority over file
        values.
    """

    # Load local machine paths from .env, copying .env.example on first run.
    env_path = PROJECT_ROOT / ".env"
    example_env_path = PROJECT_ROOT / ".env.example"

    if not env_path.exists():
        if example_env_path.exists():
            copyfile(example_env_path, env_path)
        else:
            return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def required_env_path(name):
    """Return a required environment path value.

    Inputs:
        name: Environment variable name to read, such as FAST_PATH.

    Outputs:
        The configured path string.

    Assumptions:
        Placeholder values containing "\\path\\to" are invalid because they are
        template paths and cannot point to a usable FAST checkout.
    """

    # Require a configured environment path before calling FAST.
    value = os.environ.get(name, "").strip()

    if not value or r"\path\to\\" in value or r"\path\to" in value:
        raise RuntimeError(
            f"{name} is required. Edit .env and set {name} for your machine."
        )

    return value


class FastWrapper:
    """Run FAST through MATLAB Engine using Python-defined inputs.

    Inputs:
        fast_path: Local FAST checkout path containing Main.m.

    Outputs:
        run() returns a dictionary with status, mtow, converted aircraft data,
        and the captured MATLAB command-window log.

    Side effects:
        start() launches MATLAB, adds FAST to the MATLAB path, and stop() quits
        the MATLAB process.
    """

    def __init__(self, fast_path=None):
        # Validate the FAST checkout up front. Failing here gives a short Python
        # error instead of a later MATLAB path-resolution failure.
        self.fast_path = self._resolve_fast_path(fast_path)
        self.engine = None

    def start(self):
        """Start MATLAB Engine and add the FAST checkout to MATLAB's path."""

        # Reuse an already-running engine if the caller starts the wrapper once
        # and runs multiple FAST cases through the same object.
        if self.engine:
            return self

        try:
            import matlab.engine
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "MATLAB Engine for Python is not installed in this environment."
            ) from error

        # Start MATLAB once, then add the whole FAST tree so package folders
        # and helper functions are visible.
        self.engine = matlab.engine.start_matlab()
        self.engine.addpath(self.engine.genpath(str(self.fast_path)), nargout=0)
        return self

    def stop(self):
        """Stop the MATLAB Engine session owned by this wrapper."""

        # MATLAB Engine owns an external MATLAB process. Explicitly quitting it
        # avoids leaving background MATLAB sessions after scripts or servers end.
        if self.engine:
            self.engine.quit()
            self.engine = None

    def run(self, aircraft, mission):
        """Run FAST with Python dictionaries for aircraft and mission inputs.

        Inputs:
            aircraft: Nested dictionary matching the FAST Aircraft structure.
            mission: Nested dictionary matching the FAST Mission.Profile fields.

        Outputs:
            Dictionary containing:
            - status: "success" when Main.m completes.
            - mtow: maximum takeoff weight in kg from FAST output.
            - aircraft: FAST output Aircraft structure converted to Python.
            - log: MATLAB command-window text captured during the run.
        """

        self._require_engine()

        # Convert Python dictionaries into MATLAB struct(...) literals. This is
        # slower than passing raw MATLAB objects, but it keeps main.py editable
        # with ordinary Python data and works without a separate schema layer.
        aircraft = self._prepare_aircraft(aircraft)
        aircraft_literal = self._to_matlab_literal(aircraft)
        mission_literal = self._to_matlab_literal(mission)

        # FAST wants mission_profile to be a function handle that accepts the
        # Aircraft struct and attaches the mission profile. The anonymous
        # function mirrors the behavior of FAST's package mission functions.
        log = self.engine.evalc(
            f"""
            aircraft_spec = {aircraft_literal};
            mission_profile = @(Aircraft) setfield(Aircraft, "Mission", "Profile", {mission_literal});
            fast_result = Main(aircraft_spec, mission_profile);
            """,
            nargout=1,
        )

        fast_result = self.engine.workspace["fast_result"]
        aircraft = self._to_python_data(fast_result)
        mtow = self._get_nested(fast_result, ["Specs", "Weight", "MTOW"])

        return {
            "status": "success",
            "mtow": float(mtow),
            "aircraft": aircraft,
            "log": log,
        }

    def __enter__(self):
        """Start MATLAB when entering a with-block."""

        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        """Quit MATLAB when leaving a with-block."""

        self.stop()

    def _resolve_fast_path(self, fast_path):
        """Resolve and validate the configured FAST checkout path."""

        if not fast_path:
            raise RuntimeError("FAST path is required.")

        path = Path(fast_path).expanduser().resolve()
        self._validate_fast_path(path)
        return path

    def _validate_fast_path(self, path):
        """Check that the FAST checkout has the entry point used by wrapper."""

        # Main.m is the FAST entry point. The wrapper adds the whole FAST tree
        # to MATLAB's path so package dependencies are resolved by MATLAB.
        if not path.exists() or not path.is_dir():
            raise RuntimeError(f"FAST path does not exist: {path}")

        required_paths = [path / "Main.m"]
        missing_paths = [str(item) for item in required_paths if not item.exists()]

        if missing_paths:
            joined_paths = ", ".join(missing_paths)
            raise RuntimeError(f"FAST path is missing required files: {joined_paths}")

    def _require_engine(self):
        """Fail early if a FAST run is attempted before MATLAB starts."""

        if not self.engine:
            raise RuntimeError("MATLAB engine is not running. Call start() first.")

    def _prepare_aircraft(self, aircraft):
        """Normalize Python aircraft input into the structure expected by FAST.

        Inputs:
            aircraft: User-editable Python aircraft dictionary.

        Outputs:
            A deep-copied aircraft dictionary safe to convert to MATLAB code.

        Side effects:
            None. The original input dictionary is not modified.
        """

        # Work on a copy so callers can reuse their original Python dictionaries
        # after a run without hidden mutations from wrapper normalization.
        aircraft = deepcopy(aircraft)

        try:
            propulsion = aircraft["Specs"]["Propulsion"]
        except KeyError:
            return aircraft

        prop_arch = propulsion.get("PropArch")

        if not isinstance(prop_arch, str):
            return aircraft

        arch_type = prop_arch.upper()

        if arch_type == "O":
            # FAST uses "O" for a user-supplied graph architecture. main.py
            # stores the large graph as PropArchGraph to keep the selector simple;
            # MATLAB expects the graph fields under PropArch itself.
            graph = propulsion.get("PropArchGraph")

            if graph is None:
                raise ValueError(
                    'PropArchGraph is required when "PropArch" is "O".'
                )

            prop_arch = deepcopy(graph)
            prop_arch["Type"] = "O"

            for field_name in ("SrcType", "TrnType"):
                if field_name in prop_arch:
                    # FAST compares these vectors against transmitter/source
                    # counts as row vectors. If sent as columns, MATLAB's
                    # implicit expansion can produce invalid component indices.
                    prop_arch[field_name] = MatlabRow(prop_arch[field_name])

            propulsion["PropArch"] = prop_arch
            del propulsion["PropArchGraph"]
            return aircraft

        # Built-in FAST architectures need only a Type field. Removing a custom
        # graph here avoids accidentally sending stale graph data with "C", "E",
        # "PHE", and the other built-in architecture codes.
        propulsion["PropArch"] = {"Type": arch_type}
        propulsion.pop("PropArchGraph", None)
        return aircraft

    def _to_matlab_literal(self, value):
        """Convert supported Python values into MATLAB literal source text."""

        # This function intentionally handles only the data types used by FAST
        # inputs. If a new type is needed, add it explicitly so unsupported
        # values fail before MATLAB receives malformed code.
        if isinstance(value, MatlabExpression):
            return value.value

        if isinstance(value, MatlabRow):
            return self._to_matlab_row(value.value)

        if isinstance(value, dict):
            fields = []

            for key, item in value.items():
                # struct field names are also written into MATLAB code.
                if not VALID_STRUCT_FIELD.match(key):
                    raise ValueError(f"Invalid MATLAB struct field name: {key}")

                fields.append(f'"{key}", {self._to_matlab_literal(item)}')

            if not fields:
                return "struct()"

            return f"struct({', '.join(fields)})"

        if isinstance(value, str):
            # MATLAB double-quoted strings escape a quote by doubling it.
            escaped_value = value.replace('"', '""')
            return f'"{escaped_value}"'

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, int) or isinstance(value, float):
            # NaN is used heavily in FAST to request preprocessing defaults or
            # regression-filled values. Python NaN is the only float unequal to
            # itself, which gives a dependency-free check.
            if value != value:
                return "NaN"

            return repr(value)

        if value is None:
            return "[]"

        if isinstance(value, list) or isinstance(value, tuple):
            return self._to_matlab_array(value)

        raise TypeError(f"Unsupported MATLAB literal value: {value!r}")

    def _to_matlab_array(self, value):
        """Convert Python list or tuple input into a MATLAB array literal."""

        if not value:
            return "[]"

        # One-dimensional mission arrays are represented as MATLAB columns.
        # FAST mission fields are aligned by row, so a Python list of N values
        # should become an N-by-1 MATLAB array.
        if all(isinstance(item, str) for item in value):
            rows = [self._to_matlab_literal(item) for item in value]
            return "[" + "; ".join(rows) + "]"

        if all(not isinstance(item, list) and not isinstance(item, tuple) for item in value):
            rows = [self._to_matlab_literal(item) for item in value]
            return "[" + "; ".join(rows) + "]"

        # Nested lists are treated as MATLAB matrices. Each nested list is a
        # MATLAB row, which is what FAST's architecture and efficiency matrices
        # expect.
        rows = []

        for row in value:
            if not isinstance(row, list) and not isinstance(row, tuple):
                raise TypeError("MATLAB matrix rows must all be lists or tuples.")

            rows.append(", ".join(self._to_matlab_literal(item) for item in row))

        return "[" + "; ".join(rows) + "]"

    def _to_matlab_row(self, value):
        """Convert a one-dimensional Python sequence into a MATLAB row vector."""

        if not value:
            return "[]"

        # Keep row conversion narrow. It is currently for graph metadata only,
        # not a general replacement for mission/array conversion.
        if any(isinstance(item, list) or isinstance(item, tuple) for item in value):
            raise TypeError("MATLAB row values must be one-dimensional.")

        return "[" + ", ".join(self._to_matlab_literal(item) for item in value) + "]"

    def _get_nested(self, value, keys):
        """Read a nested field from a MATLAB struct-like object."""

        # MATLAB structs returned through Engine behave like nested mappings.
        current = value

        for key in keys:
            current = current[key]

        return current

    def _to_python_data(self, value):
        """Convert MATLAB Engine return values into ordinary Python data."""

        # MATLAB Engine returns a mix of Python scalars, matlab arrays, and
        # struct-like objects. Normalize only recognized containers so unknown
        # values remain available instead of being lossy-converted.
        if value is None or isinstance(value, str):
            return value

        if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
            return value

        if isinstance(value, dict):
            return {
                key: self._to_python_data(item)
                for key, item in value.items()
            }

        struct_fields = self._matlab_struct_fields(value)

        if struct_fields is not None:
            return {
                key: self._to_python_data(value[key])
                for key in struct_fields
            }

        if isinstance(value, list) or isinstance(value, tuple):
            return self._convert_sequence(value)

        if self._looks_like_matlab_array(value):
            return self._convert_sequence(list(value))

        return value

    def _matlab_struct_fields(self, value):
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

    def _looks_like_matlab_array(self, value):
        """Detect MATLAB Engine array containers without importing matlab types."""

        module_name = type(value).__module__

        return (
            module_name.startswith("matlab.")
            and hasattr(value, "__iter__")
            and not isinstance(value, str)
        )

    def _convert_sequence(self, value):
        """Recursively convert list-like values returned by MATLAB Engine."""

        items = [self._to_python_data(item) for item in value]

        if len(items) == 1 and not isinstance(items[0], dict):
            return items[0]

        return items
