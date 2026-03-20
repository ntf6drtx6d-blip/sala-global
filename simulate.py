# simulate.py
import math
from tqdm import tqdm
from pvgis_client import pvcalc_monthly_wh_per_day, shs_monthly, load_cache, save_cache

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def lat_based_tilt(lat):
    s = abs(float(lat))
    return max(5.0, min(55.0, s))

def _as_float(x):
    if x is None:
        return None
    if isinstance(x, dict):
        x = x.get("value")
    try:
        return float(x)
    except Exception:
        return None

def get_optimal_angles(lat, lon, cache, key):
    # не критично, але збережемо як було (можна спростити/видалити)
    slope = lat_based_tilt(lat)
    az = 0.0
    cache.setdefault(key, {})["angles"] = {"slope": slope, "azimuth": az}
    save_cache(cache)
    return slope, az

def choose_azimuth_fixed_for_year(lat, lon, tilt_deg, cache, key):
    # для стабільності: північна півкуля → 0° (південь), південна → 180°
    return 0.0 if float(lat) >= 0 else 180.0

def _pvcalc_fallback_wh_day(lat, lon, pv_wp, tilt, aspect, mi):
    wh = pvcalc_monthly_wh_per_day(lat, lon, pv_wp, tilt, aspect)
    return max(0.0, float(wh[mi]))

def max_wh_for_month_fast(lat, lon, pv_wp, batt_wh, tilt, aspect, mi, device_w):
    """
    Знаходить максимальне добове споживання (Wh/day), яке система витримує в місяці `mi`
    без 'empty battery days' за SHScalc (тобто f_e == 0).

    Потім години для графіка/таблиці: hours = min(best_wh / device_w, 24.0).
    Для стабільності робимо класичний бінарний пошук з точністю 1 Wh.
    Ніяких "степів" чи евристик, ніяких тихих фолбеків усередині пошуку.
    """

    # Верхня межа пошуку (достатня навіть для слабких зимових місяців; підняв запас)
    hi_cap = int(min(20000, max(3 * batt_wh, 8 * pv_wp * 24)))

    def fe_for(cons_wh_day):
        # 🔒 PVGIS SHScalc падає на consumptionday=0.0 (400 BAD REQUEST)
        if cons_wh_day <= 0:
            return 0.0  # не викликаємо PVGIS з consumptionday=0

        monthly = shs_monthly(
            lat, lon,
            pv_wp, batt_wh,
            float(cons_wh_day),
            tilt, aspect
        )
        return float(monthly[mi].get("f_e", 0.0))

    # ⚠️ Стартуємо з 1, щоб ніколи не тестувати 0 Wh/day у PVGIS
    lo, hi = 1, hi_cap
    best = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        # Якщо SHS тимчасово недоступний (rate limit), нехай виняток підніметься нагору:
        # головне — НЕ підміняти тут значенням 1.0 або 0.0, щоб не зламати пошук.
        fe = fe_for(mid)

        if fe <= 0.0:
            # Це значення система тягне без empty days → пробуємо збільшити
            best = mid
            lo = mid + 1
        else:
            # Забагато — зменшуємо
            hi = mid - 1

    # Діагностика (вмикається, якщо виставиш S4GA_DIAG=1 у .command)
    import os
    if os.getenv("S4GA_DIAG") == "1" and mi == 0:
        try:
            print(f"[DIAG] Jan: best_wh={best} Wh/day -> hours@{device_w}W={best/max(device_w,1e-9):.2f}")
        except Exception:
            pass

    return int(best)

def simulate_for_devices(loc, required_hrs, selected_ids, batt_mode_by_engine=None, power_override=None, az_override=None):
    batt_mode_by_engine = batt_mode_by_engine or {}
    power_override = power_override or {}

    lat, lon = loc["lat"], loc["lon"]
    cache = load_cache()
    key = f"{round(lat,5)},{round(lon,5)}"
    slope, _ = get_optimal_angles(lat, lon, cache, key)
    if slope is None:
        slope = lat_based_tilt(lat)

    results = {}
    az_for_tilt = {}

    total_steps = len(selected_ids) * 12
    pbar = tqdm(total=total_steps, desc="Simulation", unit="month", dynamic_ncols=True, leave=True)

    from devices import DEVICES  # локальний імпорт щоб уникати циклів

    for did in selected_ids:
        dspec = DEVICES[did]
        name = dspec["name"]
        pv = dspec["pv"]
        power = power_override.get(did, dspec["power"])
        batt = dspec["batt"]

        if "batt_ext" in dspec and batt_mode_by_engine.get(dspec["engine"], "Std") == "Ext":
            batt = dspec["batt_ext"]

        tilt = int(round(dspec["tilt"])) if dspec.get("fixed") else min([15, 35, 55], key=lambda x: abs(x - slope))

        if az_override is not None:
            azim = float(az_override)
        elif tilt in az_for_tilt:
            azim = az_for_tilt[tilt]
        else:
            azim = choose_azimuth_fixed_for_year(lat, lon, tilt, cache, key)
            az_for_tilt[tilt] = azim

        hours = []
        for mi in range(12):
            best_wh = max_wh_for_month_fast(lat, lon, pv, batt, tilt, azim, mi, device_w=power)
            hours.append(min(best_wh / max(power, 0.05), 24.0))
            pbar.update(1)

        min_margin = min(h - required_hrs for h in hours)
        status = "PASS" if all(h >= required_hrs - 1e-6 for h in hours) else "FAIL"
        fail_months = [MONTHS[i] for i, h in enumerate(hours) if h + 1e-6 < required_hrs]

        results[name] = {
            "engine": dspec["engine"], "pv": pv, "batt": batt,
            "tilt": tilt, "azim": float(azim),
            "hours": hours, "status": status,
            "min_margin": min_margin, "fail_months": fail_months,
            "power": power,
        }

    pbar.close()

    worst_name, worst_gap = None, +1e9
    overall = "PASS"
    for name, r in results.items():
        gap = r["min_margin"]
        if gap < worst_gap:
            worst_gap, worst_name = gap, name
        if r["status"] == "FAIL":
            overall = "FAIL"

    return results, overall, worst_name, worst_gap, slope
