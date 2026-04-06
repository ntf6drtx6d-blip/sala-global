# core/avlite_fs.py
# FINAL STABLE VERSION (MRcalc + correct parsing + aspect)

import calendar
import time
from functools import lru_cache
import requests

from core.devices_avlite import AVLITE_FIXTURES, AVLITE_DEVICES

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

PVGIS_BASE = "https://re.jrc.ec.europa.eu/api/v5_3"
DEFAULT_PR = 0.86
HTTP_TIMEOUT = 45


def _days(m):
    return calendar.monthrange(2025, m)[1]


def resolve_avlite_config(device_id):
    d = AVLITE_DEVICES[int(device_id)]
    f = AVLITE_FIXTURES[d["fixture_key"]]

    return {
        "name": d["name"],
        "power": float(f["power_w_100"]),
        "batt": float(f["battery_wh_nominal"]),
        "cutoff": float(f["cutoff_pct"]),
        "panels": f["panels"],
    }


def _extract_monthly(data):
    rows = data["outputs"]["monthly"]

    by_month = {m: [] for m in range(1,13)}

    for r in rows:
        m = int(r["month"])
        v = float(r["H(i)_m"])
        by_month[m].append(v)

    return [sum(by_month[m])/len(by_month[m]) for m in range(1,13)]


@lru_cache(maxsize=512)
def _mrcalc(lat, lon, tilt, aspect):
    params = {
        "lat": lat,
        "lon": lon,
        "selectrad": 1,
        "angle": tilt,
        "aspect": aspect,
        "outputformat": "json"
    }

    r = requests.get(f"{PVGIS_BASE}/MRcalc", params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return _extract_monthly(r.json())


def _panel_gen(lat, lon, panel):
    irr = _mrcalc(lat, lon, panel["tilt"], panel["aspect"])
    wp = panel["wp"]
    return [x * wp * DEFAULT_PR for x in irr]


def _total_gen(lat, lon, panels):
    total = [0]*12
    for p in panels:
        g = _panel_gen(lat, lon, p)
        for i in range(12):
            total[i]+=g[i]
    return total


def _simulate(gen, power, hours, batt, cutoff):
    min_wh = batt*(cutoff/100)
    cur = batt

    out = []

    for m in range(12):
        days=_days(m+1)
        g=gen[m]
        need=power*hours

        total=0

        for _ in range(days):
            cur=min(batt,cur+g)
            avail=max(0,cur-min_wh)

            if avail>=need:
                cur-=need
                total+=hours
            else:
                total+=avail/power
                cur=min_wh

        out.append(total/days)

    return out

def simulate_avlite_for_devices(
    loc,
    required_hrs,
    selected_ids,
    per_device_config=None,
    progress_callback=None,
):
    per_device_config = per_device_config or {}
    lat, lon = loc["lat"], loc["lon"]

    results = {}
    overall = "PASS"
    worst = None
    worst_gap = 999

    total_steps = max(1, len(selected_ids) * 12)
    completed_steps = 0
    started_at = time.time()

    for did in selected_ids:
        cfg = resolve_avlite_config(did)

        # optional UI label override if present
        user_cfg = per_device_config.get(did) or per_device_config.get(str(did), {})
        display_name = user_cfg.get("display_label") or cfg["name"]

        gen = _total_gen(lat, lon, cfg["panels"])
        hours = _simulate(gen, cfg["power"], required_hrs, cfg["batt"], cfg["cutoff"])

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
                    display_name,
                    MONTHS[mi],
                )

        gap = min(h - required_hrs for h in hours)
        status = "PASS" if all(h >= required_hrs for h in hours) else "FAIL"

        if gap < worst_gap:
            worst_gap = gap
            worst = display_name

        if status == "FAIL":
            overall = "FAIL"

        results[display_name] = {
            "device_id": did,
            "name": display_name,
            "device_code": cfg.get("device_code", ""),
            "system_type": "avlite_fixture",
            "engine": "AVLITE",
            "engine_key": cfg.get("fixture_key", ""),
            "power": cfg["power"],
            "pv": sum(float(p["wp"]) for p in cfg["panels"]),
            "batt": cfg["batt"],
            "batt_std": cfg["batt"],
            "batt_nominal_wh": cfg["batt"],
            "batt_usable_wh": cfg["batt"] * (1 - cfg["cutoff"] / 100.0),
            "battery_type": cfg.get("battery_type", ""),
            "battery_mode": "Built-in",
            "cutoff_pct": cfg["cutoff"],
            "usable_battery_pct": 100.0 - cfg["cutoff"],
            "tilt": None,
            "azim": None,
            "panel_count": len(cfg["panels"]),
            "panel_geometry": cfg.get("panel_geometry", ""),
            "hours": hours,
            "status": status,
            "min_margin": gap,
            "fail_months": [MONTHS[i] for i, h in enumerate(hours) if h < required_hrs],
            "monthly_energy_wh": [h * cfg["power"] for h in hours],
            "empty_battery_pct_by_month": [0.0] * 12,
            "empty_battery_days_by_month": [0] * 12,
            "overall_empty_battery_pct": 0.0,
            "lowest_battery_pct_est": None,
            "days_above_60_pct_est": None,
            "days_below_40_pct_est": None,
            "reserve_distribution_est": {},
            "daily_end_soc_est": [],
            "end_soc_monthly_min": [],
            "days_above_60_pct_by_month": [],
            "days_below_40_pct_by_month": [],
            "certified_intensity": "100%",
            "source_note": "Calculated with PVGIS MRcalc per panel face.",
            "pvgis_meta": {},
        }

    return results, overall, worst
