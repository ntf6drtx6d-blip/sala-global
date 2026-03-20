# devices.py

SOLAR_ENGINES = {
    "mini": {
        "code": "mini",
        "name": "Solar Engine Mini",
        "pv": 40,
        "batt": 336,
        "batt_ext": None,
        "tilt": 33,
        "fixed": True,
        "tiltset": [33],
    },
    "compact": {
        "code": "compact",
        "name": "Solar Engine Compact",
        "pv": 185,
        "batt": 1440,
        "batt_ext": 2880,
        "tilt": None,
        "fixed": False,
        "tiltset": [15, 35, 55],
    },
    "max": {
        "code": "max",
        "name": "Solar Engine Max",
        "pv": 720,
        "batt": 2640,
        "batt_ext": 5280,
        "tilt": None,
        "fixed": False,
        "tiltset": [15, 35, 55],
    },
}

DEVICES = {
    1: {
        "name": "PRO SP-401SMI",
        "system_type": "builtin",
        "power": 2.6,
        "pv": 25,
        "batt": 216,
        "tilt": 33,
        "fixed": True,
        "builtin_label": "Built-in solar module and battery",
    },
    2: {
        "name": "CAT-I SP-501SHI",
        "system_type": "builtin",
        "power": 8.0,
        "pv": 25,
        "batt": 216,
        "tilt": 33,
        "fixed": True,
        "builtin_label": "Built-in solar module and battery",
    },
    3: {
        "name": "SP-301SLI",
        "system_type": "builtin",
        "power": 1.4,
        "pv": 5,
        "batt": 54,
        "tilt": 33,
        "fixed": True,
        "builtin_label": "Built-in solar module and battery",
    },
    4: {
        "name": "SP-200 Inset Light",
        "system_type": "external_engine",
        "power": 5.0,
        "default_engine": "mini",
        "allowed_engines": ["mini", "compact", "max"],
    },
    5: {
        "name": "PAPI",
        "system_type": "external_engine",
        "power": 320.0,
        "default_engine": "max",
        "allowed_engines": ["max"],
    },
    6: {
        "name": "A-PAPI",
        "system_type": "external_engine",
        "power": 160.0,
        "default_engine": "max",
        "allowed_engines": ["max"],
    },
    7: {
        "name": "RGL",
        "system_type": "external_engine",
        "power": 3.0,
        "default_engine": "mini",
        "allowed_engines": ["mini", "compact", "max"],
    },
    8: {
        "name": "WDI",
        "system_type": "external_engine",
        "power": 10.0,
        "default_engine": "mini",
        "allowed_engines": ["mini", "compact", "max"],
    },
    9: {
        "name": "Large Sign",
        "system_type": "external_engine",
        "power": 35.0,
        "default_engine": "compact",
        "allowed_engines": ["compact", "max"],
    },
    10: {
        "name": "Medium Sign",
        "system_type": "external_engine",
        "power": 22.0,
        "default_engine": "compact",
        "allowed_engines": ["compact", "max"],
    },
    11: {
        "name": "Small Sign",
        "system_type": "external_engine",
        "power": 15.0,
        "default_engine": "compact",
        "allowed_engines": ["compact", "max"],
    },
}


def get_engine(engine_code: str) -> dict:
    if engine_code not in SOLAR_ENGINES:
        raise KeyError(f"Unknown solar engine: {engine_code}")
    return SOLAR_ENGINES[engine_code]


def resolve_device_configuration(
    device_id: int,
    selected_engine_code: str | None = None,
    battery_mode: str = "Std",
    power_override: float | None = None,
) -> dict:
    """
    Returns a normalized device configuration ready for simulation.
    """
    d = DEVICES[device_id]
    default_power = float(d["power"])
    power = default_power if power_override is None else float(power_override)

    if d["system_type"] == "builtin":
        return {
            "device_id": device_id,
            "name": d["name"],
            "system_type": "builtin",
            "engine_code": None,
            "engine_name": "Built-in",
            "power": power,
            "default_power": default_power,
            "pv": float(d["pv"]),
            "batt": float(d["batt"]),
            "batt_mode": "Std",
            "tilt": d.get("tilt", 33),
            "fixed": bool(d.get("fixed", True)),
            "tiltset": d.get("tiltset", [d.get("tilt", 33)]),
            "config_label": d.get("builtin_label", "Built-in configuration"),
        }

    engine_code = selected_engine_code or d["default_engine"]
    eng = get_engine(engine_code)

    batt = eng["batt"]
    if battery_mode == "Ext" and eng.get("batt_ext"):
        batt = eng["batt_ext"]

    return {
        "device_id": device_id,
        "name": d["name"],
        "system_type": "external_engine",
        "engine_code": engine_code,
        "engine_name": eng["name"],
        "power": power,
        "default_power": default_power,
        "pv": float(eng["pv"]),
        "batt": float(batt),
        "batt_mode": battery_mode,
        "tilt": eng.get("tilt"),
        "fixed": bool(eng.get("fixed", False)),
        "tiltset": eng.get("tiltset", [15, 35, 55]),
        "config_label": f"{eng['name']} ({'Extended battery' if battery_mode == 'Ext' else 'Standard battery'})",
    }