# core/simulate.py
# ACTION: REPLACE ENTIRE FILE

import os
import time
import calendar
from urllib.parse import urlencode

from core.devices import DEVICES, SOLAR_ENGINES
from core.avlite_fs import simulate_avlite_for_devices


def _parse_device_identifier(device_identifier, per_device_config=None):
    per_device_config = per_device_config or {}
    user_cfg = per_device_config.get(device_identifier) or per_device_config.get(str(device_identifier), {})

    lamp_variant = user_cfg.get("lamp_variant")
    raw_id = user_cfg.get("device_id", device_identifier)

    if isinstance(raw_id, str) and "||" in raw_id:
        raw_id, parsed_variant = raw_id.split("||", 1)
        lamp_variant = lamp_variant or parsed_variant

    if isinstance(device_identifier, str) and "||" in device_identifier:
        raw_id2, parsed_variant = device_identifier.split("||", 1)
        raw_id = raw_id2
        lamp_variant = lamp_variant or parsed_variant

    try:
        device_id = int(raw_id)
    except Exception:
        device_id = int(device_identifier)

    return device_id, lamp_variant, user_cfg


def _variant_short_label(lamp_variant):
    mapping = {
        "Runway edge light": "RWY edge",
        "Runway threshold/end light": "THR/END",
        "Taxiway edge light": "TWY edge",
        "Approach light": "APP",
        "Obstruction Type A LI light": "OBS LI",
        "TLOF light": "TLOF",
        "FATO light": "FATO",
    }
    return mapping.get(lamp_variant, lamp_variant) if lamp_variant else None

