# tests/test_expanded_examples.py

"""Run expanded FAST JSON fixtures and compare saved outputs."""

import pytest

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    load_example_input,
)


EXPANDED_CASE_NAMES = [
    "ERJ175LR",
    "ERJ175LR_ClimbThenAccel",
    "ERJ175LR_Elec",
    "ERJ190_E2",
    "ERJ190_FE",
    "LM100J_Conventional",
]


@pytest.mark.parametrize("case_name", EXPANDED_CASE_NAMES)
def test_expanded_example_wrapper_output_matches_saved_json_file(
    case_name,
    fast_path,
    examples_path,
):
    """Check each expanded aircraft output against saved OutputAircraft.json."""

    assert_fast_model_wrapper_matches_saved_output(
        name=case_name,
        aircraft=load_example_input(examples_path, case_name),
        saved=f"{case_name}/OutputAircraft.json",
        fast_path=fast_path,
        examples_path=examples_path,
    )
