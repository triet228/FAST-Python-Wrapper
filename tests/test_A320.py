# tests/test_A320.py

"""Run the A320 JSON fixture and compare FAST output."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    examples_path,
    fast_path,
    load_example_input,
)


def test_A320_wrapper_output_matches_saved_json_file(
    fast_path,
    examples_path,
    tmp_path,
):
    """Check the full A320 aircraft output against saved OutputAircraft.json."""

    assert_fast_model_wrapper_matches_saved_output(
        name="A320",
        aircraft=load_example_input(examples_path, "A320"),
        saved="A320/outputs/OutputAircraft.json",
        fast_path=fast_path,
        examples_path=examples_path,
        tmp_path=tmp_path,
    )
