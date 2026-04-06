# devices.py

SOLAR_ENGINES = {
    "se_micro": {
        "key": "se_micro",
        "name": "Solar Engine Micro",
        "short_name": "SE MICRO",
        "pv": 25,
        "batt": 216,
        "batt_ext": None,
        "tilt_options": [33],
        "fixed": True,
    },
    "se_mini": {
        "key": "se_mini",
        "name": "Solar Engine Mini",
        "short_name": "SE MINI",
        "pv": 40,
        "batt": 336,
        "batt_ext": None,
        "tilt_options": [33],
        "fixed": True,
    },
    "se_compact": {
        "key": "se_compact",
        "name": "Solar Engine Compact",
        "short_name": "SE COMPACT",
        "pv": 185,
        "batt": 1440,
        "batt_ext": 2880,
        "tilt_options": [15, 35, 55],
        "fixed": False,
    },
    "se_max": {
        "key": "se_max",
        "name": "Solar Engine Max",
        "short_name": "SE MAX",
        "pv": 720,
        "batt": 3000,
        "batt_ext": 6000,
        "tilt_options": [15, 35, 55],
        "fixed": False,
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
        "tilt": 33,
        "fixed": True,
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
        "tilt": 33,
        "fixed": True,
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
        "default_power": 1.48,
        "pv": 5,
        "batt": 54,
        "tilt": 33,
        "fixed": True,
        "default_lamp_variant": "Runway edge light",
        "lamp_variants": {
            "Runway edge light": {"power_w": 1.48},
            "Runway threshold/end light": {"power_w": 0.73},
            "Taxiway edge light": {"power_w": 0.2},
            "Obstruction Type A LI light": {"power_w": 0.6},
            "TLOF light": {"power_w": 1.33},
            "FATO light": {"power_w": 4.61},
        },
    },
    4: {
        "code": "SP-200",
        "name": "SP-200 Inset Light",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 5.0,
        "default_engine": "se_mini",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    5: {
        "code": "PAPI",
        "name": "PAPI",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 320.0,
        "default_engine": "se_max",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    6: {
        "code": "A-PAPI",
        "name": "A-PAPI",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 160.0,
        "default_engine": "se_max",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    7: {
        "code": "RGL",
        "name": "Runway Guard Light",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 3.0,
        "default_engine": "se_mini",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    8: {
        "code": "WDI",
        "name": "Wind Direction Indicator",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 10.0,
        "default_engine": "se_mini",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    9: {
        "code": "SIGN-L",
        "name": "Large Guidance Sign",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 35.0,
        "default_engine": "se_compact",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    10: {
        "code": "SIGN-M",
        "name": "Medium Guidance Sign",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 22.0,
        "default_engine": "se_compact",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
    },
    11: {
        "code": "SIGN-S",
        "name": "Small Guidance Sign",
        "manufacturer": "S4GA",
        "system_type": "external_engine",
        "default_power": 15.0,
        "default_engine": "se_compact",
        "compatible_engines": ["se_micro", "se_mini", "se_compact", "se_max"],
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
