# tests/test_CeRAS.py

"""Run the CeRAS JSON fixture and compare FAST output."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
    load_fast_model_json,
)


def test_CeRAS_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full CeRAS aircraft output against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        name="CeRAS",
        aircraft=load_fast_model_json(
            fast_models_path,
            "CeRAS",
            "Aircraft",
            "CeRAS.json",
        ),
        mission=load_fast_model_json(
            fast_models_path,
            "CeRAS",
            "Mission",
            "CeRAS_mission.json",
        ),
        saved="CeRAS/outputs/OutputAircraft.mat",
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
