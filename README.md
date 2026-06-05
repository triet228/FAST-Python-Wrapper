# FAST Python Wrapper

Python wrapper for running [Future Aircraft Sizing Tool (FAST)](https://github.com/ideas-um/FAST) through MATLAB Engine.

> [!WARNING]
> Please confirm your Python version is compatible with MATLAB Engine on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html). Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version.

## Files

- `wrapper.py`: core wrapper around MATLAB Engine and FAST.
- `main.py`: direct local script with editable Python `AIRCRAFT`, `MISSION`, and optional `GRAPH_BASED_PROPULSION` if custom propulsion architecture is needed.
- `.env.example`: example local path configuration, copy this to `.env` and edit the paths inside.
- `pyproject.toml`: project metadata and Python dependencies.


## Requirements

- A local FAST directory
- Use a virtual environment manager to download a virtual environment with the right Python version that is compatible with MATLAB Engine on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html). Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version.


## Installations

1. Clone this [GitHub repository](https://github.com/triet228/FAST-Python-Wrapper) to your machine.
2. Confirm Python version is compatible with MATLAB Engine. Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version.
> [!WARNING]
> Please confirm your Python version is compatible with MATLAB Engine on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html)
4. Install dependencies:
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
> [!TIP]
> Inside MATLAB, you can run `which matlab` to know where MATLAB is installed.
6. Copy [`.env.example`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/.env.example) to `.env` and set `FAST_PATH` to your local FAST directory.


## How to Run

Edit  `AIRCRAFT`, `MISSION`, and optional `GRAPH_BASED_PROPULSION` in [`main.py`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/main.py) and run:
```
python main.py
```

> [!WARNING]
> Please confirm your Python version is compatible with MATLAB Engine on [MATLAB Official Website](https://www.mathworks.com/support/requirements/python-compatibility.html). Edit [`pyproject.toml`](https://github.com/triet228/FAST-Python-Wrapper/blob/main/pyproject.toml) to match the correct python and matlabengine version.
