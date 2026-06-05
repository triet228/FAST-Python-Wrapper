# wrapper.py
import re
from copy import deepcopy
from pathlib import Path


DEFAULT_SPEC_NAME = "ERJ175LR"
DEFAULT_MISSION_NAME = "ERJ_ClimbThenAccel"

# MATLAB package/function names are inserted into a MATLAB command string.
# Keep them limited to plain identifiers so user input cannot escape into
# arbitrary MATLAB code.
VALID_MATLAB_NAME = re.compile(r"^[A-Za-z]\w*$")
VALID_STRUCT_FIELD = re.compile(r"^[A-Za-z]\w*$")


class MatlabExpression:
    # Values wrapped in this class are copied into the MATLAB script as code.
    # Use it for expressions such as UnitConversionPkg.ConvLength(...) or
    # EngineModelPkg.EngineSpecsPkg.CF34_8E5 that must be evaluated by MATLAB.
    def __init__(self, value):
        self.value = value


class MatlabRow:
    # Most Python lists become MATLAB column vectors because FAST mission
    # arrays are column-oriented. A few graph metadata fields must stay as row
    # vectors, so this wrapper marks those lists before literal conversion.
    def __init__(self, value):
        self.value = value


def matlab_expr(value):
    # Public helper used by main.py as m("...").
    return MatlabExpression(value)


class FastWrapper:
    def __init__(self, fast_path=None):
        # Validate the FAST checkout up front. Failing here gives a short Python
        # error instead of a later MATLAB path-resolution failure.
        self.fast_path = self._resolve_fast_path(fast_path)
        self.engine = None

    def start(self):
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
        # such as +AircraftSpecsPkg and +MissionProfilesPkg are visible.
        self.engine = matlab.engine.start_matlab()
        self.engine.addpath(self.engine.genpath(str(self.fast_path)), nargout=0)
        return self

    def stop(self):
        # MATLAB Engine owns an external MATLAB process. Explicitly quitting it
        # avoids leaving background MATLAB sessions after scripts or servers end.
        if self.engine:
            self.engine.quit()
            self.engine = None

    def run(self, spec_name=None, mission_name=None, aircraft=None, mission=None):
        self._require_engine()

        # There are two run modes:
        # 1. Python-defined aircraft/mission dictionaries from main.py.
        # 2. Existing FAST package functions by name, such as ERJ175LR.
        if aircraft is not None or mission is not None:
            return self._run_structs(aircraft, mission)

        spec_name = spec_name or DEFAULT_SPEC_NAME
        mission_name = mission_name or DEFAULT_MISSION_NAME
        self._validate_matlab_name(spec_name, "spec_name")
        self._validate_matlab_name(mission_name, "mission_name")

        log = self.engine.evalc(
            f"""
            aircraft_spec = AircraftSpecsPkg.{spec_name};
            mission_profile = @MissionProfilesPkg.{mission_name};
            fast_result = Main(aircraft_spec, mission_profile);
            """,
            nargout=1,
        )

        # MATLAB Engine exposes MATLAB workspace variables through a mapping.
        # Pull only the values the wrapper promises in its Python response.
        fast_result = self.engine.workspace["fast_result"]
        mtow = self._get_nested(fast_result, ["Specs", "Weight", "MTOW"])

        return {
            "status": "success",
            "spec_name": spec_name,
            "mission_name": mission_name,
            "mtow": float(mtow),
            "log": log,
        }

    def _run_structs(self, aircraft, mission):
        if aircraft is None or mission is None:
            raise ValueError("aircraft and mission must be provided together.")

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
        mtow = self._get_nested(fast_result, ["Specs", "Weight", "MTOW"])

        return {
            "status": "success",
            "mtow": float(mtow),
            "log": log,
        }

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def _resolve_fast_path(self, fast_path):
        if not fast_path:
            raise RuntimeError("FAST path is required.")

        path = Path(fast_path).expanduser().resolve()
        self._validate_fast_path(path)
        return path

    def _validate_fast_path(self, path):
        # These files/folders are the minimum needed for the wrapper's two
        # supported modes: calling Main.m and resolving built-in spec/mission
        # package functions.
        if not path.exists() or not path.is_dir():
            raise RuntimeError(f"FAST path does not exist: {path}")

        required_paths = [
            path / "Main.m",
            path / "+AircraftSpecsPkg",
            path / "+MissionProfilesPkg",
        ]
        missing_paths = [str(item) for item in required_paths if not item.exists()]

        if missing_paths:
            joined_paths = ", ".join(missing_paths)
            raise RuntimeError(f"FAST path is missing required files: {joined_paths}")

    def _require_engine(self):
        if not self.engine:
            raise RuntimeError("MATLAB engine is not running. Call start() first.")

    def _validate_matlab_name(self, value, field_name):
        if not VALID_MATLAB_NAME.match(value):
            raise ValueError(f"{field_name} must be a simple MATLAB identifier.")

    def _prepare_aircraft(self, aircraft):
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
        if not value:
            return "[]"

        # Keep row conversion narrow. It is currently for graph metadata only,
        # not a general replacement for mission/array conversion.
        if any(isinstance(item, list) or isinstance(item, tuple) for item in value):
            raise TypeError("MATLAB row values must be one-dimensional.")

        return "[" + ", ".join(self._to_matlab_literal(item) for item in value) + "]"

    def _get_nested(self, value, keys):
        # MATLAB structs returned through Engine behave like nested mappings.
        current = value

        for key in keys:
            current = current[key]

        return current
