# FAST Python Wrapper

Python wrapper for running [Future Aircraft Sizing Tool (FAST)](https://github.com/ideas-um/FAST) through MATLAB Engine.


## Running FAST-Python-Wrapper

The wrapper accepts an `input_aircraft` dictionary and the local path to FAST.

```python


from math import nan
from pathlib import Path

from numpy import nan

from main import FAST_Python_Wrapper

from core.matlab_bridge import matlab_expr

project_dir = Path(__file__).resolve().parent
fast_dir = project_dir.parent / "FAST"

input_aircraft = {
    "Specs": {
        "TLAR": {
            "Class": "Turbofan", # Turbofan, Turboprop
            "MaxPax": 180,
        },
        "Performance": {
            "Range": 4630000,
        },
        "Propulsion": {
            "PropArch": {
                "Type": "C", # C for Conventional, E for Electric
            },
            # Turboprop: nan, AE2100_D3, AE501D_22G, Allison_250_C30G, PT6A_114A, PW_123, PW_127M, TPE331_14GR_805H
            # Turbofan: LEAP_1A26, CF34_8E5
            "Engine": matlab_expr("EngineModelPkg.EngineSpecsPkg.CF34_8E5")
        },
        "Power": {
            "P_W": {},
        },
    },
    "Mission": {
        "Profile": {
            "Target": {
                "Valu": [4630000],
                "Type": ["Dist"],
            },
            "Segs": ["Cruise"],
            "ID": [1],
            "AltBeg": [10668],
            "AltEnd": [10668],
            "ClbRate": [nan],
            "VelBeg": [0.78],
            "VelEnd": [0.78],
            "TypeBeg": ["Mach"],
            "TypeEnd": ["Mach"],
        },
    },
}

result = FAST_Python_Wrapper(input_aircraft, fast_dir)

print("Run success:", result["status"])
print(result["log"])

if result["status"] == "Yes":
    MTOW = result["output"]["Specs"]["Weight"]["MTOW"]
    print("MTOW:" + str(MTOW) + " kg")


```


## Limitation

Currently only support propulsion architecture for Conventional C and Fully Electrici E


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
