# tests/test_CeRAS.py

"""Run the CeRAS JSON fixture and compare FAST output."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
    load_fast_model_input,
)


def test_CeRAS_wrapper_output_matches_saved_json_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full CeRAS aircraft output against saved OutputAircraft.json."""

    assert_fast_model_wrapper_matches_saved_output(
        name="CeRAS",
        aircraft=load_fast_model_input(
            fast_models_path,
            "CeRAS",
            "InputAircraft.json",
        ),
        mission=load_fast_model_input(
            fast_models_path,
            "CeRAS",
            "Mission.json",
        ),
        saved="CeRAS/outputs/OutputAircraft.json",
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
