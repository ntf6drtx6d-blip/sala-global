# devices.py

SOLAR_ENGINES = {
    "se_micro": {
        "key": "se_micro",
        "name": "Solar Engine Micro",
        "short_name": "SE MICRO",
        "pv": 25,
        "batt": 216,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "batt_ext": None,
        "tilt_options": [33],
        "fixed": True,
        "standby_power_w": None,
    },
    "se_mini": {
        "key": "se_mini",
        "name": "Solar Engine Mini",
        "short_name": "SE MINI",
        "pv": 40,
        "batt": 336,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "batt_ext": None,
        "tilt_options": [33],
        "fixed": True,
        "standby_power_w": None,
    },
    "se_compact": {
        "key": "se_compact",
        "name": "Solar Engine Compact",
        "short_name": "SE COMPACT",
        "pv": 185,
        "batt": 1440,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "batt_ext": 2880,
        "tilt_options": [15, 35, 55],
        "fixed": False,
        "standby_power_w": None,
    },
    # Half of SE MAX in both dimensions. Read against SE COMPACT it is the
    # recharge-focused sibling: near-identical storage (1320 vs 1440 Wh)
    # with roughly double the panel, which is what a load limited by daily
    # recharge rather than by storage actually needs.
    #
    # Its battery/panel ratio (3.7) sits close to SE MAX (4.2) rather than
    # the panel-starved MICRO/MINI/COMPACT (7.8-8.6), so it is a balanced
    # design: in a temperate worst month the panel and the battery run out
    # at about the same point, with neither substantially wasted.
    #
    # Deliberately NOT the default engine for any device; it has to be
    # chosen explicitly.
    "se_optima": {
        "key": "se_optima",
        "name": "Solar Engine Optima",
        "short_name": "SE OPTIMA",
        "pv": 360,
        "batt": 1320,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "batt_ext": 2640,
        "tilt_options": [15, 35, 55],
        "fixed": False,
        "standby_power_w": None,
    },
    "se_max": {
        "key": "se_max",
        "name": "Solar Engine Max",
        "short_name": "SE MAX",
        "pv": 720,
        "batt": 3000,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "batt_ext": 6000,
        "tilt_options": [15, 35, 55],
        "fixed": False,
        "standby_power_w": None,
    },
}

