# FAST Python Wrapper Tests

These tests verify that the FAST Python Wrapper stays aligned with MATLAB FAST. They compare results from wrapper runs against MATLAB FAST outputs.

## Test Algorithms

1. Use FAST Python Wrapper to run merged aircraft and mission dictionaries loaded from `examples/*/inputs/InputAircraft.json`.
2. Load the output aircrafts saved in `examples/*/outputs/OutputAircraft.json`.
3. Recursively compare the FAST Python Wrapper outputs against the saved `OutputAircraft.json`.

These tests compare all comparable fields in `OutputAircraft.json`, including
nested structs, numeric arrays, logical values, strings, cells, and function
handle text. Two fields are intentionally excluded:

- `Aircraft.Mission.ProfileFxn`: a MATLAB specific component that is unrelated to whether  FAST Python Wrapper produced the same aircraft/mission result.
- `Aircraft.Settings.Dir.Size`: FAST stores the local run directory, which is machine and repo location specific.

## How To Run Tests

From the repo root:
```
pytest
```
