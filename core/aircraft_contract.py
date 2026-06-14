# core/aircraft_contract.py

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

    try:
        propulsion = aircraft["Specs"]["Propulsion"]
    except KeyError:
        return aircraft

    prop_arch = propulsion.get("PropArch")

    if isinstance(prop_arch, dict):
        arch_type = prop_arch.get("Type")
    else:
        arch_type = prop_arch

    if not isinstance(arch_type, str):
        return aircraft

    arch_type = arch_type.upper()

    if arch_type not in PROP_ARCH_TYPES:
        joined_types = ", ".join(PROP_ARCH_TYPES)
        raise ValueError(f"PropArch.Type must be one of: {joined_types}.")

    propulsion["PropArch"] = {"Type": arch_type}

    for field_name in list(propulsion):
        if field_name.startswith("PropArch") and field_name != "PropArch":
            del propulsion[field_name]

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
        current = output

        for key in path[:-1]:
            if not isinstance(current, dict):
                current = None
                break

            current = current.get(key)

        if isinstance(current, dict):
            current.pop(path[-1], None)

    settings = output.get("Settings")

    if isinstance(settings, dict):
        for key in list(settings):
            key_text = key.lower()

            if key_text.startswith("narg") and "oper" in key_text:
                del settings[key]

    _clean_prop_arch_fields(output)


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
                arch_type = item.get("Type")

                if isinstance(arch_type, str):
                    arch_type = arch_type.upper()

                if arch_type in PROP_ARCH_TYPES:
                    value[key] = {
                        "Type": arch_type,
                    }
                else:
                    value[key] = {}

                continue

            _clean_prop_arch_fields(item)

        return

    if isinstance(value, list):
        for item in value:
            _clean_prop_arch_fields(item)
