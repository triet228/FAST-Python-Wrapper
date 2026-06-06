# tests/test_A320.py

"""Run the A320 JSON fixture and compare FAST output."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
    load_fast_model_json,
)


def test_A320_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full A320 aircraft output against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        name="A320",
        aircraft=load_fast_model_json(
            fast_models_path,
            "A320",
            "Aircraft",
            "A320Neo.json",
        ),
        mission=load_fast_model_json(
            fast_models_path,
            "A320",
            "Mission",
            "A320.json",
        ),
        saved="A320/outputs/OutputAircraft.mat",
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
