# FAST Python Wrapper

Python wrapper for running [Future Aircraft Sizing Tool (FAST)](https://github.com/ideas-um/FAST) through MATLAB Engine.

## Files

- `main.py`: public `FAST_Python_Wrapper()` API around MATLAB Engine and FAST.
- `core/fast_runner.py`: FAST run orchestration.
- `core/aircraft_contract.py`: aircraft input normalization and OutputAircraft cleanup.
- `core/matlab_bridge.py`: MATLAB Engine startup and MATLAB/Python data conversion.
- `core/helper.py`: compatibility imports and example input loader.
- `core/json_io.py`: JSON serialization, parsing, marker conversion, and log printing helpers.
- `core/schema_contract.py`: JSON Schema inference and validation helpers.
- `core/output_structure.py`: OutputAircraft structure generation and console preview helpers.
- `examples/<Aircraft>/InputAircraft.json`: optional merged aircraft and mission example input data.
- `examples/<Aircraft>/OutputAircraft.json`: optional saved aircraft output fixture.
- `schema/InputAircraftSchema.json`: JSON Schema for merged input aircraft JSON.
- `schema/OutputAircraftSchema.json`: JSON Schema for output aircraft JSON.


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


## Python Dict API

Use the wrapper with an in-memory `InputAircraft` dictionary. `FAST_Python_Wrapper()` does not write JSON files; it returns a Python dictionary with `status`, `log`, and `output`.

```python
from main import FAST_Python_Wrapper

input_aircraft = {
    "Specs": {
        # aircraft fields
    },
    "Mission": {
        "Profile": {
            # mission fields
        },
    },
}

result = FAST_Python_Wrapper(input_aircraft, FAST_DIR)

if result["status"] == "Yes":
    output_aircraft = result["output"]
else:
    print(result["log"])
```

## Example JSON Loader

The JSON files in `examples/` are fixtures and templates, not required runtime I/O. To run one of them manually:

```python
from core.helper import load_input_aircraft_json
from main import FAST_Python_Wrapper

input_aircraft = load_input_aircraft_json("examples/CeRAS")
result = FAST_Python_Wrapper(input_aircraft, FAST_DIR)
```


