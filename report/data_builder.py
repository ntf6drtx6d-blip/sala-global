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
    worst_key = None
    worst = None
    worst_pct = -1
    for key, r in results.items():
        pct = _to_float(r.get("overall_empty_battery_pct"), -1)
        if pct > worst_pct:
            worst_pct = pct
            worst_key = key
            worst = r
    return worst_key, (worst or {})


def _pick_best_device(results: dict):
    best_key = None
    best = None
    best_pct = 1e9
    for key, r in results.items():
        pct = _to_float(r.get("overall_empty_battery_pct"), 1e9)
        if pct < best_pct:
            best_pct = pct
            best_key = key
            best = r
    return best_key, (best or {})


def _overall_state(results: dict):
    if not results:
        return "unknown"
    statuses = [r.get("status") for r in results.values()]
    if all(s == "PASS" for s in statuses):
        return "all_pass"
    if all(s == "FAIL" for s in statuses):
        return "none_pass"
    return "mixed"


def _reserve_hours(device: dict):
    try:
        batt = float(device.get("batt", 0))
        power = max(float(device.get("power", 0.01)), 0.01)
        reserve = batt * 0.70 / power
        return reserve
    except Exception:
        return None


def _format_hours(value):
    val = _to_float(value)
    if val is None:
        return "-"
    if float(val).is_integer():
        return f"{int(val)} hrs/day"
    return f"{val:.1f} hrs/day"


def _format_reserve(device: dict):
    reserve = _reserve_hours(device)
    if reserve is None:
        return "-"
    total_minutes = round(reserve * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes:02d}m"


def _month_name_of_min(device: dict):
    hours = device.get("hours") or []
    if not hours:
        return "-"
    idx = min(range(len(hours)), key=lambda i: hours[i])
    return MONTHS[idx]


def _summary_message(state: str):
    if state == "all_pass":
        return (
            "The selected configuration remains above the required operating profile "
            "throughout the year and does not show annual blackout exposure."
        )
    if state == "mixed":
        return (
            "At least one selected configuration falls below the required operating profile "
            "under worst-case solar conditions and should be reviewed."
        )
    return (
        "The selected configuration does not support the required operating profile "
        "year-round and shows blackout exposure."
    )


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
    country = loc.get("country") or "-"
    coordinates = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    state = _overall_state(results)
    worst_name, worst_device = _pick_worst_device(results)
    best_name, best_device = _pick_best_device(results)

    worst_hours = worst_device.get("hours") or []
    lowest_hours = min(worst_hours) if worst_hours else None

    if state == "all_pass":
        accent = "green"
        conclusion_title = "System meets the required operating profile."
        conclusion_text = "The system supports operation year-round."
    elif state == "mixed":
        accent = "gold"
        conclusion_title = "System partially meets the required operating profile."
        conclusion_text = "At least one selected device remains below requirement."
    else:
        accent = "red"
        conclusion_title = "System does not meet the required operating profile."
        conclusion_text = "The system does not support operation year-round."

    revision_text = f"Rev {int(revision_no):02d}" if revision_no else "Rev 01"

    return {
        "report_id": document_no or f"SALA-SFS-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "revision": revision_text,
        "date": report_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "airport_name": airport_name,
        "country": country,
        "coordinates": coordinates,
        "prepared_by": prepared_by or "SALA user",
        "prepared_under": "SALA Standardized Feasibility Methodology",
        "methodology_note": (
            "Prepared using PVGIS developed by the Joint Research Centre (JRC), "
            "European Commission, and organized using SALA's standardized off-grid feasibility logic."
        ),
        "required_operation": _format_hours(required_hours),
        "worst_blackout_risk": f"{worst_days} days/year" if worst_days is not None else "-",
        "worst_blackout_pct": f"{worst_pct:.1f}% of the year" if worst_pct is not None else "-",
        "overall_conclusion_title": conclusion_title,
        "overall_conclusion_text": conclusion_text,
        "executive_summary": _summary_message(state),
        "accent": accent,
        "device_name": worst_device.get("name") or worst_name or "-",
        "engine_name": worst_device.get("engine") or "-",
        "achievable_worst_month": _format_hours(lowest_hours),
        "battery_reserve": _format_reserve(worst_device),
        "worst_month_name": _month_name_of_min(worst_device),
        "worst_month_hours": _format_hours(lowest_hours),
        "best_device_name": best_device.get("name") or best_name or "-",
        "best_device_blackout_pct": f"{_to_float(best_device.get('overall_empty_battery_pct'), 0):.1f}%",
        "selected_device_count": len(results),
        "overall_result": overall or "-",
        "map_image_path": None,
        "monthly_chart_path": None,
        "annual_profile_chart_path": None,
        "pvgis_meta": worst_device.get("pvgis_meta", {}),
    }
