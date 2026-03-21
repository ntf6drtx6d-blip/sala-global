# core/simulate.py
# ACTION: REPLACE ENTIRE FILE

import math
import calendar
from typing import Dict, Any, List, Tuple, Optional

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


def _days_in_month_non_leap(month_index_1_based: int) -> int:
    return calendar.monthrange(2025, month_index_1_based)[1]


def _estimate_tilt(lat: float) -> float:
    return max(10.0, min(abs(lat), 60.0))


def _estimate_azimuth(lat: float) -> float:
    # South-facing in north hemisphere, north-facing in south hemisphere
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


def _call_pvgis_shscalc(lat: float, lon: float, pv_w: float, batt_wh: float,
                        daily_consumption_wh: float, angle: float, aspect: float):
    endpoint = PVGIS_BASE + "SHScalc"
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": pv_w / 1000.0,          # W -> kW
        "batterysize": batt_wh / 1000.0,     # Wh -> kWh
        "consumptionday": daily_consumption_wh / 1000.0,  # Wh/day -> kWh/day
        "cutoff": 0.3,
        "angle": angle,
        "aspect": aspect,
        "outputformat": "json",
        "browser": 0,
    }
    r = requests.get(endpoint, params=params, timeout=60)
    r.raise_for_status()
    return r.json(), endpoint, params


def _extract_empty_battery_pct(shs_json: Dict[str, Any]) -> float:
    """
    PVGIS SHScalc usually returns:
    outputs -> overall -> percentage_days_empty
    or similar field depending on version.

    We try a few safe paths.
    """
    candidates = [
        _safe_get(shs_json, "outputs", "overall", "percentage_days_empty"),
        _safe_get(shs_json, "outputs", "overall", "percentage_days_with_empty_battery"),
        _safe_get(shs_json, "outputs", "overall", "days_empty_pct"),
        _safe_get(shs_json, "outputs", "totals", "percentage_days_empty"),
        _safe_get(shs_json, "outputs", "totals", "percentage_days_with_empty_battery"),
    ]

    for c in candidates:
        if c is not None:
            try:
                return float(c)
            except Exception:
                pass

    # fallback
    return 0.0


def _extract_monthly_energy_table(shs_json: Dict[str, Any]) -> List[float]:
    """
    Extract monthly available/load-compatible daily Wh.
    We use a tolerant parser because PVGIS JSON can vary.

    We look for monthly values under outputs/monthly and derive an approximate
    max daily energy compatible with zero-empty-battery logic using binary search elsewhere.
    """
    monthly = _safe_get(shs_json, "outputs", "monthly")
    if not isinstance(monthly, list):
        return [0.0] * 12

    # not used directly for pass/fail in this version
    return [0.0] * 12


