
# core/simulate.py
# unified simulator: standard S4GA path + Avlite equivalent-panel path using same engine

import os
import time
import calendar
import math
from urllib.parse import urlencode

from core.devices import DEVICES, SOLAR_ENGINES
from core.avlite_fs import resolve_avlite_equivalent_config
from pvgis_client import pvcalc_monthly_wh_per_day, shs_monthly, load_cache, save_cache

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _days_in_month_non_leap(month_index_1_based: int) -> int:
    return calendar.monthrange(2025, month_index_1_based)[1]


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


def _infer_battery_basis(resolved):
    code = str(resolved.get("device_code", "")).upper()
    system_type = resolved.get("system_type")

    if system_type == "avlite_fixture":
        raw_type = str(resolved.get("battery_type", "Lead Acid")).upper()
        if "NIMH" in raw_type:
            return "NiMH", 20.0
        if "LIFEPO4" in raw_type or "LFP" in raw_type:
            return "LiFePO4", 20.0
        return "Lead Acid (SLA)" if "SLA" in raw_type else "Lead Acid", 30.0

    if "SP-301" in code:
        return "LiFePO4", 20.0

    return "Lead Acid", 30.0



def _extract_generation_wh_day_from_shs_monthly(monthly_rows):
    keys = ("E_d", "Ed", "E_day", "Eday", "Eload", "E_l", "E_gen")
    values = []
    for row in monthly_rows:
        value = None
        for key in keys:
            if key in row:
                value = row.get(key)
                break
        try:
            values.append(float(value))
        except Exception:
            values.append(0.0)
    return values


def _monthly_generation_used_in_simulation(lat, lon, resolved_cfg, tilt, azim, shs_monthly_rows=None):
    """
    Prefer the same SHScalc monthly result basis already used by the off-grid evaluation.
    Fall back to PVcalc only when SHScalc monthly rows do not expose daily energy.
    """
    if shs_monthly_rows:
        shs_values = _extract_generation_wh_day_from_shs_monthly(shs_monthly_rows)
        if any(v > 0 for v in shs_values):
            return shs_values

    try:
        values = pvcalc_monthly_wh_per_day(
            lat=lat,
            lon=lon,
            pv_wp=float(resolved_cfg["pv"]),
            tilt_deg=float(tilt),
            aspect_deg=float(azim),
        )
        if any(v > 0 for v in values):
            return values
    except Exception:
        pass

    return [0.0] * 12


def _estimate_daylight_hours_by_month(lat):
    """
    Simple astronomy approximation for mid-month daylight duration.
    Enough for explanatory rate display. Does not create a second simulation truth.
    """
    lat_rad = math.radians(float(lat))
    month_mid_days = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]
    out = []
    for n in month_mid_days:
        decl = math.radians(23.44) * math.sin(2 * math.pi * (284 + n) / 365.0)
        x = -math.tan(lat_rad) * math.tan(decl)
        x = max(-1.0, min(1.0, x))
        day_len = 24.0 * math.acos(x) / math.pi
        out.append(max(1.0, min(23.0, day_len)))
    return out


def _distribute_zero_days(days_in_month, zero_days):
    zero_days = max(0, min(int(zero_days), int(days_in_month)))
    if zero_days == 0:
        return set()
    if zero_days >= days_in_month:
        return set(range(days_in_month))
    # spread as evenly as possible, 0-indexed
    return {min(days_in_month - 1, round((i + 0.5) * days_in_month / zero_days - 1)) for i in range(zero_days)}


def _aggregate_weekly(series):
    out = []
    for i in range(0, len(series), 7):
        chunk = series[i:i + 7]
        if chunk:
            out.append(sum(chunk) / len(chunk))
    return out


def _aggregate_weekly_last(series):
    out = []
    for i in range(0, len(series), 7):
        chunk = series[i:i + 7]
        if chunk:
            out.append(chunk[-1])
    return out


def _expand_monthly_to_daily(values):
    daily = []
    for mi, value in enumerate(values, start=1):
        daily.extend([float(value)] * _days_in_month_non_leap(mi))
    return daily


