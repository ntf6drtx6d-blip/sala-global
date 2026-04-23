import math

from core.simulate import get_empty_battery_stats_for_required_mode, max_wh_for_month_fast


BORDERLINE_MARGIN_HOURS = 0.5
MAX_DESIGN_SCALE = 64.0
PANEL_SEARCH_STEPS = 14
BATTERY_SEARCH_STEPS = 14
PANEL_OUTPUT_STEP = 0.1
BATTERY_OUTPUT_STEP = 1.0


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _panel_count(result_row: dict) -> int:
    try:
        if str(result_row.get("system_type", "")).lower() != "avlite_fixture":
            return 1
        panel_list = result_row.get("panel_list", []) or []
        if panel_list:
            return len(panel_list)
        return int(result_row.get("panel_count", 0) or 0)
    except Exception:
        return 0


def needs_energy_design_analysis(result_row: dict) -> bool:
    blackout_days = sum(float(x or 0.0) for x in (result_row.get("empty_battery_days_by_month") or []))
    min_margin = _safe_float(result_row.get("min_margin"), 0.0)
    status = str(result_row.get("status", "")).upper()
    if blackout_days > 0:
        return True
    if status != "PASS":
        return True
    return min_margin < BORDERLINE_MARGIN_HOURS


def _design_base_from_result(result_row: dict) -> dict:
    use_equivalent_orientation = _panel_count(result_row) > 1 and result_row.get("equivalent_panel_aspect") is not None
    return {
        "pv_wp": max(_safe_float(result_row.get("equivalent_panel_wp", result_row.get("pv")), 0.0), 0.1),
        "batt_wh": max(_safe_float(result_row.get("batt"), 0.0), 1.0),
        "power_w": max(_safe_float(result_row.get("power"), 0.0), 0.001),
        "standby_power_w": max(_safe_float(result_row.get("standby_power_w"), 0.0), 0.0),
        "cutoff_pct": _safe_float(result_row.get("cutoff_pct"), 30.0),
        "tilt_deg": _safe_float(
            result_row.get("equivalent_panel_tilt" if use_equivalent_orientation else "tilt"),
            _safe_float(result_row.get("tilt"), 33.0),
        ),
        "aspect_deg": _safe_float(
            result_row.get("equivalent_panel_aspect" if use_equivalent_orientation else "azim"),
            _safe_float(result_row.get("azim"), 0.0),
        ),
    }


def _evaluate_design(base: dict, lat: float, lon: float, required_hrs: float, pv_wp: float, batt_wh: float) -> dict:
    resolved = {
        "pv": float(pv_wp),
        "batt": float(batt_wh),
        "power": float(base["power_w"]),
        "standby_power_w": float(base["standby_power_w"]),
    }
    shs_eval_cache = {}
    monthly_energy_wh = []
    hours = []

    for mi in range(12):
        best_wh = max_wh_for_month_fast(
            lat=lat,
            lon=lon,
            pv_wp=float(pv_wp),
            batt_wh=float(batt_wh),
            tilt=float(base["tilt_deg"]),
            aspect=float(base["aspect_deg"]),
            mi=mi,
            shs_eval_cache=shs_eval_cache,
            cutoff_pct=float(base["cutoff_pct"]),
        )
        monthly_energy_wh.append(best_wh)
        standby_day_wh = float(base["standby_power_w"]) * 24.0
        active_budget_wh = max(float(best_wh) - standby_day_wh, 0.0)
        hours.append(min(active_budget_wh / float(base["power_w"]), 24.0))

    _, _, empty_days_by_month, overall_empty_pct = get_empty_battery_stats_for_required_mode(
        lat=lat,
        lon=lon,
        resolved=resolved,
        required_hrs=float(required_hrs),
        tilt=float(base["tilt_deg"]),
        aspect=float(base["aspect_deg"]),
        shs_eval_cache=shs_eval_cache,
        cutoff_pct=float(base["cutoff_pct"]),
    )

    annual_blackout_days = sum(float(x or 0.0) for x in empty_days_by_month)
    min_margin = min(float(h) - float(required_hrs) for h in hours) if hours else -float(required_hrs)
    passes = annual_blackout_days <= 1e-6 and min_margin >= -1e-6

    return {
        "passes": passes,
        "annual_blackout_days": annual_blackout_days,
        "overall_empty_pct": float(overall_empty_pct or 0.0),
        "min_margin": min_margin,
        "hours": hours,
        "monthly_energy_wh": monthly_energy_wh,
    }


