# FAST Python Wrapper

Python wrapper for running [Future Aircraft Sizing Tool (FAST)](https://github.com/ideas-um/FAST) through MATLAB Engine.


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

```python

    project_dir = Path(__file__).resolve().parent
    fast_dir = project_dir.parent / "FAST"

    input_aircraft = {
        "Specs": {
            "TLAR": {
                "EIS": 2005,
                "Class": "Turbofan",
                "MaxPax": 218.8828,
            },
            "Aero": {
                "L_D": {
                    "ClbCF": 1,
                    "CrsCF": 1,
                    "Clb": 13,
                    "Crs": 17,
                    "Des": 13,
                },
                "W_S": {
                    "SLS": 739.8499,
                },
            },
            "Propulsion": {
                "MDotCF": 1.2,
                "PropArch": {
                    "Type": "C",
                },
                "Engine": {
                    "Mach": 0.05,
                    "Alt": 0,
                    "OPR": 24.5,
                    "FPR": 1.6,
                    "BPR": 4,
                    "Tt4Max": 1711,
                    "TempLimit": {
                        "Val": nan,
                        "Type": nan,
                    },
                    "DesignThrust": 64543.6956,
                    "NoSpools": 2,
                    "RPMs": {
                        "_matlab_row": [
                            7400,
                            17820,
                        ],
                    },
                    "FanGearRatio": nan,
                    "FanBoosters": False,
                    "CoreFlow": {
                        "PaxBleed": 0.03,
                        "Leakage": 0.01,
                        "Cooling": 0,
                    },
                    "MaxIter": 300,
                    "EtaPoly": {
                        "Inlet": 0.99,
                        "Diffusers": 0.99,
                        "Fan": 0.99,
                        "Compressors": 0.94,
                        "BypassNozzle": 0.99,
                        "Combustor": 0.995,
                        "Turbines": 0.94,
                        "CoreNozzle": 0.99,
                        "Nozzles": 0.99,
                        "Mixing": 0,
                    },
                    "PerElec": 0,
                    "Cff3": 0.299,
                    "Cff2": -0.346,
                    "Cff1": 0.701,
                    "Cffch": 0,
                    "HEcoeff": 1,
                },
                "NumEngines": 2,
                "T_W": {
                    "SLS": 0.3,
                },
                "Eta": {
                    "Prop": 0.8,
                },
            },
            "Weight": {
                "WairfCF": 1,
                "MTOW": 86182.5503,
                "EM": 0,
                "Fuel": 9427.9174,
                "Batt": 0,
            },
            "Performance": {
                "Vels": {
                    "Tko": 69.45,
                    "Crs": 0.78,
                },
                "Alts": {
                    "Tko": 0,
                    "Crs": 10668,
                },
                "Range": 4630000,
                "RCMax": 11.43,
            },
            "Power": {
                "SpecEnergy": {
                    "Fuel": 12,
                    "Batt": 0.25,
                },
                "Eta": {
                    "EM": 0.96,
                    "EG": 0.96,
                },
                "P_W": {
                    "EM": 10,
                },
            },
        },
        "Settings": {
            "OEW": {
                "MaxIter": 50,
                "Tol": 0.001,
            },
            "Analysis": {
                "MaxIter": 50,
                "Type": 1,
            },
            "Plotting": 0,
            "Table": 0,
        },
        "Mission": {
            "Profile": {
                "Target": {
                    "Valu": [
                        1620500,
                        3009500,
                    ],
                    "Type": [
                        "Dist",
                        "Dist",
                    ],
                },
                "Segs": [
                    "Climb",
                    "Cruise",
                    "Climb",
                    "Cruise",
                    "Descent",
                ],
                "ID": [
                    1,
                    1,
                    2,
                    2,
                    2,
                ],
                "AltBeg": [
                    0,
                    10058.4,
                    10058.4,
                    10668,
                    10668,
                ],
                "AltEnd": [
                    10058.4,
                    10058.4,
                    10668,
                    10668,
                    0,
                ],
                "VelBeg": [
                    0.2,
                    0.78,
                    0.78,
                    0.78,
                    0.78,
                ],
                "VelEnd": [
                    0.78,
                    0.78,
                    0.78,
                    0.78,
                    0.2,
                ],
                "TypeBeg": [
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                ],
                "TypeEnd": [
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                    "Mach",
                ],
                "ClbRate": [
                    nan,
                    nan,
                    nan,
                    nan,
                    nan,
                ],
            },
        },
    }

    result = FAST_Python_Wrapper(input_aircraft, fast_dir)

    print("Run success:" + str(result["status"]))
    print(result["log"])
    print("MTOW:" + str(result["output"]["Specs"]["Weight"]["MTOW"]))
```