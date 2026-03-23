from datetime import datetime


def _annual_empty_battery_stats(results: dict):
    pcts = []
    for _, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is not None:
            try:
                pcts.append(float(pct))
            except Exception:
                pass

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


def build_report_data(loc, required_hours, results, overall, document_no="", revision_no=0, airport_label="", report_date=""):
    airport_name = airport_label or loc.get("label", "Study point")
    country = loc.get("country", "") or ""
    coordinates = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    state = _overall_state(results)

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
            "The selected configuration is not fully compliant because at least one device remains "
            "below requirement under worst-case solar conditions."
        )
        recommendation = "Review the non-compliant configuration."
        accent = "gold"

    else:
        conclusion_title = "System does not meet the required operating profile."
        conclusion_text = "The system does not support the required operating profile year-round."
        interpretation = (
            "The system does not sustain the required operating profile under worst-case solar conditions, "
            "resulting in blackout exposure."
        )
        recommendation = "System redesign is required."
        accent = "red"

    revision_text = f"Rev {int(revision_no):02d} – Issued for Review" if revision_no else "Rev 01 – Issued for Review"

    return {
        "report_id": document_no or "SALA-SFS-2026-000134",
        "revision": revision_text,
        "date": report_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "airport_name": airport_name,
        "country": country,
        "coordinates": coordinates,
        "required_operation": f"{float(required_hours):.0f} hrs/day",
        "worst_blackout_risk": f"{worst_days} days/year" if worst_days is not None else "N/A",
        "worst_blackout_pct": f"{worst_pct:.1f}% of the year" if worst_pct is not None else "",
        "overall_conclusion_title": conclusion_title,
        "overall_conclusion_text": conclusion_text,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "methodology_note": (
            "This assessment is based on long-term solar irradiation data and hourly off-grid simulation "
            "methodology consistent with PVGIS (European Commission Joint Research Centre)."
        ),
        "status": "Issued for Review",
        "prepared_under": "Prepared under SALA-SAGL-100 methodology",
        "accent": accent,
    }
