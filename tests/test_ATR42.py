# tests/test_ATR42.py

"""Run the ATR42 JSON fixture and compare FAST output."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    examples_path,
    fast_path,
    load_example_input,
)


def test_ATR42_wrapper_output_matches_saved_json_file(
    fast_path,
    examples_path,
    tmp_path,
):
    """Check the full ATR42 aircraft output against saved OutputAircraft.json."""

    assert_fast_model_wrapper_matches_saved_output(
        name="ATR42",
        aircraft=load_example_input(
            examples_path,
            "ATR42",
            "InputAircraft.json",
        ),
        mission=load_example_input(
            examples_path,
            "ATR42",
            "Mission.json",
        ),
        saved="ATR42/outputs/OutputAircraft.json",
        fast_path=fast_path,
        examples_path=examples_path,
        tmp_path=tmp_path,
    )
