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
        pct = r.get("overall_empty_battery_pct")
        pct = _to_float(pct)
        if pct is not None:
            pcts.append(pct)

    if not pcts:
        return None, None

    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100.0)
    return worst_days, worst_pct

def _count_device_statuses(results: dict):
    total = len(results)
    passed = 0
    for _, r in results.items():
        if r.get("status") == "PASS":
            passed += 1
    failed = total - passed
    return total, passed, failed

def _overall_state(results: dict):
    total, passed, failed = _count_device_statuses(results)
    if total == 0:
        return "unknown"
    if passed == total:
        return "all_pass"
    if failed == total:
        return "none_pass"
    return "mixed"

def _pick_worst_device(results: dict):
    worst_key = None
    worst_result = None
    worst_pct = -1.0

    for key, r in results.items():
        pct = _to_float(r.get("overall_empty_battery_pct"), default=-1.0)
        if pct > worst_pct:
            worst_pct = pct
            worst_key = key
            worst_result = r

    if worst_result is not None:
        return worst_key, worst_result

    for key, r in results.items():
        return key, r

    return None, {}

def _format_duration_hours(value):
    val = _to_float(value)
    if val is None:
        return "-"
    total_minutes = round(val * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes:02d}m"

def _format_hours_per_day(value):
    val = _to_float(value)
    if val is None:
        return "-"
    if float(val).is_integer():
        return f"{int(val)} hrs/day"
    return f"{val:.1f} hrs/day"

def build_report_data(
    loc,
    required_hours,
    results,
    overall,
    document_no="",
    revision_no=0,
    airport_label="",
    report_date="",
):
    airport_name = airport_label or loc.get("label", "Study point")
    country = loc.get("country", "") or "-"
    coordinates = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    state = _overall_state(results)
    _, worst_device = _pick_worst_device(results)

    if state == "all_pass":
        conclusion_title = "System meets the required operating profile."
        conclusion_text = "The system supports operation year-round."
        interpretation = "The selected configuration remains above the required operating profile throughout the annual cycle."
        recommendation = "Proceed with deployment."
        accent = "green"
    elif state == "mixed":
        conclusion_title = "System partially meets the required operating profile."
        conclusion_text = "At least one selected device remains below requirement."
        interpretation = "The selected configuration is not fully compliant under worst-case solar conditions."
        recommendation = "Review the non-compliant configuration."
        accent = "blue"
    else:
        conclusion_title = "System does not meet the required operating profile."
        conclusion_text = "The system does not support operation year-round."
        interpretation = "The selected configuration falls below the required operating profile and shows blackout exposure."
        recommendation = "System redesign is required."
        accent = "red"

    return {
        "report_id": document_no or "SALA-SFS-2026-000134",
        "revision": f"Rev {int(revision_no):02d}" if revision_no else "Rev 01",
        "date": report_date or datetime.now().strftime("%Y-%m-%d"),
        "airport_name": airport_name,
        "country": country,
        "coordinates": coordinates,
        "required_operation": f"{float(required_hours):.1f} hrs/day",
        "worst_blackout_risk": f"{worst_days} days/year" if worst_days is not None else "-",
        "worst_blackout_pct": f"{worst_pct:.1f}%" if worst_pct is not None else "-",
        "overall_conclusion_title": conclusion_title,
        "overall_conclusion_text": conclusion_text,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "methodology_note": "Based on PVGIS (European Commission).",
        "status": "Issued for Review",
        "prepared_under": "SALA-SAGL-100 methodology",
        "accent": accent,

        "device_name": worst_device.get("device_name") or worst_device.get("label") or "-",
        "achievable_worst_month": _format_hours_per_day(
            worst_device.get("worst_month_achieved_hours")
            or worst_device.get("minimum_daily_hours")
            or worst_device.get("achievable_worst_month_hours")
            or worst_device.get("lowest_sustainable_daily_operation")
        ),
        "battery_reserve": _format_duration_hours(
            worst_device.get("battery_reserve_hours")
            or worst_device.get("battery_only_reserve_hours")
            or worst_device.get("battery_reserve")
        ),

        "map_image_path": None,
        "monthly_chart_path": None,
        "annual_profile_chart_path": None,
    }
