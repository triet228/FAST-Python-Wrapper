# tests/test_CeRAS.py

"""Compare the vendored CeRAS FAST-model fixture through the Python wrapper."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
)


CASE = {
    "name": "CeRAS",
    "aircraft": "CeRAS",
    "aircraft_expression": "setfield(feval('CeRAS'), 'Settings', 'Plotting', 0)",
    "mission": "CeRAS_mission",
    "saved": "CeRAS/outputs/OutputAircraft.mat",
}


def test_CeRAS_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check CeRAS wrapper MTOW and fuel against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        CASE,
        fast_path,
        fast_models_path,
        tmp_path,
    )
