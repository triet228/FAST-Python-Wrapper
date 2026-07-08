# core/aircraft_contract.py

"""Keep Python aircraft dictionaries aligned with the public FAST contract."""

from copy import deepcopy


ENGINE_SPEC_NAMES = (
    "AE2100_D3",
    "AE3007A",
    "AE501D_22G",
    "Allison_250_C30G",
    "CeRAS",
    "CF34_8E5",
    "CF6_80C2_B7F",
    "ExampleTF",
    "ExampleTP",
    "LEAP_1A26",
    "PT6A_114A",
    "PW_123",
    "PW_127M",
    "PW_1919G",
    "PW_2037",
    "RB211_22B_02",
    "TPE331_14GR_805H",
    "Trent_970B_84",
)
AERO_METHOD_NAMES = (
    "ConstantLD",
    "DragPolar",
)
AERO_METHOD_EXPRESSIONS = {
    "ConstantLD": "@(Aircraft) AerodynamicsPkg.ConstantLD(Aircraft)",
    "DragPolar": "@(Aircraft) AerodynamicsPkg.DragPolar(Aircraft)",
}
GEOMETRY_PRESET_NAMES = (
    "LM100JNominalGeometry",
)
GEOMETRY_PRESET_EXPRESSIONS = {
    "LM100JNominalGeometry": "@(Aircraft) VisualizationPkg.GeometrySpecsPkg.LM100JNominalGeometry(Aircraft)",
}
PROP_ARCH_PRESET_TYPES = ("C", "E", "PHE", "SHE", "TE", "PE")
PROP_ARCH_CUSTOM_TYPE = "O"
PROP_ARCH_TYPES = PROP_ARCH_PRESET_TYPES + (PROP_ARCH_CUSTOM_TYPE,)
CUSTOM_PROP_ARCH_FIELDS = (
    "Arch",
    "OperUps",
    "OperDwn",
    "EtaUps",
    "EtaDwn",
    "SrcType",
    "TrnType",
)
OUTPUT_FIELDS_TO_REMOVE = (
    ("Specs", "Aero", "L_D", "Method"),
    ("Geometry", "Preset"),
    ("Mission", "ProfileFxn"),
    ("Settings", "Dir", "Size"),
)


def prepare_aircraft(aircraft):
    """Normalize InputAircraft without mutating the caller's dictionary.

    Inputs:
        aircraft: Python InputAircraft dictionary.

    Outputs:
        Deep-copied aircraft dictionary ready for MATLAB literal conversion.

    Assumptions:
        The wrapper supports FAST preset architecture labels, plus custom O
        architectures when every architecture field is fixed numeric data.
        Legacy PropArch companion fields are removed so stale graph architecture
        data cannot leak into a preset run.
    """

    if not isinstance(aircraft, dict):
        return aircraft

    aircraft = deepcopy(aircraft)
    propulsion = _get_propulsion_section(aircraft)

    if propulsion is None:
        return aircraft

    arch_type = _get_prop_arch_type(propulsion)

    if not isinstance(arch_type, str):
        return aircraft

    arch_type = arch_type.upper()
    _require_supported_prop_arch_type(arch_type)

    if arch_type == PROP_ARCH_CUSTOM_TYPE:
        _prepare_custom_prop_arch(propulsion)
    else:
        propulsion["PropArch"] = {"Type": arch_type}

    _prepare_aero_method(aircraft)
    _prepare_geometry_preset(aircraft)
    _prepare_engine_spec(propulsion)
    _remove_legacy_prop_arch_fields(propulsion)

    return aircraft


def extract_mission_profile(aircraft):
    """Remove and return the mission profile embedded in InputAircraft.

    Inputs:
        aircraft: Prepared aircraft dictionary that still contains Mission.

    Outputs:
        Mission.Profile dictionary passed into FAST's mission_profile handle.

    Side effects:
        Mutates the prepared copy by removing Mission before aircraft_spec is
        converted to MATLAB. FAST receives mission data through the function
        handle, not as a standalone top-level aircraft field.
    """

    try:
        mission_container = aircraft.pop("Mission")
        mission = mission_container["Profile"]
    except (KeyError, TypeError) as error:
        raise ValueError("InputAircraft must include Mission.Profile for FAST runs.") from error

    if not isinstance(mission, dict):
        raise ValueError("InputAircraft Mission.Profile must be an object.")

    return mission


def clean_output_fields(output):
    """Remove FAST runtime fields from reusable OutputAircraft data.

    Inputs:
        output: Python dictionary converted from MATLAB OutputAircraft.

    Side effects:
        Mutates output in place. The result is the public OutputAircraft dict
        returned by FAST_Python_Wrapper() and used by the JSON fixtures.
    """

    for path in OUTPUT_FIELDS_TO_REMOVE:
        current = _nested_dict(output, path[:-1])

        if isinstance(current, dict):
            current.pop(path[-1], None)

    settings = output.get("Settings")

    if isinstance(settings, dict):
        for key in list(settings):
            key_text = key.lower()

            if key_text.startswith("narg") and "oper" in key_text:
                del settings[key]

    _clean_prop_arch_fields(output)


def _get_propulsion_section(aircraft):
    """Return Specs.Propulsion when the input has that nested object."""

    try:
        propulsion = aircraft["Specs"]["Propulsion"]
    except KeyError:
        return None

    if isinstance(propulsion, dict):
        return propulsion

    return None


