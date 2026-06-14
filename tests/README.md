# FAST Python Wrapper Tests

These tests verify that the FAST Python Wrapper stays aligned with MATLAB FAST. They compare results from wrapper runs against MATLAB FAST outputs.

## Test Algorithms

1. Load merged aircraft and mission dictionaries from `examples/*/InputAircraft.json`.
2. Run FAST Python Wrapper with those in-memory dictionaries.
3. Require `status` to be `Yes`, then recursively compare the returned `output` dictionary against the saved `OutputAircraft.json`.

These tests compare all comparable fields in `OutputAircraft.json`, including
nested structs, numeric arrays, logical values, strings, cells, and function
handle text. One field is intentionally excluded:

- `Aircraft.Settings.Plotting`: FAST can mutate plotting state independently of the aircraft and mission result.

## How To Run Tests

From the repo root:
```
pytest
```