def _weighted_average_monthly(values):
    total_days = sum(_days_in_month_non_leap(i + 1) for i in range(12))
    if total_days <= 0:
        return 0.0
    return sum(float(values[i]) * _days_in_month_non_leap(i + 1) for i in range(12)) / total_days


def _median(values):
    clean = sorted(float(v) for v in values)
    if not clean:
        return 0.0
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2.0


def _battery_behavior_metrics(
    monthly_gen_wh_day,
    batt_wh,
    cutoff_pct,
    power_w,
    required_hrs,
    monthly_empty_battery_days=None,
    lat=None,
):
    """
    Build a graph-friendly battery behavior layer that is constrained by the same
    monthly off-grid empty-battery result used in the feasibility engine.

    0% on the graph = usable reserve exhausted (operational cut-off reached).
    """
    usable_battery_wh = max(0.001, float(batt_wh) * (1.0 - float(cutoff_pct) / 100.0))
    discharge_day_wh = max(float(power_w), 0.0) * max(float(required_hrs), 0.0)
    discharge_pct_per_day = discharge_day_wh / usable_battery_wh * 100.0
    discharge_pct_per_hr = discharge_pct_per_day / max(float(required_hrs), 1e-6) if required_hrs else 0.0

    monthly_empty_battery_days = monthly_empty_battery_days or [0] * 12
    daylight_hours = _estimate_daylight_hours_by_month(lat if lat is not None else 0.0)

    charge_day_pct_by_month = []
    recharge_pct_per_hr_by_month = []
    monthly_reserve_avg = []
    monthly_reserve_end = []
    monthly_reserve_min = []
    monthly_reserve_median = []
    monthly_soc_preclip_min = []
    monthly_soc_preclip_median = []
    monthly_status = []

    reserve = 100.0
    daily_reserve = []
    daily_charge_pct = []
    daily_discharge_pct = []
    daily_charge_pct_per_hr = []
    daily_discharge_pct_per_hr = []
    daily_week_status = []
    daily_week_labels = []
    daily_reserve_start = []
    daily_reserve_end = []

    week_counter = 1

    for mi, gen_wh_day in enumerate(monthly_gen_wh_day, start=1):
        days = _days_in_month_non_leap(mi)
        charge_day_pct = max(float(gen_wh_day), 0.0) / usable_battery_wh * 100.0
        charge_day_pct_by_month.append(charge_day_pct)

        daylight = max(1.0, daylight_hours[mi - 1])
        recharge_pct_per_hr = charge_day_pct / daylight
        recharge_pct_per_hr_by_month.append(recharge_pct_per_hr)

        month_status = "green" if charge_day_pct >= discharge_pct_per_day else "red"
        monthly_status.append(month_status)

        zero_targets = _distribute_zero_days(days, monthly_empty_battery_days[mi - 1])

        reserve_values_month = []
        reserve_values_month_preclip = []
        for di in range(days):
            reserve_start = reserve

            if di in zero_targets:
                preclip_reserve = 0.0
                reserve = 0.0
            else:
                reserve = reserve + charge_day_pct - discharge_pct_per_day
                reserve = min(100.0, reserve)
                preclip_reserve = reserve
                # if source-of-truth says no empty days in this month, do not allow explanatory layer
                # to invent extra empties
                floor = 0.1 if int(monthly_empty_battery_days[mi - 1]) == 0 else 0.0
                reserve = max(floor, reserve)

            reserve_values_month.append(reserve)
            reserve_values_month_preclip.append(preclip_reserve)

            daily_reserve_start.append(reserve_start)
            daily_reserve_end.append(reserve)
            daily_reserve.append(reserve)
            daily_charge_pct.append(charge_day_pct)
            daily_discharge_pct.append(discharge_pct_per_day)
            daily_charge_pct_per_hr.append(recharge_pct_per_hr)
            daily_discharge_pct_per_hr.append(discharge_pct_per_hr)
            daily_week_status.append(month_status)
            daily_week_labels.append(week_counter)
            if len(daily_reserve) % 7 == 0:
                week_counter += 1

        monthly_reserve_avg.append(sum(reserve_values_month) / len(reserve_values_month) if reserve_values_month else reserve)
        monthly_reserve_end.append(reserve)
        monthly_reserve_min.append(min(reserve_values_month) if reserve_values_month else reserve)
        monthly_reserve_median.append(_median(reserve_values_month) if reserve_values_month else reserve)
        monthly_soc_preclip_min.append(min(reserve_values_month_preclip) if reserve_values_month_preclip else reserve)
        monthly_soc_preclip_median.append(_median(reserve_values_month_preclip) if reserve_values_month_preclip else reserve)

    weekly_labels = [f"W{i}" for i in range(1, len(_aggregate_weekly(daily_reserve)) + 1)]
    weekly_reserve_pct = _aggregate_weekly(daily_reserve)
    weekly_charge_pct = _aggregate_weekly(daily_charge_pct)
    weekly_discharge_pct = _aggregate_weekly(daily_discharge_pct)
    weekly_charge_pct_per_hr = _aggregate_weekly(daily_charge_pct_per_hr)
    weekly_discharge_pct_per_hr = _aggregate_weekly(daily_discharge_pct_per_hr)
    weekly_reserve_start = _aggregate_weekly(daily_reserve_start)
    weekly_reserve_end = _aggregate_weekly_last(daily_reserve_end)
    weekly_deficit_flags = [c < d for c, d in zip(weekly_charge_pct, weekly_discharge_pct)]

    avg_recharge_pct_per_hr = _weighted_average_monthly(recharge_pct_per_hr_by_month)
    avg_charge_day_pct = _weighted_average_monthly(charge_day_pct_by_month)

    return {
        "usable_battery_wh": usable_battery_wh,
        "discharge_pct_per_hr": discharge_pct_per_hr,
        "recharge_pct_per_hr_by_month": recharge_pct_per_hr_by_month,
        "avg_recharge_pct_per_hr": avg_recharge_pct_per_hr,
        "charge_day_pct_by_month": charge_day_pct_by_month,
        "avg_charge_day_pct": avg_charge_day_pct,
        "discharge_pct_per_day": discharge_pct_per_day,
        "monthly_soc_avg": monthly_reserve_avg,
        "monthly_soc_end": monthly_reserve_end,
        "monthly_soc_min": monthly_reserve_min,
        "monthly_soc_median": monthly_reserve_median,
        "monthly_soc_preclip_min": monthly_soc_preclip_min,
        "monthly_soc_preclip_median": monthly_soc_preclip_median,
        "monthly_status": monthly_status,

        "weekly_labels": weekly_labels,
        "weekly_reserve_pct": weekly_reserve_pct,
        "weekly_charge_pct": weekly_charge_pct,
        "weekly_discharge_pct": weekly_discharge_pct,
        "weekly_charge_pct_per_hr": weekly_charge_pct_per_hr,
        "weekly_discharge_pct_per_hr": weekly_discharge_pct_per_hr,
        "weekly_reserve_start_pct": weekly_reserve_start,
        "weekly_reserve_end_pct": weekly_reserve_end,
        "weekly_deficit_flags": weekly_deficit_flags,

        "lowest_usable_reserve_pct": min(daily_reserve) if daily_reserve else 100.0,
        "weeks_in_deficit": sum(1 for x in weekly_deficit_flags if x),
        "avg_daily_energy_in_wh": _weighted_average_monthly(monthly_gen_wh_day),
        "avg_daily_energy_out_wh": discharge_day_wh,
        "daylight_hours_by_month": daylight_hours,
    }


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


