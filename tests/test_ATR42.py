# tests/test_ATR42.py

"""Compare the vendored ATR42 FAST-model fixture through the Python wrapper."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
)


CASE = {
    "name": "ATR42",
    "aircraft": "ATR42",
    "mission": "ATR42_600",
    "saved": "ATR42/outputs/OutputAircraft.mat",
}


def test_ATR42_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check ATR42 wrapper MTOW and fuel against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        CASE,
        fast_path,
        fast_models_path,
        tmp_path,
    )
