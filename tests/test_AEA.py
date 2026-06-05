# tests/test_AEA.py

"""Compare the vendored AEA FAST-model fixture through the Python wrapper."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
)


CASE = {
    "name": "AEA",
    "aircraft": "AEA",
    "mission": "AEAProfile",
    "saved": "AEA/outputs/OutputAircraft.mat",
}


def test_AEA_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check AEA wrapper MTOW and fuel against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        CASE,
        fast_path,
        fast_models_path,
        tmp_path,
    )