def _get_prop_arch_type(propulsion):
    """Return the propulsion architecture label from current or legacy shape."""

    prop_arch = propulsion.get("PropArch")

    if isinstance(prop_arch, dict):
        return prop_arch.get("Type")

    return prop_arch


def _require_supported_prop_arch_type(arch_type):
    """Fail early when the wrapper does not support a PropArch label."""

    if arch_type in PROP_ARCH_TYPES:
        return

    joined_types = ", ".join(PROP_ARCH_TYPES)
    raise ValueError(f"PropArch.Type must be one of: {joined_types}.")


def _prepare_custom_prop_arch(propulsion):
    """Normalize and validate fixed numeric custom architecture data."""

    prop_arch = propulsion.get("PropArch")

    if not isinstance(prop_arch, dict):
        raise ValueError("PropArch.Type O requires PropArch to be an object.")

    prop_arch["Type"] = PROP_ARCH_CUSTOM_TYPE

    for field_name in CUSTOM_PROP_ARCH_FIELDS:
        if field_name not in prop_arch:
            raise ValueError(f"PropArch.Type O requires PropArch.{field_name}.")

        _require_fixed_numeric_value(
            prop_arch[field_name],
            f"PropArch.{field_name}",
        )


def _prepare_engine_spec(propulsion):
    """Convert an allowlisted EngineSpecsPkg name into a MATLAB package call."""

    engine = propulsion.get("Engine")

    if engine is None or isinstance(engine, dict):
        return

    if not isinstance(engine, str):
        raise ValueError("Specs.Propulsion.Engine must be an EngineSpecsPkg name.")

    if engine not in ENGINE_SPEC_NAMES:
        joined_names = ", ".join(ENGINE_SPEC_NAMES)
        raise ValueError(f"Specs.Propulsion.Engine must be one of: {joined_names}.")

    propulsion["Engine"] = {
        "_matlab_expression": f"EngineModelPkg.EngineSpecsPkg.{engine}",
    }


def _prepare_aero_method(aircraft):
    """Convert explicit public Aero.L_D.Method names into FAST function handles."""

    try:
        l_d = aircraft["Specs"]["Aero"]["L_D"]
    except KeyError:
        return

    if not isinstance(l_d, dict):
        return

    method = l_d.get("Method")

    if isinstance(method, dict):
        return

    if method is None:
        method = "ConstantLD"

    if not isinstance(method, str):
        raise ValueError("Specs.Aero.L_D.Method must be an aerodynamic method name.")

    if method not in AERO_METHOD_EXPRESSIONS:
        joined_names = ", ".join(AERO_METHOD_NAMES)
        raise ValueError(f"Specs.Aero.L_D.Method must be one of: {joined_names}.")

    l_d["Method"] = {
        "_matlab_expression": AERO_METHOD_EXPRESSIONS[method],
    }


def _prepare_geometry_preset(aircraft):
    """Convert public Geometry.Preset names into FAST visualization handles."""

    geometry = aircraft.get("Geometry")

    if not isinstance(geometry, dict):
        return

    preset = geometry.get("Preset")

    if preset is None or isinstance(preset, dict):
        return

    if not isinstance(preset, str):
        raise ValueError("Geometry.Preset must be a geometry preset name.")

    if preset not in GEOMETRY_PRESET_EXPRESSIONS:
        joined_names = ", ".join(GEOMETRY_PRESET_NAMES)
        raise ValueError(f"Geometry.Preset must be one of: {joined_names}.")

    geometry["Preset"] = {
        "_matlab_expression": GEOMETRY_PRESET_EXPRESSIONS[preset],
    }


def _require_fixed_numeric_value(value, label):
    """Reject variables, marker objects, strings, and booleans in O data."""

    if isinstance(value, bool):
        raise ValueError(f"{label} must contain only fixed numeric values.")

    if isinstance(value, int) or isinstance(value, float):
        return

    if isinstance(value, list) or isinstance(value, tuple):
        for index, item in enumerate(value):
            _require_fixed_numeric_value(item, f"{label}[{index}]")

        return

    raise ValueError(f"{label} must contain only fixed numeric values.")


def _remove_legacy_prop_arch_fields(propulsion):
    """Drop old PropArch companion fields that FAST no longer needs here."""

    for field_name in list(propulsion):
        if field_name.startswith("PropArch") and field_name != "PropArch":
            del propulsion[field_name]


def _nested_dict(value, path):
    """Return a nested dictionary or None when any step is missing."""

    current = value

    for key in path:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    if isinstance(current, dict):
        return current

    return None


def _clean_prop_arch_fields(value):
    """Keep every PropArch object limited to Type for supported architectures.

    Assumptions:
        FAST may expand propulsion architectures into internal graph-like data.
        The wrapper exposes only the public architecture label, so expanded
        fields are intentionally removed from output.
    """

    if isinstance(value, dict):
        for key, item in list(value.items()):
            if key == "PropArch" and isinstance(item, dict):
                value[key] = _public_prop_arch(item)
                continue

            _clean_prop_arch_fields(item)

        return

    if isinstance(value, list):
        for item in value:
            _clean_prop_arch_fields(item)


def _public_prop_arch(prop_arch):
    """Return the public PropArch object from expanded FAST internals."""

    arch_type = prop_arch.get("Type")

    if isinstance(arch_type, str):
        arch_type = arch_type.upper()

    if arch_type in PROP_ARCH_TYPES:
        return {
            "Type": arch_type,
        }

    return {}
