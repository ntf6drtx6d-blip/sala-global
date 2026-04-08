
# core/simulate.py
# unified simulator: standard S4GA path + Avlite equivalent-panel path using same engine

import os
import time
import calendar
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


def _monthly_generation_used_in_simulation(lat, lon, resolved_cfg, tilt, azim):
    try:
        return pvcalc_monthly_wh_per_day(
            lat=lat,
            lon=lon,
            pv_wp=float(resolved_cfg["pv"]),
            tilt_deg=float(tilt),
            aspect_deg=float(azim),
        )
    except Exception:
        return [0.0] * 12


def _battery_behavior_metrics(monthly_gen_wh_day, batt_wh, cutoff_pct, power_w, required_hrs):
    usable_battery_wh = max(0.001, float(batt_wh) * (1.0 - float(cutoff_pct) / 100.0))
    discharge_pct_per_hr = float(power_w) / usable_battery_wh * 100.0

    recharge_pct_per_hr_by_month = []
    monthly_soc_avg = []
    monthly_soc_end = []
    monthly_status = []

    weekly_labels = []
    weekly_soc = []
    weekly_recharge_pct_per_hr = []
    weekly_discharge_pct_per_hr = []
    weekly_status = []

    soc = 100.0
    cutoff_floor = float(cutoff_pct)

    for i, gen_wh_day in enumerate(monthly_gen_wh_day, start=1):
        recharge_pct_per_hr = float(gen_wh_day) / usable_battery_wh / 24.0 * 100.0
        recharge_pct_per_hr_by_month.append(recharge_pct_per_hr)

        net_pct_per_day = (recharge_pct_per_hr * 24.0) - (discharge_pct_per_hr * float(required_hrs))
        dim = _days_in_month_non_leap(i)
        soc_start = soc
        soc_end = soc + net_pct_per_day * dim
        soc_end = min(100.0, soc_end)
        soc_end = max(cutoff_floor, soc_end)

        monthly_soc_avg.append((soc_start + soc_end) / 2.0)
        monthly_soc_end.append(soc_end)
        month_state = 'green' if recharge_pct_per_hr >= discharge_pct_per_hr else 'red'
        monthly_status.append(month_state)

        # derive week-level trajectory from month-level balance using real week buckets from day counts
        days_remaining = dim
        month_start_soc = soc_start
        week_no = 1
        while days_remaining > 0:
            week_days = min(7, days_remaining)
            week_end_soc = month_start_soc + net_pct_per_day * week_days
            week_end_soc = min(100.0, week_end_soc)
            week_end_soc = max(cutoff_floor, week_end_soc)
            week_avg_soc = (month_start_soc + week_end_soc) / 2.0

            weekly_labels.append(f"{MONTHS[i-1]}-W{week_no}")
            weekly_soc.append(week_avg_soc)
            weekly_recharge_pct_per_hr.append(recharge_pct_per_hr)
            weekly_discharge_pct_per_hr.append(discharge_pct_per_hr)
            weekly_status.append(month_state)

            month_start_soc = week_end_soc
            days_remaining -= week_days
            week_no += 1

        soc = soc_end

    avg_recharge_pct_per_hr = sum(
        recharge_pct_per_hr_by_month[i] * _days_in_month_non_leap(i + 1) for i in range(12)
    ) / sum(_days_in_month_non_leap(i + 1) for i in range(12))

    lowest_soc_pct = min(weekly_soc) if weekly_soc else min(monthly_soc_avg) if monthly_soc_avg else 100.0
    weeks_in_deficit = sum(1 for s in weekly_status if s == 'red')

    return {
        'usable_battery_wh': usable_battery_wh,
        'discharge_pct_per_hr': discharge_pct_per_hr,
        'recharge_pct_per_hr_by_month': recharge_pct_per_hr_by_month,
        'avg_recharge_pct_per_hr': avg_recharge_pct_per_hr,
        'monthly_soc_avg': monthly_soc_avg,
        'monthly_soc_end': monthly_soc_end,
        'monthly_status': monthly_status,
        'weekly_labels': weekly_labels,
        'weekly_soc': weekly_soc,
        'weekly_recharge_pct_per_hr': weekly_recharge_pct_per_hr,
        'weekly_discharge_pct_per_hr': weekly_discharge_pct_per_hr,
        'weekly_status': weekly_status,
        'lowest_soc_pct': lowest_soc_pct,
        'weeks_in_deficit': weeks_in_deficit,
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

        empty_battery_pct_by_month, empty_battery_days_by_month, overall_empty_battery_pct = get_empty_battery_stats_for_required_mode(
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
        monthly_generation_wh_day = _monthly_generation_used_in_simulation(lat, lon, resolved, tilt, azim)
        if not monthly_generation_wh_day or max(monthly_generation_wh_day) <= 1e-9:
            # fallback: use sustainable monthly operating energy already solved by SHScalc path
            monthly_generation_wh_day = [float(x) for x in monthly_energy_wh]
        behavior = _battery_behavior_metrics(
            monthly_gen_wh_day=monthly_generation_wh_day,
            batt_wh=resolved["batt"],
            cutoff_pct=cutoff_pct,
            power_w=resolved["power"],
            required_hrs=required_hrs,
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
            "soc_monthly_avg": behavior["monthly_soc_avg"],
            "soc_monthly_end": behavior["monthly_soc_end"],
            "charge_discharge_status_by_month": behavior["monthly_status"],
            "weekly_labels": behavior["weekly_labels"],
            "weekly_soc": behavior["weekly_soc"],
            "weekly_recharge_pct_per_hr": behavior["weekly_recharge_pct_per_hr"],
            "weekly_discharge_pct_per_hr": behavior["weekly_discharge_pct_per_hr"],
            "charge_discharge_status_by_week": behavior["weekly_status"],
            "lowest_soc_pct": behavior["lowest_soc_pct"],
            "weeks_in_deficit": behavior["weeks_in_deficit"],

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
