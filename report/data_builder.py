from datetime import datetime

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def _to_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default

def _pick_worst_device(results):
    worst_key = None
    worst = None
    worst_gap = None
    for key, r in results.items():
        hours = r.get("hours") or []
        if not hours:
            continue
        weakest = min([float(x) for x in hours])
        if worst_gap is None or weakest < worst_gap:
            worst_gap = weakest
            worst_key = key
            worst = r
    return worst_key, (worst or {})

def _pick_strongest_month(device):
    hours = device.get("hours") or []
    if not hours:
        return "-", None
    idx = max(range(len(hours)), key=lambda i: float(hours[i]))
    return MONTHS[idx], float(hours[idx])

def _pick_weakest_month(device):
    hours = device.get("hours") or []
    if not hours:
        return "-", None
    idx = min(range(len(hours)), key=lambda i: float(hours[i]))
    return MONTHS[idx], float(hours[idx])

def _annual_empty_battery_stats(results):
    pcts = []
    for r in results.values():
        pct = _to_float(r.get("overall_empty_battery_pct"))
        if pct is not None:
            pcts.append(pct)
    if not pcts:
        return None, None
    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100.0)
    return worst_days, worst_pct

def build_report_data(
    loc,
    required_hours,
    results,
    overall,
    document_no="",
    revision_no=0,
    airport_label="",
    report_date="",
    prepared_by=None,
):
    airport_name = airport_label or loc.get("label", "Study point")
    coordinates = f"{float(loc.get('lat', 0)):.5f}, {float(loc.get('lon', 0)):.5f}"
    worst_name, worst_device = _pick_worst_device(results)
    weak_month, weak_hours = _pick_weakest_month(worst_device)
    strong_month, strong_hours = _pick_strongest_month(worst_device)
    worst_days, worst_pct = _annual_empty_battery_stats(results)

    gap = None if weak_hours is None else weak_hours - float(required_hours)
    fail = gap is None or gap < 0

    cover_statement = (
        f"The analysed solar AGL configuration does not meet the required operating profile of "
        f"{float(required_hours):.0f} hours/day throughout the year. "
        f"The weakest case falls short by {abs(gap):.1f} hours/day. "
        f"Additional PV, battery capacity or reduced load is recommended."
        if fail else
        f"The analysed solar AGL configuration meets the required operating profile of "
        f"{float(required_hours):.0f} hours/day throughout the year. "
        f"The weakest case remains above requirement by {gap:.1f} hours/day."
    )

    return {
        "report_id": document_no or f"SALA-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "date": report_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "airport_name": airport_name,
        "coordinates": coordinates,
        "required_operation": f"{float(required_hours):.0f} hrs/day",
        "prepared_by": prepared_by or "SALA user",
        "cover_verdict": "NOT TECHNICALLY FEASIBLE" if fail else "TECHNICALLY FEASIBLE",
        "cover_statement": cover_statement,
        "overall_result_label": "NOT TECHNICALLY FEASIBLE" if fail else "TECHNICALLY FEASIBLE",
        "overall_result_value": "FAIL" if fail else "PASS",
        "gap_vs_requirement": f"{abs(gap):.0f} hrs" if gap is not None else "-",
        "weakest_month_short": weak_month,
        "strongest_month_short": strong_month,
        "executive_summary": cover_statement,
        "accent": "red" if fail else "green",
        "base_tilt": _safe_or("-", worst_device.get("tilt")),
        "azimuth_mode": "Automatic",
        "annual_profile_chart_path": None,
        "monthly_chart_path": None,
        "map_image_path": None,
        "pvgis_meta": worst_device.get("pvgis_meta", {}),
    }

def _safe_or(default, value):
    return default if value in (None, "") else str(value)
