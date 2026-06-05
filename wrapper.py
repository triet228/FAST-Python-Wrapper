# wrapper.py
import os
import re
from pathlib import Path


DEFAULT_SPEC_NAME = "ERJ175LR"
DEFAULT_MISSION_NAME = "ERJ_ClimbThenAccel"
VALID_MATLAB_NAME = re.compile(r"^[A-Za-z]\w*$")


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

    def run(self, spec_name=None, mission_name=None):
        self._require_engine()

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

    def _get_nested(self, value, keys):
        current = value

        for key in keys:
            current = current[key]

        return current
