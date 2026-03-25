from datetime import datetime


def _to_float(v, default=None):
    try:
        return float(v)
    except:
        return default


def _annual_empty_battery_stats(results):
    pcts = []
    for r in results.values():
        pct = _to_float(r.get("overall_empty_battery_pct"))
        if pct is not None:
            pcts.append(pct)

    if not pcts:
        return None, None

    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100)
    return worst_days, worst_pct


def _overall_state(results):
    total = len(results)
    passed = sum(1 for r in results.values() if r.get("status") == "PASS")

    if total == 0:
        return "unknown"
    if passed == total:
        return "all_pass"
    if passed == 0:
        return "none_pass"
    return "mixed"


def _pick_device(results):
    return list(results.values())[0] if results else {}


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
    coordinates = f"{loc.get('lat')}, {loc.get('lon')}"

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    state = _overall_state(results)
    device = _pick_device(results)

    if state == "all_pass":
        title = "System meets the required operating profile."
        text = "The system supports operation year-round."
        accent = "green"
    elif state == "mixed":
        title = "System partially meets the required operating profile."
        text = "At least one device is below requirement."
        accent = "gold"
    else:
        title = "System does not meet the required operating profile."
        text = "The system does not support operation year-round."
        accent = "red"

    return {
        "airport_name": airport_name,
        "coordinates": coordinates,
        "required_operation": f"{required_hours} hrs/day",
        "worst_blackout_risk": f"{worst_days} days/year",
        "worst_blackout_pct": f"{worst_pct:.1f}%",
        "overall_conclusion_title": title,
        "overall_conclusion_text": text,
        "accent": accent,

        "device_name": device.get("device_name"),
        "requirement_status": device.get("status"),
        "achievable_worst_month": device.get("minimum_daily_hours"),
        "battery_reserve": device.get("battery_reserve_hours"),

        "methodology_note": "Based on PVGIS (European Commission)",

        # filled later
        "map_image_path": None,
        "monthly_chart_path": None,
        "annual_profile_chart_path": None,
    }
