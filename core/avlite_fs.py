# core/avlite_fs.py

import calendar
import time

from pvgis_client import pvcalc_monthly_wh_per_day
from core.devices_avlite import AVLITE_FIXTURES, AVLITE_DEVICES

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _days_in_month_non_leap(month_index_1_based: int) -> int:
    return calendar.monthrange(2025, month_index_1_based)[1]


def _parse_avlite_device_identifier(device_identifier, per_device_config=None):
    per_device_config = per_device_config or {}
    user_cfg = per_device_config.get(device_identifier) or per_device_config.get(str(device_identifier), {})
    raw_id = user_cfg.get("device_id", device_identifier)
    try:
        device_id = int(raw_id)
    except Exception:
        device_id = int(device_identifier)
    return device_id, user_cfg


def resolve_avlite_config(device_id, per_device_config=None):
    per_device_config = per_device_config or {}
    parsed_device_id, user_cfg = _parse_avlite_device_identifier(device_id, per_device_config)
    dspec = AVLITE_DEVICES[parsed_device_id]
    fixture = AVLITE_FIXTURES[dspec["fixture_key"]]

    display_name = user_cfg.get("display_label") or dspec["name"]

    return {
        "device_id": parsed_device_id,
        "device_code": dspec["code"],
        "device_name": display_name,
        "system_type": "avlite_fixture",
        "fixture_key": dspec["fixture_key"],
        "fixture_name": fixture["name"],
        "battery_type": fixture["battery_type"],
        "battery_voltage_v": float(fixture["battery_voltage_v"]),
        "battery_ah": float(fixture["battery_ah"]),
        "batt_nominal_wh": float(fixture["battery_wh_nominal"]),
        "cutoff_pct": float(fixture["cutoff_pct"]),
        "usable_battery_pct": float(fixture["usable_battery_pct"]),
        "batt_usable_wh": float(fixture["battery_wh_nominal"]) * (float(fixture["usable_battery_pct"]) / 100.0),
        "power": float(fixture["power_w_100"]),
        "pv": float(fixture["pv_total_wp"]),
        "panel_count": int(fixture["panel_count"]),
        "panel_geometry": fixture["panel_geometry"],
        "panels": fixture["panels"],
        "certified_intensity": fixture["certified_intensity"],
        "source_note": fixture.get("source_note", ""),
    }


def _sanitize_panel_geometry(panel):
    """
    PVGIS PVcalc can be unstable on exact edge geometry values such as:
    - tilt = 90
    - aspect = 180
    We soften them slightly.

    IMPORTANT:
    pvgis_client.py internally clamps PVcalc peakpower to minimum 0.05 kW (= 50 Wp).
    For small panels (e.g. 0.7W, 5W, 7W) we therefore:
    1) query PVGIS at 50Wp
    2) scale the result back to actual Wp
    This is valid because PVcalc energy scales linearly with peak power.
    """
    actual_wp = max(0.001, float(panel["wp"]))
    query_wp = max(actual_wp, 50.0)
    scale = actual_wp / query_wp

    tilt = float(panel["tilt"])
    if tilt >= 90.0:
        tilt = 89.0
    elif tilt < 0.0:
        tilt = 0.0

    aspect = float(panel["aspect"])
    if aspect >= 180.0:
        aspect = 179.0
    elif aspect <= -180.0:
        aspect = -179.0

    return {
        "actual_wp": actual_wp,
        "query_wp": query_wp,
        "scale": scale,
        "tilt": tilt,
        "aspect": aspect,
    }


def _single_panel_monthly_wh_day(lat, lon, panel):
    geom = _sanitize_panel_geometry(panel)

    monthly_query = pvcalc_monthly_wh_per_day(
        lat=float(lat),
        lon=float(lon),
        pv_wp=float(geom["query_wp"]),
        tilt_deg=float(geom["tilt"]),
        aspect_deg=float(geom["aspect"]),
    )

    monthly_actual = [float(x) * float(geom["scale"]) for x in monthly_query]
    return monthly_actual, geom


def _monthly_generation_wh_per_day(lat, lon, resolved_cfg):
    """
    Sum PVGIS monthly Wh/day over all physical panel faces.
    """
    per_panel_monthly = []
    total = [0.0] * 12

    for panel in resolved_cfg["panels"]:
        monthly, geom = _single_panel_monthly_wh_day(lat=lat, lon=lon, panel=panel)

        per_panel_monthly.append({
            "name": panel["name"],
            "wp_actual": float(geom["actual_wp"]),
            "wp_query": float(geom["query_wp"]),
            "scale_applied": float(geom["scale"]),
            "tilt": float(geom["tilt"]),
            "aspect": float(geom["aspect"]),
            "monthly_wh_day": monthly,
        })

        for i in range(12):
            total[i] += float(monthly[i])

    return total, per_panel_monthly


