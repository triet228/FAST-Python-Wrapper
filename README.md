# FAST Python Wrapper

Unofficial Python wrapper for running FAST through MATLAB Engine.

Use this repo as a lightweight integration layer around a local FAST installation.

This project does not include FAST or MATLAB Engine. Each user needs a local FAST checkout and a working MATLAB Engine for Python installation.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `api.py`: optional FastAPI server.
- `main.py`: direct local script that runs the default FAST case.
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

You can also pass the path directly in Python:

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

By default, this runs:

```text
AircraftSpecsPkg.ERJ175LR
MissionProfilesPkg.ERJ_ClimbThenAccel
```

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
