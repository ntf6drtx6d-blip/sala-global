# simulate.py
import time
from devices import resolve_device_configuration
from pvgis_client import pvcalc_monthly_wh_per_day, shs_monthly, load_cache, save_cache

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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


def simulate_for_devices(
    loc,
    required_hrs,
    selected_ids,
    selected_engine_by_device=None,
    battery_mode_by_device=None,
    power_override=None,
    az_override=None,
    progress_callback=None,
):
    selected_engine_by_device = selected_engine_by_device or {}
    battery_mode_by_device = battery_mode_by_device or {}
    power_override = power_override or {}

    lat, lon = loc["lat"], loc["lon"]
    cache = load_cache()
    key = f"{round(lat, 5)},{round(lon, 5)}"
    slope, _ = get_optimal_angles(lat, lon, cache, key)
    if slope is None:
        slope = lat_based_tilt(lat)

    results = {}
    az_for_tilt = {}

    total_steps = max(1, len(selected_ids) * 12)
    completed_steps = 0
    started_at = time.time()

    for did in selected_ids:
        resolved = resolve_device_configuration(
            device_id=did,
            selected_engine_code=selected_engine_by_device.get(did),
            battery_mode=battery_mode_by_device.get(did, "Std"),
            power_override=power_override.get(did),
        )

        name = resolved["name"]
        pv = resolved["pv"]
        power = resolved["power"]
        batt = resolved["batt"]
        engine_name = resolved["engine_name"]

        if resolved["fixed"]:
            tilt = int(round(resolved["tilt"]))
        else:
            possible = resolved.get("tiltset", [15, 35, 55])
            tilt = min(possible, key=lambda x: abs(x - slope))

        if az_override is not None:
            azim = float(az_override)
        elif tilt in az_for_tilt:
            azim = az_for_tilt[tilt]
        else:
            azim = choose_azimuth_fixed_for_year(lat, lon, tilt, cache, key)
            az_for_tilt[tilt] = azim

        hours = []
        monthly_best_wh = []

        for mi in range(12):
            best_wh = max_wh_for_month_fast(lat, lon, pv, batt, tilt, azim, mi)
            monthly_best_wh.append(best_wh)
            hours.append(min(best_wh / max(power, 0.05), 24.0))

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
                    name,
                    MONTHS[mi]
                )

        min_margin = min(h - required_hrs for h in hours)
        status = "PASS" if all(h >= required_hrs - 1e-6 for h in hours) else "FAIL"
        fail_months = [MONTHS[i] for i, h in enumerate(hours) if h + 1e-6 < required_hrs]

        results[name] = {
            "device_id": did,
            "system_type": resolved["system_type"],
            "engine": engine_name,
            "engine_code": resolved["engine_code"],
            "config_label": resolved["config_label"],
            "pv": pv,
            "batt": batt,
            "batt_mode": resolved["batt_mode"],
            "tilt": tilt,
            "azim": float(azim),
            "hours": hours,
            "monthly_best_wh": monthly_best_wh,
            "status": status,
            "min_margin": min_margin,
            "fail_months": fail_months,
            "power": power,
            "default_power": resolved["default_power"],
            "pvgis_inputs": {
                "lat": float(lat),
                "lon": float(lon),
                "peakpower": float(pv),
                "batterysize": float(batt),
                "consumptionday_examples": monthly_best_wh,
                "angle": float(tilt),
                "aspect": float(azim),
            },
        }

    worst_name, worst_gap = None, +1e9
    overall = "PASS"
    for name, r in results.items():
        gap = r["min_margin"]
        if gap < worst_gap:
            worst_gap, worst_name = gap, name
        if r["status"] == "FAIL":
            overall = "FAIL"

    return results, overall, worst_name, worst_gap, slope