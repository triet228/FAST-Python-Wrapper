# core/aircraft_contract.py

"""Keep Python aircraft dictionaries aligned with the public FAST contract."""

from copy import deepcopy


PROP_ARCH_TYPES = ("C", "E")
OUTPUT_FIELDS_TO_REMOVE = (
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
        For now the wrapper only supports propulsion architecture types C and
        E. Any legacy PropArch companion fields are removed so stale graph
        architecture data cannot leak into a conventional run.
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

    propulsion["PropArch"] = {"Type": arch_type}
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
        The wrapper currently supports only the public architecture labels C
        and E, so expanded fields are intentionally removed from output.
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