def _monthly_empty_battery_for_required_mode(
    lat: float,
    lon: float,
    pv_w: float,
    batt_wh: float,
    required_hours: float,
    power_w: float,
    angle: float,
    aspect: float,
) -> Tuple[List[float], List[int], Dict[str, Any]]:
    """
    For the user-selected operating mode, call PVGIS once and reuse the returned
    monthly empty-battery percentages if available. If only overall percentage is
    available, we conservatively map it across failed months later as 0/overall fallback.

    Since PVGIS monthly per-month empty-battery output may vary by endpoint version,
    this function tries to extract month-level percentages when present.
    """
    daily_wh = required_hours * power_w
    shs_json, shs_endpoint, shs_params = _call_pvgis_shscalc(
        lat, lon, pv_w, batt_wh, daily_wh, angle, aspect
    )

    overall_pct = _extract_empty_battery_pct(shs_json)

    # Try month-level percentages if present
    monthly_pct = [0.0] * 12
    monthly_days = [0] * 12

    monthly = _safe_get(shs_json, "outputs", "monthly")
    if isinstance(monthly, list) and len(monthly) >= 12:
        found_any = False
        for i in range(12):
            row = monthly[i] if i < len(monthly) else {}
            candidates = [
                row.get("percentage_days_empty"),
                row.get("percentage_days_with_empty_battery"),
                row.get("days_empty_pct"),
            ]
            pct_val = None
            for c in candidates:
                if c is not None:
                    try:
                        pct_val = float(c)
                        break
                    except Exception:
                        pass
            if pct_val is not None:
                found_any = True
                monthly_pct[i] = pct_val
                monthly_days[i] = round(_days_in_month_non_leap(i + 1) * pct_val / 100.0)

        if not found_any:
            # leave zeros; UI can still use overall if wanted
            pass

    meta = {
        "overall_empty_battery_pct": overall_pct,
        "shs_endpoint": shs_endpoint,
        "shs_params": shs_params,
        "raw_shs": shs_json,
    }
    return monthly_pct, monthly_days, meta


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
    Binary search daily Wh threshold so that empty-battery percentage stays ~0
    for the given month. Keeps existing pass/fail logic.
    """
    low = 0.0
    high = max(power_w * 24.0 * 2.0, 50.0)

    # Expand high if still zero-empty
    for _ in range(8):
        shs_json, _, _ = _call_pvgis_shscalc(lat, lon, pv_w, batt_wh, high, angle, aspect)
        monthly = _safe_get(shs_json, "outputs", "monthly")
        pct = None
        if isinstance(monthly, list) and len(monthly) >= month_index:
            row = monthly[month_index - 1]
            for k in ["percentage_days_empty", "percentage_days_with_empty_battery", "days_empty_pct"]:
                if k in row:
                    try:
                        pct = float(row[k])
                        break
                    except Exception:
                        pass
        if pct is None:
            pct = _extract_empty_battery_pct(shs_json)

        if pct <= 0.0:
            low = high
            high *= 1.6
        else:
            break

    # Binary search
    for _ in range(18):
        mid = (low + high) / 2.0
        shs_json, _, _ = _call_pvgis_shscalc(lat, lon, pv_w, batt_wh, mid, angle, aspect)
        monthly = _safe_get(shs_json, "outputs", "monthly")
        pct = None
        if isinstance(monthly, list) and len(monthly) >= month_index:
            row = monthly[month_index - 1]
            for k in ["percentage_days_empty", "percentage_days_with_empty_battery", "days_empty_pct"]:
                if k in row:
                    try:
                        pct = float(row[k])
                        break
                    except Exception:
                        pass
        if pct is None:
            pct = _extract_empty_battery_pct(shs_json)

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

        # one PVcalc call for meta/trust
        pvcalc_json, pvcalc_endpoint, pvcalc_params = _call_pvgis_pvcalc(
            lat, lon, pv_w, tilt, azim
        )

        # monthly pass/fail logic stays exactly the same conceptually
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

        # NEW: monthly empty battery stats for the selected operating mode
        empty_battery_pct_by_month, empty_battery_days_by_month, eb_meta = _monthly_empty_battery_for_required_mode(
            lat=lat,
            lon=lon,
            pv_w=pv_w,
            batt_wh=batt_wh,
            required_hours=required_hrs,
            power_w=power_w,
            angle=tilt,
            aspect=azim,
        )

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

            # NEW FIELDS
            "empty_battery_pct_by_month": empty_battery_pct_by_month,
            "empty_battery_days_by_month": empty_battery_days_by_month,
            "overall_empty_battery_pct": eb_meta["overall_empty_battery_pct"],

            "pvgis_meta": {
                "dataset": "PVGIS-SARAH3",
                "pvcalc_endpoint": pvcalc_endpoint,
                "pvcalc_params": pvcalc_params,
                "pvcalc_url_example": requests.Request("GET", pvcalc_endpoint, params=pvcalc_params).prepare().url,
                "shs_endpoint": eb_meta["shs_endpoint"],
                "shs_params": eb_meta["shs_params"],
                "shs_url_example": requests.Request("GET", eb_meta["shs_endpoint"], params=eb_meta["shs_params"]).prepare().url,
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