def _simulate_year_with_monthly_average_generation(monthly_gen_wh_day, power_w, required_hrs, batt_nominal_wh, cutoff_pct):
    required_hrs = float(required_hrs)
    power_w = max(float(power_w), 0.0001)
    batt_nominal_wh = float(batt_nominal_wh)
    cutoff_pct = float(cutoff_pct)

    batt_min_wh = batt_nominal_wh * (cutoff_pct / 100.0)
    batt_max_wh = batt_nominal_wh
    batt_wh = batt_max_wh

    hours_by_month = []
    energy_by_month = []
    empty_days_by_month = []
    empty_pct_by_month = []
    end_soc_monthly_min = []
    days_above_60_pct_by_month = []
    days_below_40_pct_by_month = []
    all_daily_end_soc = []

    total_days = 0
    total_empty_days = 0

    for mi in range(12):
        days = _days_in_month_non_leap(mi + 1)
        gen_day_wh = float(monthly_gen_wh_day[mi])
        demand_day_wh = required_hrs * power_w

        month_achieved_hours = 0.0
        month_empty_days = 0
        month_end_socs = []

        for _day in range(days):
            # simple daily bucket model:
            # daily PV generation charges the battery first
            batt_wh = min(batt_max_wh, batt_wh + gen_day_wh)

            available_wh = max(0.0, batt_wh - batt_min_wh)

            if available_wh >= demand_day_wh:
                achieved_hrs = required_hrs
                batt_wh -= demand_day_wh
            else:
                achieved_hrs = available_wh / power_w
                batt_wh = batt_min_wh
                month_empty_days += 1

            end_soc = 100.0 * batt_wh / batt_nominal_wh if batt_nominal_wh > 0 else 0.0

            month_achieved_hours += achieved_hrs
            month_end_socs.append(end_soc)
            all_daily_end_soc.append(end_soc)

        avg_achieved_hrs = month_achieved_hours / days if days else 0.0
        hours_by_month.append(avg_achieved_hrs)
        energy_by_month.append(avg_achieved_hrs * power_w)
        empty_days_by_month.append(month_empty_days)
        empty_pct_by_month.append((month_empty_days / days) * 100.0 if days else 0.0)
        end_soc_monthly_min.append(min(month_end_socs) if month_end_socs else 0.0)

        above_60 = sum(1 for x in month_end_socs if x >= 60.0)
        below_40 = sum(1 for x in month_end_socs if x < 40.0)

        days_above_60_pct_by_month.append((above_60 / days) * 100.0 if days else 0.0)
        days_below_40_pct_by_month.append((below_40 / days) * 100.0 if days else 0.0)

        total_days += days
        total_empty_days += month_empty_days

    overall_empty_battery_pct = (total_empty_days / total_days) * 100.0 if total_days else 0.0
    lowest_battery_pct = min(all_daily_end_soc) if all_daily_end_soc else 0.0

    above_60_total = sum(1 for x in all_daily_end_soc if x >= 60.0)
    below_40_total = sum(1 for x in all_daily_end_soc if x < 40.0)

    days_above_60_pct_total = (above_60_total / total_days) * 100.0 if total_days else 0.0
    days_below_40_pct_total = (below_40_total / total_days) * 100.0 if total_days else 0.0

    reserve_distribution_est = {
        "80_100": (sum(1 for x in all_daily_end_soc if x >= 80.0) / total_days) * 100.0 if total_days else 0.0,
        "60_80":  (sum(1 for x in all_daily_end_soc if 60.0 <= x < 80.0) / total_days) * 100.0 if total_days else 0.0,
        "40_60":  (sum(1 for x in all_daily_end_soc if 40.0 <= x < 60.0) / total_days) * 100.0 if total_days else 0.0,
        "30_40":  (sum(1 for x in all_daily_end_soc if 30.0 <= x < 40.0) / total_days) * 100.0 if total_days else 0.0,
        "below_30": (sum(1 for x in all_daily_end_soc if x < 30.0) / total_days) * 100.0 if total_days else 0.0,
    }

    return {
        "hours_by_month": hours_by_month,
        "monthly_energy_wh": energy_by_month,
        "empty_battery_days_by_month": empty_days_by_month,
        "empty_battery_pct_by_month": empty_pct_by_month,
        "overall_empty_battery_pct": overall_empty_battery_pct,
        "lowest_battery_pct_est": lowest_battery_pct,
        "days_above_60_pct_est": days_above_60_pct_total,
        "days_below_40_pct_est": days_below_40_pct_total,
        "reserve_distribution_est": reserve_distribution_est,
        "daily_end_soc_est": all_daily_end_soc,
        "end_soc_monthly_min": end_soc_monthly_min,
        "days_above_60_pct_by_month": days_above_60_pct_by_month,
        "days_below_40_pct_by_month": days_below_40_pct_by_month,
    }