def max_wh_for_month_fast(lat, lon, pv_wp, batt_wh, tilt, aspect, mi, shs_eval_cache=None):
    hi_cap = float(min(20000, max(3 * batt_wh, 8 * pv_wp * 24)))
    shs_eval_cache = shs_eval_cache if shs_eval_cache is not None else {}

    def fe_for(cons_wh_day):
        if cons_wh_day <= 0:
            return 0.0

        cache_key = round(float(cons_wh_day), 6)
        monthly = shs_eval_cache.get(cache_key)
        if monthly is None:
            monthly = shs_monthly(
                lat, lon,
                pv_wp, batt_wh,
                float(cons_wh_day),
                tilt, aspect
            )
            shs_eval_cache[cache_key] = monthly
        return float(monthly[mi].get("f_e", 0.0))

    # Integer Wh/day steps are too coarse for ultra-low-power fixtures such as Avlite
    # markers, where 1 Wh/day can represent many operating hours. Use a float binary
    # search so the "max sustainable hours/day" metric stays aligned with the
    # empty-battery-day metric derived from the same SHScalc engine.
    lo, hi = 0.0, hi_cap
    best = 0.0

    for _ in range(22):
        mid = (lo + hi) / 2.0
        fe = fe_for(mid)

        if fe <= 0.0:
            best = mid
            lo = mid
        else:
            hi = mid

    return float(best)



