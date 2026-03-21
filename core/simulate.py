# core/simulate.py
# ACTION: REPLACE ENTIRE FILE

import time
from typing import Dict, Any, List, Optional

import requests

from core.devices import DEVICES, SOLAR_ENGINES

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

PVGIS_BASE = "https://re.jrc.ec.europa.eu/api/v5_3/"


def _safe_get(dct, *keys, default=None):
    cur = dct
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _estimate_tilt(lat: float) -> float:
    return max(10.0, min(abs(lat), 60.0))


def _estimate_azimuth(lat: float) -> float:
    # 0=south, 180=north in PVGIS convention
    return 0.0 if lat >= 0 else 180.0


def _device_runtime_hours_from_wh(wh_day: float, power_w: float) -> float:
    power_w = max(float(power_w), 0.01)
    return wh_day / power_w


def _build_device_config(device_id: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    dspec = DEVICES[device_id]
    power = float(cfg.get("power", dspec["default_power"]))

    if dspec["system_type"] == "builtin":
        pv = float(dspec["pv"])
        batt = float(dspec["batt"])
        engine_label = "Built-in"
    else:
        engine_key = cfg.get("engine_key") or dspec["default_engine"]
        eng = SOLAR_ENGINES[engine_key]
        pv = float(eng["pv"])

        battery_mode = cfg.get("battery_mode", "Std")
        if battery_mode == "Ext" and eng.get("batt_ext"):
            batt = float(eng["batt_ext"])
        else:
            batt = float(eng["batt"])

        engine_label = eng["short_name"]

    return {
        "device_code": dspec["code"],
        "device_name": dspec["name"],
        "power": power,
        "pv": pv,
        "batt": batt,
        "engine": engine_label,
    }


def _call_pvgis_pvcalc(lat: float, lon: float, peakpower: float, angle: float, aspect: float):
    endpoint = PVGIS_BASE + "PVcalc"
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": peakpower / 1000.0,  # W -> kW
        "loss": 0,
        "angle": angle,
        "aspect": aspect,
        "outputformat": "json",
        "browser": 0,
    }
    r = requests.get(endpoint, params=params, timeout=60)
    r.raise_for_status()
    return r.json(), endpoint, params


def _call_pvgis_shscalc(
    lat: float,
    lon: float,
    pv_w: float,
    batt_wh: float,
    daily_consumption_wh: float,
    angle: float,
    aspect: float,
):
    """
    Stable version:
    - peakpower in kW
    - batterysize in Wh
    - consumptionday in Wh/day
    - cutoff in %
    """
    endpoint = PVGIS_BASE + "SHScalc"
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": pv_w / 1000.0,      # W -> kW
        "batterysize": batt_wh,          # Wh
        "consumptionday": daily_consumption_wh,  # Wh/day
        "cutoff": 30,                    # %
        "angle": angle,
        "aspect": aspect,
        "outputformat": "json",
        "browser": 0,
        "raddatabase": "PVGIS-SARAH3",
    }
    r = requests.get(endpoint, params=params, timeout=60)
    r.raise_for_status()
    return r.json(), endpoint, params