DEVICES = {
    1: {
        "code": "SP-401SMI",
        "name": "PRO SP-401SMI",
        "manufacturer": "S4GA",
        "system_type": "builtin",
        "default_power": 3.3,
        "pv": 25,
        "batt": 216,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "tilt": 33,
        "fixed": True,
        "supports_intensity_adjustment": True,
        "standby_power_w": None,
        "default_lamp_variant": "Runway edge light",
        "lamp_variants": {
            "Runway edge light": {"power_w": 3.3},
            "Runway threshold/end light": {"power_w": 1.8},
            "Taxiway edge light": {"power_w": 0.6},
            "Approach light": {"power_w": 3.9},
            "Obstruction Type A LI light": {"power_w": 0.6},
            "TLOF light": {"power_w": 2.58},
            "FATO light": {"power_w": 4.5},
        },
    },
    2: {
        "code": "SP-501SHI",
        "name": "CAT-I SP-501SHI",
        "manufacturer": "S4GA",
        "system_type": "builtin",
        "default_power": 27.0,
        "pv": 25,
        "batt": 216,
        "battery_type": "Lead Acid",
        "cutoff_pct": 30,
        "tilt": 33,
        "fixed": True,
        "supports_intensity_adjustment": True,
        "standby_power_w": None,
        "default_lamp_variant": "Runway edge light",
        "lamp_variants": {
            "Runway edge light": {"power_w": 27.0},
            "Runway threshold/end light": {"power_w": 25.0},
            "Approach light": {"power_w": 30.0},
        },
    },
    3: {
        "code": "SP-301SL",
        "name": "STD SP-301SL",
        "manufacturer": "S4GA",
        "system_type": "builtin",
        "default_power": 2.7,
        "pv": 5,
        "batt": 54,
        "battery_type": "LiFePO4",
        "cutoff_pct": 20,
        "tilt": 33,
        "fixed": True,
        "supports_intensity_adjustment": True,
        "standby_power_w": None,
        # Figures are the A/LED SP-301 wattage column (volts x drive
        # current); the regulator suffix is carried in the name only where
        # the same optic exists under more than one standard, so Taxiway,
        # Obstruction, TLOF and FATO stay unsuffixed.
        "default_lamp_variant": "Runway edge light (ICAO)",
        "lamp_variants": {
            "Runway edge light (ICAO)": {"power_w": 2.7},
            "Runway edge light (MOS)": {"power_w": 3.84},
            "Runway edge light, yellow (FAA)": {"power_w": 0.15},
            "Taxiway edge light": {"power_w": 0.2},
            "Runway threshold/end light (ICAO)": {"power_w": 0.73},
            "Runway threshold/end light (MOS)": {"power_w": 0.99},
            "Runway threshold light (ICAO, MOS)": {"power_w": 0.71},
            "Runway end light (ICAO, MOS)": {"power_w": 0.26},
            "Obstruction Type A LI light": {"power_w": 0.6},
            "TLOF light": {"power_w": 1.32},
            "Holding point light (MOS)": {"power_w": 0.15},
            "FATO light": {"power_w": 4.61},
        },
    },
    4: {
        "code": "SP-200",
        "name": "SP-200 Inset Light",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 5.0,
        "default_engine": "se_micro",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": False,
        "standby_power_w": None,
    },
    5: {
        "code": "PAPI",
        "name": "PAPI",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 320.0,
        "default_engine": "se_max",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": True,
        "standby_power_w": None,
    },
    6: {
        "code": "A-PAPI",
        "name": "A-PAPI",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 160.0,
        "default_engine": "se_max",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": True,
        "standby_power_w": None,
    },
    7: {
        "code": "RGL",
        "name": "Runway Guard Light",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 3.0,
        "default_engine": "se_mini",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": False,
        "standby_power_w": None,
    },
    8: {
        "code": "WDI",
        "name": "Wind Direction Indicator",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 10.0,
        "default_engine": "se_mini",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": False,
        "standby_power_w": None,
    },
    9: {
        "code": "SIGN-L",
        "name": "Large Guidance Sign",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 35.0,
        "default_engine": "se_compact",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": False,
        "standby_power_w": None,
    },
    10: {
        "code": "SIGN-M",
        "name": "Medium Guidance Sign",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 22.0,
        "default_engine": "se_compact",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": False,
        "standby_power_w": None,
    },
    11: {
        "code": "SIGN-S",
        "name": "Small Guidance Sign",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 15.0,
        "default_engine": "se_compact",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_optima", "se_max"],
        "supports_intensity_adjustment": False,
        "standby_power_w": None,
    },
}

from core.devices_avlite import AVLITE_DEVICES

DEVICES.update(AVLITE_DEVICES)

def get_device_by_code(device_code: str):
    for _, device in DEVICES.items():
        if device["code"] == device_code:
            return device
    return None


def get_device_by_id(device_id: int):
    return DEVICES.get(device_id)


def get_lamp_variants(device_code: str) -> list[str]:
    device = get_device_by_code(device_code)
    if not device:
        return []
    return list(device.get("lamp_variants", {}).keys())


def get_default_lamp_variant(device_code: str):
    device = get_device_by_code(device_code)
    if not device:
        return None
    return device.get("default_lamp_variant")


def get_variant_power(device_code: str, lamp_variant: str):
    device = get_device_by_code(device_code)
    if not device:
        return None

    variants = device.get("lamp_variants", {})
    if lamp_variant in variants:
        return float(variants[lamp_variant]["power_w"])

    default_power = device.get("default_power")
    return float(default_power) if default_power is not None else None
