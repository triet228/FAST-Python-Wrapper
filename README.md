# FAST Python Wrapper

Unofficial Python wrapper for running FAST through MATLAB Engine.

Use this repo as a lightweight integration layer around a local FAST installation.

This project does not include FAST or MATLAB Engine. Each user needs a local FAST checkout and a working MATLAB Engine for Python installation.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `main.py`: direct local script with editable Python `AIRCRAFT`, `MISSION`, and propulsion graph inputs.
- `pyproject.toml`: project metadata and Python dependencies.

## Requirements

- Python 3.10 or newer supported by your MATLAB release
- MATLAB
- MATLAB Engine for Python
- A local FAST repo

This repo has been smoke-tested on Windows with:

- Conda environment `fast_python_wrapper`
- Python 3.11
- MATLAB R2025b
- FAST checkout at `C:\Users\homin\Projects\FAST`

Install the Python dependencies:

```powershell
python -m pip install -e .
```

Install MATLAB Engine for Python from your local MATLAB installation if `import matlab.engine` does not work. For MATLAB R2025b, use Python 3.9, 3.10, 3.11, or 3.12.

If MathWorks' local installer cannot build directly from `C:\Program Files`, copy the engine package into a writable temporary folder and install from there, or install the shipped `matlab` package into the environment with paths pointing back to the MATLAB installation.

## FAST Path

Set `FAST_PATH` at the top of `main.py` to the local FAST repo path. The path must contain:

```text
Main.m
+AircraftSpecsPkg/
+MissionProfilesPkg/
```

You can also pass the path directly in Python. This package-style mode runs aircraft and mission functions already available inside the FAST checkout:

```python
from wrapper import FastWrapper

with FastWrapper("C:/Users/your-name/Projects/FAST") as fast:
    result = fast.run("ERJ175LR", "ERJ_ClimbThenAccel")

print(result)
```

## Run Directly

```powershell
python main.py
```

With the tested Windows setup above:

```powershell
conda activate fast_python_wrapper
python main.py
```

The current custom graph example returns a successful result with `mtow` near `57537.66416956265` kg. FAST may also print a thrust overconstraint warning before the iteration log.

The wrapper also returns the full FAST output aircraft struct converted into
plain Python dictionaries and lists:

```python
result = fast.run(aircraft=AIRCRAFT, mission=MISSION)
aircraft = result["aircraft"]

mtow = aircraft["Specs"]["Weight"]["MTOW"]
mission_profile = aircraft["Mission"]["Profile"]
```

`main.py` is the main editable entry point. It defines FAST inputs as Python dictionaries:

```python
AIRCRAFT = {...}
MISSION = {...}
GRAPH_BASED_PROPULSION = {...}
```

Use plain Python values for constants, `nan` for FAST fields that should remain unspecified, and `m("...")` for MATLAB expressions such as `UnitConversionPkg` conversions or `EngineModelPkg` references.

The aircraft propulsion architecture is selected with:

```python
"PropArch": "O"
```

FAST built-in propulsion architecture codes can be used directly:

```python
"PropArch": "C"    # conventional
"PropArch": "E"    # fully electric
"PropArch": "PHE"  # parallel hybrid electric
"PropArch": "SHE"  # series hybrid electric
"PropArch": "TE"   # turboelectric
"PropArch": "PE"   # partially turboelectric
```

When `PropArch` is `"O"`, `main.py` attaches `GRAPH_BASED_PROPULSION` as `PropArchGraph`. The wrapper converts that Python structure into the MATLAB struct expected by FAST's graph-based propulsion architecture path. If `PropArch` is any built-in code such as `"C"` or `"E"`, the graph is ignored.