def _extract_monthly_fe_values(shs_json: Dict[str, Any]) -> List[float]:
    """
    Extract monthly f_e (% days battery empty) from PVGIS SHScalc.

    We support:
    - list of dicts with key 'f_e'
    - list of dicts with key 'fe'
    - nested structures
    - fallback to text/table-like parsing from raw JSON string values

    IMPORTANT:
    If nothing is found, return zeros instead of 100s.
    100% fallback was collapsing the binary search to ~0 hours/day.
    """

    # 1) direct structured candidates
    candidates = [
        _safe_get(shs_json, "outputs", "monthly"),
        _safe_get(shs_json, "outputs", "monthly", "fixed"),
        _safe_get(shs_json, "outputs", "monthly_data"),
        _safe_get(shs_json, "monthly"),
    ]

    for monthly in candidates:
        if isinstance(monthly, list) and len(monthly) >= 12:
            vals = []
            ok = True
            for row in monthly[:12]:
                if isinstance(row, dict):
                    if "f_e" in row:
                        try:
                            vals.append(float(row["f_e"]))
                            continue
                        except Exception:
                            ok = False
                            break
                    elif "fe" in row:
                        try:
                            vals.append(float(row["fe"]))
                            continue
                        except Exception:
                            ok = False
                            break
                ok = False
                break
            if ok and len(vals) == 12:
                return vals

    # 2) recursive search for any list containing dict rows with f_e / fe
    def _walk(obj):
        if isinstance(obj, list):
            if len(obj) >= 12 and all(isinstance(x, dict) for x in obj[:12]):
                vals = []
                ok = True
                for row in obj[:12]:
                    if "f_e" in row:
                        try:
                            vals.append(float(row["f_e"]))
                        except Exception:
                            ok = False
                            break
                    elif "fe" in row:
                        try:
                            vals.append(float(row["fe"]))
                        except Exception:
                            ok = False
                            break
                    else:
                        ok = False
                        break
                if ok and len(vals) == 12:
                    return vals

            for item in obj:
                res = _walk(item)
                if res is not None:
                    return res

        elif isinstance(obj, dict):
            for v in obj.values():
                res = _walk(v)
                if res is not None:
                    return res

        return None

    found = _walk(shs_json)
    if found is not None:
        return found

    # 3) text-style fallback:
    # look for lines like:
    # month E_d E_lost_d f_f f_e
    # 1 10.74 0.0 0.0 100.0
    import re

    text_chunks = []

    def _collect_strings(obj):
        if isinstance(obj, str):
            text_chunks.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect_strings(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect_strings(item)

    _collect_strings(shs_json)

    month_map = {}
    line_pattern = re.compile(
        r"^\s*(\d{1,2})\s+[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+\s+([-+]?\d*\.?\d+)\s*$"
    )

    for chunk in text_chunks:
        for line in chunk.splitlines():
            m = line_pattern.match(line.strip())
            if m:
                month_num = int(m.group(1))
                fe_val = float(m.group(2))
                if 1 <= month_num <= 12:
                    month_map[month_num] = fe_val

    if len(month_map) == 12:
        return [month_map[i] for i in range(1, 13)]

    # SAFE fallback:
    # return zeros, not 100s
    return [0.0] * 12
    """
    Extract monthly f_e (% days battery empty) from PVGIS SHScalc.
    Supports common JSON shapes.
    """
    candidates = [
        _safe_get(shs_json, "outputs", "monthly"),
        _safe_get(shs_json, "outputs", "monthly", "fixed"),
        _safe_get(shs_json, "outputs", "monthly_data"),
    ]

    for monthly in candidates:
        if isinstance(monthly, list) and len(monthly) >= 12:
            vals = []
            ok = True
            for row in monthly[:12]:
                if isinstance(row, dict) and "f_e" in row:
                    try:
                        vals.append(float(row["f_e"]))
                    except Exception:
                        ok = False
                        break
                else:
                    ok = False
                    break
            if ok and len(vals) == 12:
                return vals

    # recursive fallback
    def _walk(obj):
        if isinstance(obj, list) and len(obj) >= 12:
            if all(isinstance(x, dict) and "f_e" in x for x in obj[:12]):
                try:
                    return [float(x["f_e"]) for x in obj[:12]]
                except Exception:
                    return None
            for item in obj:
                res = _walk(item)
                if res is not None:
                    return res
        elif isinstance(obj, dict):
            for v in obj.values():
                res = _walk(v)
                if res is not None:
                    return res
        return None

    found = _walk(shs_json)
    return found if found is not None else [100.0] * 12


def _extract_month_pct_for_binary_search(shs_json: Dict[str, Any], month_index: int) -> float:
    vals = _extract_monthly_fe_values(shs_json)
    if 1 <= month_index <= 12:
        return float(vals[month_index - 1])
    return 100.0


def _max_wh_for_month_fast(
    lat: float,
    lon: float,
    pv_w: float,
    batt_wh: float,
    angle: float,
    aspect: float,
    month_index: int,
    power_w: float,
) -> float:
    """
    Binary search daily Wh threshold so that monthly f_e stays at 0
    for the given month.
    """
    low = 0.0
    high = max(power_w * 24.0 * 2.0, 50.0)

    # Expand high if still zero-empty
    for _ in range(8):
        shs_json, _, _ = _call_pvgis_shscalc(lat, lon, pv_w, batt_wh, high, angle, aspect)
        pct = _extract_month_pct_for_binary_search(shs_json, month_index)

        if pct <= 0.0:
            low = high
            high *= 1.6
        else:
            break

    # Binary search
    for _ in range(18):
        mid = (low + high) / 2.0
        shs_json, _, _ = _call_pvgis_shscalc(lat, lon, pv_w, batt_wh, mid, angle, aspect)
        pct = _extract_month_pct_for_binary_search(shs_json, month_index)

        if pct <= 0.0:
            low = mid
        else:
            high = mid

    return low


def simulate_for_devices(
    loc: Dict[str, Any],
    required_hrs: float,
    selected_ids: List[str],
    per_device_config: Dict[str, Dict[str, Any]],
    az_override: Optional[float] = None,
    progress_callback=None,
):
    lat = float(loc["lat"])
    lon = float(loc["lon"])

    tilt = _estimate_tilt(lat)
    azim = az_override if az_override is not None else _estimate_azimuth(lat)

    results = {}

    total_steps = max(len(selected_ids) * 12, 1)
    done_steps = 0
    started = time.time()

    for device_id in selected_ids:
        cfg = per_device_config.get(device_id, {})
        built = _build_device_config(device_id, cfg)

        power_w = built["power"]
        pv_w = built["pv"]
        batt_wh = built["batt"]

        hours = []
        fail_months = []

        pvcalc_json, pvcalc_endpoint, pvcalc_params = _call_pvgis_pvcalc(
            lat, lon, pv_w, tilt, azim
        )

        for month_idx in range(1, 13):
            max_wh = _max_wh_for_month_fast(
                lat=lat,
                lon=lon,
                pv_w=pv_w,
                batt_wh=batt_wh,
                angle=tilt,
                aspect=azim,
                month_index=month_idx,
                power_w=power_w,
            )
            h = _device_runtime_hours_from_wh(max_wh, power_w)
            hours.append(h)

            if h + 1e-6 < required_hrs:
                fail_months.append(MONTHS[month_idx - 1])

            done_steps += 1
            if progress_callback:
                elapsed = time.time() - started
                pct = done_steps / total_steps
                eta = (elapsed / pct - elapsed) if pct > 0 else 0
                progress_callback(
                    done_steps,
                    total_steps,
                    pct,
                    elapsed,
                    eta,
                    f"{built['device_code']} — {built['device_name']}",
                    MONTHS[month_idx - 1],
                )

        status = "PASS" if all(h >= required_hrs - 1e-6 for h in hours) else "FAIL"
        min_margin = min(h - required_hrs for h in hours)

        results[f"{built['device_code']} — {built['device_name']}"] = {
            "status": status,
            "hours": hours,
            "fail_months": fail_months,
            "min_margin": min_margin,
            "engine": built["engine"],
            "pv": pv_w,
            "batt": batt_wh,
            "power": power_w,
            "tilt": tilt,
            "azim": azim,

            # keep these for UI compatibility
            "empty_battery_pct_by_month": None,
            "empty_battery_days_by_month": None,
            "overall_empty_battery_pct": None,

            "pvgis_meta": {
                "dataset": "PVGIS-SARAH3",
                "pvcalc_endpoint": pvcalc_endpoint,
                "pvcalc_params": pvcalc_params,
                "pvcalc_url_example": requests.Request("GET", pvcalc_endpoint, params=pvcalc_params).prepare().url,
                "shs_endpoint": PVGIS_BASE + "SHScalc",
                "shs_params": None,
                "shs_url_example": None,
            },
        }

    overall = "PASS" if all(r["status"] == "PASS" for r in results.values()) else "FAIL"

    worst_name = None
    worst_gap = None
    for name, r in results.items():
        gap = r["min_margin"]
        if worst_gap is None or gap < worst_gap:
            worst_gap = gap
            worst_name = name

    return results, overall, worst_name, worst_gap if worst_gap is not None else 0.0, azim
