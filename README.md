# FAST Python Wrapper

Unofficial Python wrapper for running FAST through MATLAB Engine.

Use this repo as a lightweight integration layer around a local FAST installation.

This project does not include FAST or MATLAB Engine. Each user needs a local FAST checkout and a working MATLAB Engine for Python installation.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `api.py`: optional FastAPI server.
- `main.py`: direct local script with editable Python `AIRCRAFT`, `MISSION`, and propulsion graph inputs.
- `pyproject.toml`: project metadata and Python dependencies.

## Requirements

- Python 3.10 or newer
- MATLAB
- MATLAB Engine for Python
- A local FAST repo

Install the Python dependencies:

```powershell
python -m pip install -e .
```

Install MATLAB Engine for Python from your local MATLAB installation if `import matlab.engine` does not work.

## FAST Path

Set `FAST_PATH` to the local FAST repo path:

```powershell
$env:FAST_PATH="C:\Users\your-name\Projects\FAST"
```

The path must contain:

```text
Main.m
+AircraftSpecsPkg/
+MissionProfilesPkg/
```

You can also pass the path directly in Python. This legacy/package-style mode runs aircraft and mission functions already available inside the FAST checkout:

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

## Run API

```powershell
uvicorn api:app --reload
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Run FAST:

```powershell
curl.exe -X POST http://127.0.0.1:8000/run `
  -H "Content-Type: application/json" `
  -d "{\"spec_name\":\"ERJ175LR\",\"mission_name\":\"ERJ_ClimbThenAccel\"}"
```

The API still supports package-style `spec_name` and `mission_name` calls. For richer Python-defined aircraft and mission inputs, use `main.py` directly so MATLAB expressions can be represented with `m("...")`.

## Optional API Key

Set `FAST_API_KEY` if you want the API to require an `x-api-key` header:

```powershell
$env:FAST_API_KEY="change-me"
```

Then call:

```powershell
curl.exe -X POST http://127.0.0.1:8000/run `
  -H "Content-Type: application/json" `
  -H "x-api-key: change-me" `
  -d "{\"spec_name\":\"ERJ175LR\",\"mission_name\":\"ERJ_ClimbThenAccel\"}"
```
