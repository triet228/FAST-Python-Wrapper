# FAST Python Wrapper

Unofficial Python wrapper for running FAST through MATLAB Engine.

Use this repo as a lightweight integration layer around a local FAST installation.

This project does not include FAST or MATLAB Engine. Each user needs a local FAST checkout and a working MATLAB Engine for Python installation.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `main.py`: direct local script with editable Python `AIRCRAFT`, `MISSION`, and propulsion graph inputs.
- `.env.example`: example local path configuration.
- `pyproject.toml`: project metadata and Python dependencies.

## Requirements

- Python 3.10 or newer supported by your MATLAB release
- MATLAB
- MATLAB Engine for Python
- A local FAST repo

This repo has been smoke-tested on Windows with:

- Conda environment `fast`
- Python 3.11
- MATLAB R2025b
- FAST checkout at `C:\Users\homin\Projects\FAST`

## Setup

Open PowerShell or Anaconda Prompt.

Create a conda environment with Python 3.11:

```powershell
conda create -n fast python=3.11
conda activate fast
```

Go to the folder where you cloned this repo and install the wrapper:

```powershell
cd C:\path\to\FAST-Python-Wrapper
python -m pip install -e .
```

Create your local path settings:

```powershell
Copy-Item .env.example .env
notepad .env
```

If `.env` does not exist yet, `python main.py` will also create it from
`.env.example` and ask you to edit it.

Set `FAST_PATH` to your local FAST checkout. For example:

```text
FAST_PATH=C:\Users\your-name\Projects\FAST
MATLAB_ROOT=C:\Program Files\MATLAB\R2025b
```

`FAST_PATH` is used by `main.py`. `MATLAB_ROOT` is only a note for setup, so
you know where MATLAB Engine is installed.

Now install MATLAB Engine for Python. This is the package that lets Python
start MATLAB.

If you do not know where MATLAB is installed, open MATLAB and run:

```matlab
which matlab
```

Example output:

```text
C:\Program Files\MATLAB\R2025b\toolbox\matlab\general\matlab.m
```

In that example, the MATLAB install folder is:

```text
C:\Program Files\MATLAB\R2025b
```

Use that folder as `MATLAB_ROOT` in `.env`.

First copy MATLAB's Python engine installer to a normal writable folder:

In this command, replace `C:\Program Files\MATLAB\R2025b` with your
`MATLAB_ROOT` if your MATLAB install folder is different.

```powershell
New-Item -ItemType Directory "$env:TEMP\matlab-engine-R2025b-python" -Force
Copy-Item "C:\Program Files\MATLAB\R2025b\extern\engines\python\*" "$env:TEMP\matlab-engine-R2025b-python" -Recurse -Force
```

Then install MATLAB Engine from that copied folder:

```powershell
python -m pip install "$env:TEMP\matlab-engine-R2025b-python"
```

Check that Python can import MATLAB Engine:

```powershell
python -c "import matlab.engine; print('MATLAB Engine OK')"
```

If that prints `MATLAB Engine OK`, the environment is ready.

Do not run `python -m pip install .` from inside
`C:\Program Files\MATLAB\R2025b\extern\engines\python`. Windows often blocks
pip from writing build files inside `C:\Program Files`, which causes an
`Access is denied` error.

## FAST Path

Set `FAST_PATH` in `.env` to the local FAST repo path. The path must contain:

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
