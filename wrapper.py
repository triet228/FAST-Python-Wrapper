# wrapper.py
import os
import re
from copy import deepcopy
from pathlib import Path


DEFAULT_SPEC_NAME = "ERJ175LR"
DEFAULT_MISSION_NAME = "ERJ_ClimbThenAccel"
VALID_MATLAB_NAME = re.compile(r"^[A-Za-z]\w*$")
VALID_STRUCT_FIELD = re.compile(r"^[A-Za-z]\w*$")


class MatlabExpression:
    def __init__(self, value):
        self.value = value


def matlab_expr(value):
    return MatlabExpression(value)


class FastWrapper:
    def __init__(self, fast_path=None):
        self.fast_path = self._resolve_fast_path(fast_path)
        self.engine = None

    def start(self):
        if self.engine:
            return self

        try:
            import matlab.engine
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "MATLAB Engine for Python is not installed in this environment."
            ) from error

        self.engine = matlab.engine.start_matlab()
        self.engine.addpath(self.engine.genpath(str(self.fast_path)), nargout=0)
        return self

    def stop(self):
        if self.engine:
            self.engine.quit()
            self.engine = None

    def run(self, spec_name=None, mission_name=None, aircraft=None, mission=None):
        self._require_engine()

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

        aircraft = self._prepare_aircraft(aircraft)
        aircraft_literal = self._to_matlab_literal(aircraft)
        mission_literal = self._to_matlab_literal(mission)

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
        raw_path = fast_path or os.environ.get("FAST_PATH")

        if not raw_path:
            raise RuntimeError(
                "FAST path is required. Pass fast_path or set FAST_PATH."
            )

        path = Path(raw_path).expanduser().resolve()
        self._validate_fast_path(path)
        return path

    def _validate_fast_path(self, path):
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
            graph = propulsion.get("PropArchGraph")

            if graph is None:
                raise ValueError(
                    'PropArchGraph is required when "PropArch" is "O".'
                )

            prop_arch = deepcopy(graph)
            prop_arch["Type"] = "O"
            propulsion["PropArch"] = prop_arch
            del propulsion["PropArchGraph"]
            return aircraft

        propulsion["PropArch"] = {"Type": arch_type}
        propulsion.pop("PropArchGraph", None)
        return aircraft

    def _to_matlab_literal(self, value):
        if isinstance(value, MatlabExpression):
            return value.value

        if isinstance(value, dict):
            fields = []

            for key, item in value.items():
                if not VALID_STRUCT_FIELD.match(key):
                    raise ValueError(f"Invalid MATLAB struct field name: {key}")

                fields.append(f'"{key}", {self._to_matlab_literal(item)}')

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
            return self._to_matlab_array(value)

        raise TypeError(f"Unsupported MATLAB literal value: {value!r}")

    def _to_matlab_array(self, value):
        if not value:
            return "[]"

        if all(isinstance(item, str) for item in value):
            rows = [self._to_matlab_literal(item) for item in value]
            return "[" + "; ".join(rows) + "]"

        if all(not isinstance(item, list) and not isinstance(item, tuple) for item in value):
            rows = [self._to_matlab_literal(item) for item in value]
            return "[" + "; ".join(rows) + "]"

        rows = []

        for row in value:
            if not isinstance(row, list) and not isinstance(row, tuple):
                raise TypeError("MATLAB matrix rows must all be lists or tuples.")

            rows.append(", ".join(self._to_matlab_literal(item) for item in row))

        return "[" + "; ".join(rows) + "]"

    def _get_nested(self, value, keys):
        current = value

        for key in keys:
            current = current[key]

        return current
