# core/schema_contract.py

"""Compatibility exports for schema building and validation helpers.

Older code imports schema helpers from this module. The implementation now
lives in schema_builder.py and schema_validation.py so each file has one clear
job, but this module keeps the public import path stable.
"""

from .aircraft_contract import PROP_ARCH_TYPES
from .json_io import (
    INPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    JsonValidationError,
    OUTPUT_AIRCRAFT_SCHEMA_JSON_PATH,
    SCHEMA_DIR,
    get_json_path,
    is_json_number,
    read_raw_json_file,
    require_json_object,
)
from .schema_builder import (
    apply_prop_arch_schema_contract,
    build_json_schema_from_value,
    json_schema_matlab_expression,
    json_schema_number,
    json_schema_prop_arch,
    merge_json_array_schemas,
    merge_json_object_schemas,
    merge_json_schemas,
    merge_json_schemas_without_specialization,
)
from .schema_validation import (
    is_json_schema_document,
    read_schema_file,
    require_json_list,
    require_json_number,
    require_json_string,
    resolve_json_schema_ref,
    validate_aircraft_json,
    validate_json_markers,
    validate_json_schema_document,
    validate_json_schema_number_limits,
    validate_json_schema_type,
    validate_json_schema_value,
    validate_mission_profile_json,
    validate_output_aircraft_json,
)
