# tests/test_CeRAS.py

"""Run the CeRAS JSON fixture and compare FAST output."""

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    examples_path,
    fast_path,
    load_example_input,
)


def test_CeRAS_wrapper_output_matches_saved_json_file(
    fast_path,
    examples_path,
    tmp_path,
):
    """Check the full CeRAS aircraft output against saved OutputAircraft.json."""

    assert_fast_model_wrapper_matches_saved_output(
        name="CeRAS",
        aircraft=load_example_input(examples_path, "CeRAS"),
        saved="CeRAS/outputs/OutputAircraft.json",
        fast_path=fast_path,
        examples_path=examples_path,
        tmp_path=tmp_path,
    )