from pvgis_client import pvcalc_monthly_wh_per_day, shs_monthly, load_cache, save_cache

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _days_in_month_non_leap(month_index_1_based: int) -> int:
    return calendar.monthrange(2025, month_index_1_based)[1]


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
    parsed_device_id, lamp_variant, user_cfg = _parse_device_identifier(device_id, per_device_config)
    dspec = DEVICES[parsed_device_id]

    if lamp_variant and dspec.get("lamp_variants") and lamp_variant in dspec["lamp_variants"]:
        default_power = float(dspec["lamp_variants"][lamp_variant]["power_w"])
    else:
        default_power = float(dspec["default_power"])

    power = float(user_cfg.get("power", default_power))
    variant_suffix = f" / {_variant_short_label(lamp_variant)}" if lamp_variant else ""
    display_name = user_cfg.get("display_label") or f"{dspec['name']}{variant_suffix}"

    if dspec["system_type"] == "builtin":
        cfg = {
            "device_id": parsed_device_id,
            "device_code": dspec["code"],
            "device_name": display_name,
            "lamp_variant": lamp_variant,
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
        "device_id": parsed_device_id,
        "device_code": dspec["code"],
        "device_name": display_name,
        "lamp_variant": lamp_variant,
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
    shs_url = "https://re.jrc.ec.europa.eu/api/v5_2/SHScalc?" + urlencode(
        {
            "lat": float(lat),
            "lon": float(lon),
            "peakpower": max(1.0, float(resolved_cfg["pv"])),
            "batterysize": max(10.0, float(resolved_cfg["batt"])),
            "consumptionday": 100,
            "cutoff": 40,
            "angle": float(tilt),
            "aspect": float(azim),
            "usehorizon": 1,
            "outputformat": "json",
            "raddatabase": os.getenv("S4GA_PVGIS_DATASET", "PVGIS-SARAH2"),
        }
    )

    return {
        "dataset": dataset,
        "pvcalc_endpoint": "PVcalc",
        "shs_endpoint": "SHScalc",
        "pvcalc_params": pvcalc_params,
        "shs_params": shs_params,
        "pvcalc_url_example": pvcalc_url,
        "shs_url_example": shs_url,
        "explanation": (
            "PVGIS performs the solar and off-grid calculations. "
            "SALA sends the selected input parameters to PVGIS, retrieves the responses, "
            "and organizes them into a device-level feasibility assessment."
        ),
    }


def max_wh_for_month_fast(lat, lon, pv_wp, batt_wh, tilt, aspect, mi):
    hi_cap = int(min(20000, max(3 * batt_wh, 8 * pv_wp * 24)))

    def fe_for(cons_wh_day):
        if cons_wh_day <= 0:
            return 0.0

        monthly = shs_monthly(
            lat, lon,
            pv_wp, batt_wh,
            float(cons_wh_day),
            tilt, aspect
        )
        return float(monthly[mi].get("f_e", 0.0))

    lo, hi = 1, hi_cap
    best = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        fe = fe_for(mid)

        if fe <= 0.0:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return int(best)


def get_empty_battery_stats_for_required_mode(lat, lon, resolved, required_hrs, tilt, aspect):
    """
    Uses the REAL PVGIS monthly f_e values for the selected operating mode.
    """
    daily_wh = float(required_hrs) * max(float(resolved["power"]), 0.05)

    monthly = shs_monthly(
        lat, lon,
        resolved["pv"],
        resolved["batt"],
        daily_wh,
        tilt, aspect
    )

    pct_by_month = []
    days_by_month = []

    total_days = 0
    weighted_pct_sum = 0.0

    for mi in range(12):
        f_e = float(monthly[mi].get("f_e", 0.0))
        dim = _days_in_month_non_leap(mi + 1)
        pct_by_month.append(f_e)
        days_by_month.append(round(dim * f_e / 100.0))

        weighted_pct_sum += f_e * dim
        total_days += dim

    overall_pct = weighted_pct_sum / total_days if total_days else 0.0

    return pct_by_month, days_by_month, overall_pct


def simulate_for_devices(
    loc,
    required_hrs,
    selected_ids,
    per_device_config=None,
    az_override=None,
    progress_callback=None
):
    per_device_config = per_device_config or {}

    lat, lon = loc["lat"], loc["lon"]
    cache = load_cache()
    key = f"{round(lat,5)},{round(lon,5)}"

    slope, _ = get_optimal_angles(lat, lon, cache, key)
    if slope is None:
        slope = lat_based_tilt(lat)

    results = {}
    az_for_tilt = {}

    avlite_ids = []
    standard_ids = []

    for did in selected_ids:
        try:
            did_int = int(str(did).split("||", 1)[0])
        except Exception:
            did_int = int(did)

        dspec = DEVICES[did_int]
        if dspec.get("system_type") == "avlite_fixture":
            avlite_ids.append(did)
        else:
            standard_ids.append(did)

    if avlite_ids:
        avlite_results, avlite_overall, avlite_worst = simulate_avlite_for_devices(
            loc=loc,
            required_hrs=required_hrs,
            selected_ids=avlite_ids,
            per_device_config=per_device_config,
            progress_callback=progress_callback,
        )
        results.update(avlite_results)

    total_steps = max(1, len(standard_ids) * 12) if standard_ids else 1
    completed_steps = 0
    started_at = time.time()

    for did in standard_ids:
        resolved = resolve_device_config(did, per_device_config)
        tilt_options = resolved["tilt_options"]
        tilt = tilt_options[0] if resolved["fixed"] else min(tilt_options, key=lambda x: abs(x - slope))

        if az_override is not None:
            azim = float(az_override)
        elif tilt in az_for_tilt:
            azim = az_for_tilt[tilt]
        else:
            azim = choose_azimuth_fixed_for_year(lat, lon, tilt, cache, key)
            az_for_tilt[tilt] = azim

        hours = []
        monthly_energy_wh = []

        for mi in range(12):
            best_wh = max_wh_for_month_fast(
                lat=lat,
                lon=lon,
                pv_wp=resolved["pv"],
                batt_wh=resolved["batt"],
                tilt=tilt,
                aspect=azim,
                mi=mi
            )
            monthly_energy_wh.append(best_wh)
            hours.append(min(best_wh / max(resolved["power"], 0.05), 24.0))

            completed_steps += 1
            if progress_callback:
                elapsed = time.time() - started_at
                pct = completed_steps / total_steps
                eta = (elapsed / completed_steps) * (total_steps - completed_steps) if completed_steps else 0
                progress_callback(
                    completed_steps,
                    total_steps,
                    pct,
                    elapsed,
                    eta,
                    resolved["device_name"],
                    MONTHS[mi]
                )

        min_margin = min(h - required_hrs for h in hours)
        status = "PASS" if all(h >= required_hrs - 1e-6 for h in hours) else "FAIL"
        fail_months = [MONTHS[i] for i, h in enumerate(hours) if h + 1e-6 < required_hrs]

        empty_battery_pct_by_month, empty_battery_days_by_month, overall_empty_battery_pct =             get_empty_battery_stats_for_required_mode(
                lat=lat,
                lon=lon,
                resolved=resolved,
                required_hrs=required_hrs,
                tilt=tilt,
                aspect=azim
            )

        pvgis_meta = build_pvgis_meta(lat, lon, resolved, tilt, azim)

        result_key = resolved['device_name']

        results[result_key] = {
            "device_id": did,
            "device_code": resolved["device_code"],
            "name": resolved["device_name"],
            "system_type": resolved["system_type"],
            "engine": resolved["engine_name"],
            "engine_key": resolved["engine_key"],
            "pv": resolved["pv"],
            "batt": resolved["batt"],
            "batt_std": resolved["batt_std"],
            "battery_mode": resolved["battery_mode"],
            "tilt": tilt,
            "azim": float(azim),
            "hours": hours,
            "status": status,
            "min_margin": min_margin,
            "fail_months": fail_months,
            "power": resolved["power"],
            "lamp_variant": resolved.get("lamp_variant"),
            "monthly_energy_wh": monthly_energy_wh,
            "empty_battery_pct_by_month": empty_battery_pct_by_month,
            "empty_battery_days_by_month": empty_battery_days_by_month,
            "overall_empty_battery_pct": overall_empty_battery_pct,
            "pvgis_meta": pvgis_meta,
        }

    worst_name, worst_gap = None, 1e9
    overall = "PASS"

    for name, r in results.items():
        gap = r["min_margin"]
        if gap < worst_gap:
            worst_gap, worst_name = gap, name
        if r["status"] == "FAIL":
            overall = "FAIL"

    return results, overall, worst_name, worst_gap, slope
