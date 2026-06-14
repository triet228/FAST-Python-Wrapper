# FAST Python Wrapper

Python wrapper for running [Future Aircraft Sizing Tool (FAST)](https://github.com/ideas-um/FAST) through MATLAB Engine.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `main.py`: direct script that runs FAST-Python_Wrapper from a Python dictionary.
- `examples/<Aircraft>/inputs/InputAircraft.json`: optional merged aircraft and mission example input data.
- `examples/<Aircraft>/outputs/`: optional saved aircraft output fixtures.
- `contracts/InputAircraftSchema.json`: JSON Schema for merged input aircraft JSON.
- `contracts/OutputAircraftSchema.json`: JSON Schema for output aircraft JSON.


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

Use the wrapper with an in-memory `InputAircraft` dictionary. `FastWrapper.run()` does not write JSON files; it returns a Python dictionary with `status`, `log`, and `output`.

```python
from wrapper import FastWrapper

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

with FastWrapper(FAST_DIR) as fast:
    result = fast.run(input_aircraft)

if result["status"] == "Yes":
    output_aircraft = result["output"]
else:
    print(result["log"])
```

For a one-shot call:

```python
from wrapper import run_fast

result = run_fast(input_aircraft, FAST_DIR)
```

## Example JSON Loader

The JSON files in `examples/` are fixtures and templates, not required runtime I/O. To run one of them manually:

```python
from helper import load_input_aircraft_json
from main import main

input_aircraft = load_input_aircraft_json("examples/CeRAS/inputs")
result = main(input_aircraft, FAST_DIR)
```

Or edit the input and FAST paths at the bottom of `main.py`, then run:

```bash
python main.py
```


