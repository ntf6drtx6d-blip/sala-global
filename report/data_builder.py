from datetime import datetime


def _to_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


# -------------------------
# BLACKOUT STATS
# -------------------------
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


# -------------------------
# DEVICE STATUS
# -------------------------
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


# -------------------------
# WORST DEVICE (KEY LOGIC)
# -------------------------
def _pick_worst_device(results: dict):
    """
    Select device with highest blackout risk
    """
    worst_key = None
    worst_result = None
    worst_pct = -1

    for key, r in results.items():
        pct = _to_float(r.get("overall_empty_battery_pct"), default=-1)

        if pct > worst_pct:
            worst_pct = pct
            worst_key = key
            worst_result = r

    if worst_result:
        return worst_key, worst_result

    for key, r in results.items():
        return key, r

    return None, {}


# -------------------------
# FORMATTERS
# -------------------------
def _format_hours_per_day(value):
    v = _to_float(value)
    if v is None:
        return "—"
    return f"{v:.1f} hrs/day" if not v.is_integer() else f"{int(v)} hrs/day"


def _format_duration_hours(value):
    v = _to_float(value)
    if v is None:
        return "—"

    minutes = int(round(v * 60))
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m:02d}m"


# -------------------------
# MAIN BUILDER
# -------------------------
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
    country = loc.get("country", "") or ""
    coordinates = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    state = _overall_state(results)

    device_id, device = _pick_worst_device(results)

    # -------------------------
    # CONCLUSION LOGIC
    # -------------------------
    if state == "all_pass":
        conclusion_title = "System meets the required operating profile."
        conclusion_text = "The system supports the required operating profile year-round."
        interpretation = (
            "The system demonstrates sufficient energy autonomy and resilience "
            "to support continuous airfield operations under the defined profile."
        )
        recommendation = "Proceed with deployment."
        accent = "green"

    elif state == "mixed":
        conclusion_title = "System partially meets the required operating profile."
        conclusion_text = "At least one selected device remains below requirement."
        interpretation = (
            "At least one configuration does not sustain the required operation "
            "under worst-case solar conditions."
        )
        recommendation = "Review non-compliant configuration."
        accent = "gold"

    else:
        conclusion_title = "System does not meet the required operating profile."
        conclusion_text = "The system does not support the required operating profile year-round."
        interpretation = (
            "The system does not sustain required operation under worst-case solar conditions."
        )
        recommendation = "System redesign required."
        accent = "red"

    # -------------------------
    # DEVICE DATA (for summary)
    # -------------------------
    device_name = (
        device.get("device_name")
        or device.get("label")
        or str(device_id or "Device")
    )

    requirement_status = (
        "Meets requirement"
        if device.get("status") == "PASS"
        else "Below requirement"
    )

    achievable_worst_month = _format_hours_per_day(
        device.get("worst_month_achieved_hours")
        or device.get("minimum_daily_hours")
    )

    battery_reserve = _format_duration_hours(
        device.get("battery_reserve_hours")
        or device.get("battery_only_reserve_hours")
    )

    # -------------------------
    # CUSTOM OPERATION WINDOW
    # -------------------------
    custom_operation = ""
    if loc.get("operation_start_hour") is not None:
        custom_operation = (
            f"{int(loc['operation_start_hour']):02d}:00–"
            f"{int(loc['operation_end_hour']):02d}:00"
        )

    # -------------------------
    # FINAL OUTPUT
    # -------------------------
    revision_text = (
        f"Rev {int(revision_no):02d} – Issued for Review"
        if revision_no
        else "Rev 01 – Issued for Review"
    )

    return {
        "report_id": document_no or "SALA-SFS-2026-000001",
        "revision": revision_text,
        "date": report_date or datetime.now().strftime("%Y-%m-%d %H:%M"),

        "airport_name": airport_name,
        "country": country or "N/A",
        "coordinates": coordinates,

        "required_operation": f"{float(required_hours):.0f} hrs/day",
        "custom_operation": custom_operation,

        "worst_blackout_risk": (
            f"{worst_days} days/year" if worst_days is not None else "N/A"
        ),
        "worst_blackout_pct": (
            f"{worst_pct:.1f}% of the year" if worst_pct is not None else ""
        ),

        "overall_conclusion_title": conclusion_title,
        "overall_conclusion_text": conclusion_text,

        "interpretation": interpretation,
        "recommendation": recommendation,

        "methodology_note": (
            "This assessment is based on PVGIS (Joint Research Centre, European Commission), "
            "using long-term historical solar radiation and weather data."
        ),

        "status": "Issued for Review",
        "prepared_under": "Prepared under SALA methodology",
        "accent": accent,

        # 👇 summary fields
        "device_name": device_name,
        "requirement_status": requirement_status,
        "achievable_worst_month": achievable_worst_month,
        "battery_reserve": battery_reserve,
        "map_note": "Verified airport location used for the feasibility study.",

        # 👇 filled later in report.py
        "map_image_path": None,
        "monthly_chart_path": None,
        "annual_profile_chart_path": None,
    }
