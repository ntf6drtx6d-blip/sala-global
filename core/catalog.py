from copy import deepcopy

from core.db import list_device_catalog
from core.devices import DEVICES as STATIC_DEVICES, SOLAR_ENGINES as STATIC_SOLAR_ENGINES


def _safe_list_device_catalog():
    try:
        return list_device_catalog()
    except Exception:
        return []


def get_runtime_catalog():
    rows = _safe_list_device_catalog()
    if not rows:
        return deepcopy(STATIC_DEVICES), deepcopy(STATIC_SOLAR_ENGINES)

    devices = {}
    engines = {}

    for row in rows:
        metadata = row.get("metadata") or {}
        entity_type = row.get("entity_type")

        if entity_type == "solar_engine":
            tilt_options = row.get("panel_tilt_options") or []
            external_battery_wh = metadata.get("battery_wh_external")
            if not tilt_options and row.get("panel_tilt_deg") is not None:
                tilt_options = [float(row.get("panel_tilt_deg"))]
            engines[row["code"]] = {
                "key": row["code"],
                "name": row.get("name") or row["code"],
                "short_name": metadata.get("short_name") or str(row["code"]).upper(),
                "pv": float(row.get("panel_wp") or 0.0),
                "batt": float(row.get("battery_wh") or 0.0),
                "battery_type": row.get("battery_type"),
                "cutoff_pct": row.get("cutoff_pct"),
                "batt_ext": float(external_battery_wh) if external_battery_wh is not None else None,
                "tilt_options": tilt_options,
                "fixed": len(tilt_options) <= 1,
                "standby_power_w": row.get("standby_power_w"),
            }
            continue

        runtime_id = row.get("runtime_id")
        if runtime_id is None:
            continue

        tilt_options = row.get("panel_tilt_options") or metadata.get("tilt_options") or []
        lamp_variants = metadata.get("lamp_variants") or {}
        device = {
            "code": row["code"],
            "name": row.get("name") or row["code"],
            "manufacturer": row.get("manufacturer") or "Unknown",
            "system_type": row.get("system_type") or "builtin",
            "default_power": float(row.get("default_power_w") or 0.0),
            "pv": float(row.get("panel_wp") or 0.0),
            "batt": float(row.get("battery_wh") or 0.0),
            "tilt": row.get("panel_tilt_deg"),
            "fixed": len(tilt_options) <= 1 if tilt_options else True,
            "tilt_options": tilt_options,
            "supports_intensity_adjustment": bool(row.get("supports_intensity_adjustment")),
            "standby_power_w": row.get("standby_power_w"),
            "default_lamp_variant": metadata.get("default_lamp_variant"),
            "lamp_variants": lamp_variants,
            "default_engine": row.get("default_engine_code"),
            "compatible_engines": row.get("compatible_engine_codes") or [],
            "fixture_key": metadata.get("fixture_key"),
            "battery_type": row.get("battery_type"),
            "cutoff_pct": row.get("cutoff_pct"),
        }
        devices[int(runtime_id)] = device

    if not devices:
        devices = deepcopy(STATIC_DEVICES)
    if not engines:
        engines = deepcopy(STATIC_SOLAR_ENGINES)

    return devices, engines


def get_runtime_devices():
    devices, _ = get_runtime_catalog()
    return devices


def get_runtime_device(device_id):
    try:
        return get_runtime_devices().get(int(device_id))
    except Exception:
        return None


def runtime_device_label(device_id):
    device = get_runtime_device(device_id)
    if device:
        return device.get("name") or device.get("code") or str(device_id)
    return str(device_id)


def runtime_device_variant_label(device_id, variant=None):
    base = runtime_device_label(device_id)
    if variant:
        return f"{base} / {variant}"
    return base