def _find_min_value(base: dict, lat: float, lon: float, required_hrs: float, current_pv: float, current_batt: float, variable: str):
    if variable == "pv":
        def evaluate(candidate):
            return _evaluate_design(base, lat, lon, required_hrs, candidate, current_batt)
        current_value = current_pv
        step = PANEL_OUTPUT_STEP
    else:
        def evaluate(candidate):
            return _evaluate_design(base, lat, lon, required_hrs, current_pv, candidate)
        current_value = current_batt
        step = BATTERY_OUTPUT_STEP

    baseline = evaluate(current_value)
    if baseline["passes"]:
        return current_value, baseline

    hi = current_value
    hi_eval = baseline
    limit = max(current_value * MAX_DESIGN_SCALE, current_value + step)
    while hi < limit and not hi_eval["passes"]:
        hi *= 2.0
        hi_eval = evaluate(hi)

    if not hi_eval["passes"]:
        return None, hi_eval

    lo = current_value
    for _ in range(PANEL_SEARCH_STEPS if variable == "pv" else BATTERY_SEARCH_STEPS):
        mid = (lo + hi) / 2.0
        mid_eval = evaluate(mid)
        if mid_eval["passes"]:
            hi = mid
            hi_eval = mid_eval
        else:
            lo = mid

    rounded = math.ceil(hi / step) * step
    rounded_eval = evaluate(rounded)
    if rounded_eval["passes"]:
        return rounded, rounded_eval

    fallback = math.ceil((rounded + step) / step) * step
    return fallback, evaluate(fallback)


def analyze_device_energy_design(result_row: dict, lat: float, lon: float, required_hrs: float) -> dict | None:
    if not needs_energy_design_analysis(result_row):
        return None

    base = _design_base_from_result(result_row)
    current_eval = _evaluate_design(base, lat, lon, required_hrs, base["pv_wp"], base["batt_wh"])

    panel = base["pv_wp"]
    battery = base["batt_wh"]
    final_eval = current_eval

    for _ in range(4):
        panel_candidate, panel_eval = _find_min_value(base, lat, lon, required_hrs, panel, battery, "pv")
        if panel_candidate is None:
            break
        battery_candidate, battery_eval = _find_min_value(base, lat, lon, required_hrs, panel_candidate, battery, "battery")
        if battery_candidate is None:
            panel = panel_candidate
            final_eval = panel_eval
            break

        stable = abs(panel_candidate - panel) < PANEL_OUTPUT_STEP and abs(battery_candidate - battery) < BATTERY_OUTPUT_STEP
        panel = panel_candidate
        battery = battery_candidate
        final_eval = battery_eval
        if stable:
            break

    solar_plus_eval = _evaluate_design(base, lat, lon, required_hrs, base["pv_wp"] * 2.0, base["batt_wh"])
    battery_plus_eval = _evaluate_design(base, lat, lon, required_hrs, base["pv_wp"], base["batt_wh"] * 2.0)

    return {
        "current_panel_wp": base["pv_wp"],
        "current_battery_wh": base["batt_wh"],
        "required_panel_wp": panel,
        "required_battery_wh": battery,
        "required_design_passes": bool(final_eval.get("passes")),
        "required_design_blackout_days": float(final_eval.get("annual_blackout_days", 0.0) or 0.0),
        "required_design_min_margin": float(final_eval.get("min_margin", 0.0) or 0.0),
        "battery_plus_passes": bool(battery_plus_eval.get("passes")),
        "battery_plus_blackout_days": float(battery_plus_eval.get("annual_blackout_days", 0.0) or 0.0),
        "solar_plus_passes": bool(solar_plus_eval.get("passes")),
        "solar_plus_blackout_days": float(solar_plus_eval.get("annual_blackout_days", 0.0) or 0.0),
        "consumption_locked": True,
        "is_borderline": current_eval["annual_blackout_days"] <= 1e-6 and float(result_row.get("min_margin", 0.0) or 0.0) < BORDERLINE_MARGIN_HOURS,
    }
