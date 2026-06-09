# FAST Python Wrapper

Python wrapper for running [Future Aircraft Sizing Tool (FAST)](https://github.com/ideas-um/FAST) through MATLAB Engine.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `main.py`: direct local script that reads `inputs/InputAircraft.json` and `inputs/Mission.json`, runs FAST, and writes output files under `outputs/`.
- `inputs/InputAircraft.json`: aircraft input data.
- `inputs/Mission.json`: mission input data.
- `outputs/`: generated FAST output JSON files.
- `contracts/InputAircraftStructure.json`: committed structure contract for aircraft input JSON.
- `contracts/MissionStructure.json`: committed structure contract for mission input JSON.
- `contracts/OutputAircraftStructure.json`: reference structure for generated FAST output.
- `pyproject.toml`: project metadata and Python dependencies.


## Requirements

- A local FAST directory
- Use a virtual environment with a Python version that is compatible with MATLAB Engine on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html). Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version.

> [!WARNING]
> Please make sure your Python version is compatible with MATLAB Engine and it's reflected in both your virtual environment and [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml).


## Installations

1. Clone this [GitHub repository](https://github.com/triet228/FAST-Python-Wrapper) to your machine.

2. Confirm Python version is compatible with MATLAB Engine. Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version.
> [!WARNING]
> Please confirm your Python version is compatible with MATLAB Engine on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html)

3. Install dependencies:
> [!TIP]
> Command line can be run in VS Code Terminal
```
pip install -e .
```

4. Check that Python can import MATLAB Engine:
```powershell
python -c "import matlab.engine; print('MATLAB Engine OK')"
```
If this gives error, you will need to debug this before continue. If this prints `MATLAB Engine OK`, the environment is ready.
> [!WARNING]
> One bug might be that your Python version is not compatible with MATLAB Engine. Please check on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html). Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version. Then redo step 4 `pip install -e .` to install dependencies.

> [!TIP]
> Inside MATLAB, you can run `which matlab` to know where MATLAB is installed.

5. Keep the local FAST checkout path handy as `FAST_DIR`. You pass it directly when running
   `main.py` or calling `main.main(...)`.


## How to Run

Edit `inputs/InputAircraft.json` and `inputs/Mission.json`, then run:
```powershell
python main.py "C:\path\to\FAST"
```

The script validates both input files against the committed structure contracts,
runs FAST through MATLAB Engine, and writes `outputs/OutputAircraft.json`.

Python callers pass `INPUT_DIR`, `OUTPUT_DIR`, and `FAST_DIR` explicitly:
```python
import main

main.main("path/to/inputs", "path/to/outputs", "path/to/FAST")
```

FAST input values in `inputs/InputAircraft.json` and `inputs/Mission.json` are
written in SI units where applicable, such as kg, m, m/s, N, and kg/m^2. JSON
does not support comments, so keep unit notes in documentation instead of adding
comment fields to the input structures passed into FAST.


