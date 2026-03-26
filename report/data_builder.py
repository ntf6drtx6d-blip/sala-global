from datetime import datetime


def _to_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _annual_empty_battery_stats(results: dict):
    pcts = []
    for _, r in results.items():
        pct = _to_float(r.get("overall_empty_battery_pct"))
        if pct is not None:
            pcts.append(pct)

    if not pcts:
        return None, None

    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100.0)
    return worst_days, worst_pct


def _pick_worst_device(results: dict):
    worst = None
    worst_pct = -1

    for r in results.values():
        pct = _to_float(r.get("overall_empty_battery_pct"), -1)
        if pct > worst_pct:
            worst_pct = pct
            worst = r

    return worst or {}


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

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    worst_device = _pick_worst_device(results)

    hours = worst_device.get("hours", [])
    lowest_hours = min(hours) if hours else None

    return {
        "report_id": document_no or f"SALA-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "revision": "Rev 01",
        "date": report_date or datetime.now().strftime("%Y-%m-%d"),
        "airport_name": airport_name,
        "coordinates": f"{loc.get('lat')}, {loc.get('lon')}",
        "required_operation": f"{required_hours} hrs/day",
        "worst_blackout_risk": f"{worst_days} days/year",
        "worst_blackout_pct": f"{worst_pct:.1f}%",
        "prepared_by": prepared_by or "SALA user",
        "prepared_under": "SALA Methodology",
        "methodology_note": "Based on PVGIS (JRC, European Commission)",

        "device_name": worst_device.get("name", "-"),
        "achievable_worst_month": f"{lowest_hours:.1f} hrs/day" if lowest_hours else "-",
        "battery_reserve": "-",  # simple for now

        "map_image_path": None,
        "monthly_chart_path": None,
        "annual_profile_chart_path": None,

        "accent": "green" if worst_days == 0 else "red",
    }
