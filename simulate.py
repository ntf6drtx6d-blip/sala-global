# simulate.py
import os
import time
from urllib.parse import urlencode

from devices import DEVICES, SOLAR_ENGINES
from pvgis_client import pvcalc_monthly_wh_per_day, shs_monthly, load_cache, save_cache

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def lat_based_tilt(lat):
    s = abs(float(lat))
    return max(5.0, min(55.0, s))


def get_optimal_angles(lat, lon, cache, key):
    slope = lat_based_tilt(lat)
    az = 0.0
    cache.setdefault(key, {})["angles"] = {"slope": slope, "azimuth": az}
    save_cache(cache)
    return slope, az


def choose_azimuth_fixed_for_year(lat, lon, tilt_deg, cache, key):
    return 0.0 if float(lat) >= 0 else 180.0


def dataset_label():
    return os.getenv("S4GA_PVGIS_DATASET", "PVGIS-SARAH2 (fallback: PVGIS-ERA5)")


def resolve_device_config(device_id, per_device_config=None):
    per_device_config = per_device_config or {}
    dspec = DEVICES[device_id]
    user_cfg = per_device_config.get(device_id, {})

    power = float(user_cfg.get("power", dspec["default_power"]))

    if dspec["system_type"] == "builtin":
        cfg = {
            "device_id": device_id,
            "device_code": dspec["code"],
            "device_name": dspec["name"],
            "system_type": "builtin",
            "engine_key": None,
            "engine_name": "BUILT-IN",
            "power": power,
            "pv": float(dspec["pv"]),
            "batt_std": float(dspec["batt"]),
            "batt": float(dspec["batt"]),
            "battery_mode": "Std",
            "fixed": bool(dspec.get("fixed", True)),
            "tilt_options": [float(dspec.get("tilt", 33))],
            "tilt": float(dspec.get("tilt", 33)),
        }
        return cfg

    engine_key = user_cfg.get("engine_key", dspec["default_engine"])
    if engine_key not in SOLAR_ENGINES:
        engine_key = dspec["default_engine"]

    eng = SOLAR_ENGINES[engine_key]
    battery_mode = user_cfg.get("battery_mode", "Std")
    batt = float(eng["batt_ext"]) if (battery_mode == "Ext" and eng.get("batt_ext")) else float(eng["batt"])

    cfg = {
        "device_id": device_id,
        "device_code": dspec["code"],
        "device_name": dspec["name"],
        "system_type": "external_engine",
        "engine_key": engine_key,
        "engine_name": eng["short_name"],
        "power": power,
        "pv": float(eng["pv"]),
        "batt_std": float(eng["batt"]),
        "batt": batt,
        "battery_mode": battery_mode,
        "fixed": bool(eng.get("fixed", False)),
        "tilt_options": list(eng.get("tilt_options", [15, 35, 55])),
        "tilt": None,
    }
    return cfg


def build_pvgis_meta(lat, lon, resolved_cfg, tilt, azim):
    dataset = dataset_label()

    pvcalc_params = {
        "lat": float(lat),
        "lon": float(lon),
        "peakpower": max(0.05, float(resolved_cfg["pv"]) / 1000.0),
        "loss": float(os.getenv("S4GA_PVCALC_LOSS", "14")),
        "angle": float(tilt),
        "aspect": float(azim),
        "usehorizon": 1,
        "mountingplace": "free",
        "optimalangles": 0,
        "outputformat": "json",
        "raddatabase": os.getenv("S4GA_PVGIS_DATASET", "PVGIS-SARAH2"),
    }

    shs_params = {
        "lat": float(lat),
        "lon": float(lon),
        "peakpower": max(1.0, float(resolved_cfg["pv"])),
        "batterysize": max(10.0, float(resolved_cfg["batt"])),
        "consumptionday": "varied by SALA binary search",
        "cutoff": 40,
        "angle": float(tilt),
        "aspect": float(azim),
        "usehorizon": 1,
        "outputformat": "json",
        "raddatabase": os.getenv("S4GA_PVGIS_DATASET", "PVGIS-SARAH2"),
    }

    pvcalc_url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?" + urlencode(
        {k: v for k, v in pvcalc_params.items() if k != "raddatabase"} | {"raddatabase": pvcalc_params["raddatabase"]}
    )
    shs_url = "https://re.jrc.ec.eu