def build_avlite_pvgis_meta(lat, lon, resolved_cfg, per_panel_monthly, total_monthly_wh_day):
    return {
        "dataset_note": (
            "Calculated with PVGIS PVcalc by summing all physical panel faces separately. "
            "Small panels below 50Wp are queried at 50Wp due to pvgis_client clamp and then scaled back."
        ),
        "lat": float(lat),
        "lon": float(lon),
        "device": resolved_cfg["fixture_name"],
        "certified_intensity": resolved_cfg["certified_intensity"],
        "power_w_100": resolved_cfg["power"],
        "battery_type": resolved_cfg["battery_type"],
        "battery_nominal_wh": resolved_cfg["batt_nominal_wh"],
        "battery_usable_wh": resolved_cfg["batt_usable_wh"],
        "cutoff_pct": resolved_cfg["cutoff_pct"],
        "panel_count": resolved_cfg["panel_count"],
        "panel_geometry": resolved_cfg["panel_geometry"],
        "panels": per_panel_monthly,
        "monthly_total_wh_day": total_monthly_wh_day,
        "explanation": (
            "This Avlite engine does not use one synthetic single-plane panel. "
            "It runs PVGIS panel-by-panel and sums all faces."
        ),
    }


def simulate_avlite_for_devices(loc, required_hrs, selected_ids, per_device_config=None, progress_callback=None):
    per_device_config = per_device_config or {}
    lat, lon = float(loc["lat"]), float(loc["lon"])
    results = {}

    total_steps = max(1, len(selected_ids) * 12)
    completed_steps = 0
    started_at = time.time()

    for did in selected_ids:
        resolved = resolve_avlite_config(did, per_device_config)

        monthly_gen_wh_day, per_panel_monthly = _monthly_generation_wh_per_day(
            lat=lat,
            lon=lon,
            resolved_cfg=resolved
        )

        sim = _simulate_year_with_monthly_average_generation(
            monthly_gen_wh_day=monthly_gen_wh_day,
            power_w=resolved["power"],
            required_hrs=required_hrs,
            batt_nominal_wh=resolved["batt_nominal_wh"],
            cutoff_pct=resolved["cutoff_pct"],
        )

        for mi in range(12):
            completed_steps += 1
            if progress_callback:
                elapsed = time.time() - started_at
                pct = completed_steps / total_steps
                eta = (elapsed / completed_steps) * (total_steps - completed_steps) if completed_steps else 0.0
                progress_callback(
                    completed_steps,
                    total_steps,
                    pct,
                    elapsed,
                    eta,
                    resolved["device_name"],
                    MONTHS[mi],
                )

        hours = sim["hours_by_month"]
        min_margin = min(h - float(required_hrs) for h in hours)
        status = "PASS" if all(h >= float(required_hrs) - 1e-6 for h in hours) else "FAIL"
        fail_months = [MONTHS[i] for i, h in enumerate(hours) if h + 1e-6 < float(required_hrs)]

        pvgis_meta = build_avlite_pvgis_meta(
            lat=lat,
            lon=lon,
            resolved_cfg=resolved,
            per_panel_monthly=per_panel_monthly,
            total_monthly_wh_day=monthly_gen_wh_day,
        )

        result_key = resolved["device_name"]

        results[result_key] = {
            "device_id": did,
            "device_code": resolved["device_code"],
            "name": resolved["device_name"],
            "system_type": "avlite_fixture",
            "engine": "AVLITE",
            "engine_key": resolved["fixture_key"],

            "power": resolved["power"],
            "pv": resolved["pv"],
            "batt": resolved["batt_nominal_wh"],
            "batt_std": resolved["batt_nominal_wh"],
            "batt_nominal_wh": resolved["batt_nominal_wh"],
            "batt_usable_wh": resolved["batt_usable_wh"],
            "battery_type": resolved["battery_type"],
            "battery_mode": "Built-in",
            "cutoff_pct": resolved["cutoff_pct"],
            "usable_battery_pct": resolved["usable_battery_pct"],

            "tilt": None,
            "azim": None,
            "panel_count": resolved["panel_count"],
            "panel_geometry": resolved["panel_geometry"],

            "hours": hours,
            "status": status,
            "min_margin": min_margin,
            "fail_months": fail_months,
            "monthly_energy_wh": sim["monthly_energy_wh"],
            "empty_battery_pct_by_month": sim["empty_battery_pct_by_month"],
            "empty_battery_days_by_month": sim["empty_battery_days_by_month"],
            "overall_empty_battery_pct": sim["overall_empty_battery_pct"],

            "lowest_battery_pct_est": sim["lowest_battery_pct_est"],
            "days_above_60_pct_est": sim["days_above_60_pct_est"],
            "days_below_40_pct_est": sim["days_below_40_pct_est"],
            "reserve_distribution_est": sim["reserve_distribution_est"],
            "daily_end_soc_est": sim["daily_end_soc_est"],
            "end_soc_monthly_min": sim["end_soc_monthly_min"],
            "days_above_60_pct_by_month": sim["days_above_60_pct_by_month"],
            "days_below_40_pct_by_month": sim["days_below_40_pct_by_month"],

            "certified_intensity": resolved["certified_intensity"],
            "source_note": resolved["source_note"],
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

    return results, overall, worst_name