def get_empty_battery_stats_for_required_mode(lat, lon, resolved, required_hrs, tilt, aspect):
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

    return monthly, pct_by_month, days_by_month, overall_pct


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

    work_items = []
    for did in selected_ids:
        try:
            did_int = int(str(did).split("||", 1)[0])
        except Exception:
            did_int = int(did)
        dspec = DEVICES[did_int]
        if dspec.get("system_type") == "avlite_fixture":
            resolved = resolve_avlite_equivalent_config(did, loc, per_device_config)
            work_items.append(("avlite", did, resolved))
        else:
            resolved = resolve_device_config(did, per_device_config)
            work_items.append(("standard", did, resolved))

    total_steps = max(1, len(work_items) * 12)
    completed_steps = 0
    started_at = time.time()

    for source_type, did, resolved in work_items:
        tilt_options = resolved["tilt_options"]
        tilt = tilt_options[0] if resolved["fixed"] else min(tilt_options, key=lambda x: abs(x - slope))

        if source_type == "avlite":
            azim = float(resolved.get("equivalent_aspect", 0.0))
        elif az_override is not None:
            azim = float(az_override)
        elif tilt in az_for_tilt:
            azim = az_for_tilt[tilt]
        else:
            azim = choose_azimuth_fixed_for_year(lat, lon, tilt, cache, key)
            az_for_tilt[tilt] = azim

        hours = []
        monthly_energy_wh = []
        shs_eval_cache = {}

        for mi in range(12):
            best_wh = max_wh_for_month_fast(
                lat=lat,
                lon=lon,
                pv_wp=resolved["pv"],
                batt_wh=resolved["batt"],
                tilt=tilt,
                aspect=azim,
                mi=mi,
                shs_eval_cache=shs_eval_cache,
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

        shs_monthly_rows, empty_battery_pct_by_month, empty_battery_days_by_month, overall_empty_battery_pct = get_empty_battery_stats_for_required_mode(
            lat=lat,
            lon=lon,
            resolved=resolved,
            required_hrs=required_hrs,
            tilt=tilt,
            aspect=azim
        )

        pvgis_meta = build_pvgis_meta(lat, lon, resolved, tilt, azim)
        if source_type == "avlite":
            pvgis_meta.update(resolved.get("avlite_meta", {}))

        battery_type, cutoff_pct = _infer_battery_basis(resolved)
        monthly_generation_wh_day = _monthly_generation_used_in_simulation(
            lat, lon, resolved, tilt, azim, shs_monthly_rows=shs_monthly_rows
        )
        behavior = _battery_behavior_metrics(
            monthly_gen_wh_day=monthly_generation_wh_day,
            batt_wh=resolved["batt"],
            cutoff_pct=cutoff_pct,
            power_w=resolved["power"],
            required_hrs=required_hrs,
            monthly_empty_battery_days=empty_battery_days_by_month,
            lat=lat,
        )
        effective_pv_used = float(resolved.get("equivalent_panel_wp", resolved["pv"]))
        faa_3sunhours_energy_wh = effective_pv_used * 3.0
        faa_8h_required_wh = max(float(resolved["power"]), 0.0) * 8.0
        faa_3sunhours_compliant = faa_3sunhours_energy_wh >= faa_8h_required_wh
        faa_8h_compliant = behavior["usable_battery_wh"] >= faa_8h_required_wh

        result_key = resolved['device_name']
        row = {
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

            "battery_type": battery_type,
            "cutoff_pct": cutoff_pct,
            "usable_battery_wh": behavior["usable_battery_wh"],
            "monthly_generation_wh_day": monthly_generation_wh_day,
            "discharge_pct_per_hr": behavior["discharge_pct_per_hr"],
            "recharge_pct_per_hr_by_month": behavior["recharge_pct_per_hr_by_month"],
            "avg_recharge_pct_per_hr": behavior["avg_recharge_pct_per_hr"],
            "discharge_pct_per_day": behavior["discharge_pct_per_day"],
            "charge_day_pct_by_month": behavior["charge_day_pct_by_month"],
            "avg_charge_day_pct": behavior["avg_charge_day_pct"],
            "avg_daily_energy_in_wh": behavior["avg_daily_energy_in_wh"],
            "avg_daily_energy_out_wh": behavior["avg_daily_energy_out_wh"],
            "soc_monthly_avg": behavior["monthly_soc_avg"],
            "soc_monthly_end": behavior["monthly_soc_end"],
            "soc_monthly_min": behavior["monthly_soc_min"],
            "soc_monthly_median": behavior["monthly_soc_median"],
            "soc_monthly_preclip_min": behavior["monthly_soc_preclip_min"],
            "soc_monthly_preclip_median": behavior["monthly_soc_preclip_median"],
            "charge_discharge_status_by_month": behavior["monthly_status"],
            "weekly_labels": behavior["weekly_labels"],
            "weekly_reserve_pct": behavior["weekly_reserve_pct"],
            "weekly_charge_pct": behavior["weekly_charge_pct"],
            "weekly_discharge_pct": behavior["weekly_discharge_pct"],
            "weekly_charge_pct_per_hr": behavior["weekly_charge_pct_per_hr"],
            "weekly_discharge_pct_per_hr": behavior["weekly_discharge_pct_per_hr"],
            "weekly_reserve_start_pct": behavior["weekly_reserve_start_pct"],
            "weekly_reserve_end_pct": behavior["weekly_reserve_end_pct"],
            "weekly_deficit_flags": behavior["weekly_deficit_flags"],
            "lowest_usable_reserve_pct": behavior["lowest_usable_reserve_pct"],
            "weeks_in_deficit": behavior["weeks_in_deficit"],
            "daylight_hours_by_month": behavior["daylight_hours_by_month"],

            "faa_reference": "FAA AC 150/5345-50B §3.4.2.2",
            "faa_3sunhours_energy_wh": faa_3sunhours_energy_wh,
            "faa_8h_required_wh": faa_8h_required_wh,
            "faa_3sunhours_compliant": faa_3sunhours_compliant,
            "faa_8h_compliant": faa_8h_compliant,
        }
        for k in ["panel_count", "panel_list", "total_nominal_wp", "equivalent_panel_wp",
                  "equivalent_panel_tilt", "equivalent_panel_aspect",
                  "equivalent_pct_of_physical_nominal", "physical_panel_geometry",
                  "certified_intensity", "source_note"]:
            if k in resolved:
                row[k] = resolved[k]
        results[result_key] = row

    worst_name, worst_gap = None, 1e9
    overall = "PASS"

    for name, r in results.items():
        gap = r["min_margin"]
        if gap < worst_gap:
            worst_gap, worst_name = gap, name
        if r["status"] == "FAIL":
            overall = "FAIL"

    return results, overall, worst_name, worst_gap, slope
