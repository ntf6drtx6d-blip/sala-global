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


def simulate_avlite_for_devices(loc, required_hrs, selected_ids):
    lat,lon=loc["lat"],loc["lon"]

    results={}
    overall="PASS"
    worst=None
    worst_gap=999

    for did in selected_ids:
        cfg=resolve_avlite_config(did)

        gen=_total_gen(lat,lon,cfg["panels"])

        hours=_simulate(gen,cfg["power"],required_hrs,cfg["batt"],cfg["cutoff"])

        gap=min(h-required_hrs for h in hours)
        status="PASS" if all(h>=required_hrs for h in hours) else "FAIL"

        if gap<worst_gap:
            worst_gap=gap
            worst=cfg["name"]

        if status=="FAIL":
            overall="FAIL"

        results[cfg["name"]]={
            "hours":hours,
            "status":status,
            "min_margin":gap
        }

    return results, overall, worst
