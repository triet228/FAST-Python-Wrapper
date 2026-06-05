# tests/test_A320.py

"""Compare the vendored A320 FAST-model fixture through the Python wrapper."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
)


CASE = {
    "name": "A320",
    "aircraft": "A320Neo",
    "mission": "A320",
    "saved": "A320/outputs/OutputAircraft.mat",
}


def test_A320_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check A320 wrapper MTOW and fuel against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        CASE,
        fast_path,
        fast_models_path,
        tmp_path,
    )
