# ui/result_helpers.py

import math
import streamlit as st


def format_required_hours(hours: float) -> str:
    return f"{math.ceil(float(hours))} hrs/day"


def format_achievable_hours(hours: float) -> str:
    return f"{math.floor(float(hours))} hrs/day"


def format_battery_hours(hours: float) -> str:
    h = float(hours)
    whole = int(h)
    minutes = int(round((h - whole) * 60))
    if minutes == 60:
        whole += 1
        minutes = 0
    if minutes == 0:
        return f"{whole}h"
    return f"{whole}h {minutes:02d}m"


def operating_mode_name() -> str:
    mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
    if mode == "24/7":
        return "24/7 operation"
    if mode == "Dusk to dawn":
        return "Dusk-to-Dawn"
    return "Custom operation"


def operating_window_example(hours_value: float) -> str:
    h = max(0.0, min(float(hours_value), 24.0))
    if h >= 24:
        return "00:00–24:00"

    end_hour = 6.0
    start_hour = (end_hour - h) % 24

    def fmt(x: float) -> str:
        whole = int(x) % 24
        minutes = int(round((x - int(x)) * 60))
        if minutes == 60:
            whole = (whole + 1) % 24
            minutes = 0
        return f"{whole:02d}:{minutes:02d}"

    return f"{fmt(start_hour)}–{fmt(end_hour)}"


def short_device_label(full_name: str) -> str:
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def annual_empty_battery_stats(results: dict):
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


def count_device_statuses(results: dict):
    total = len(results)
    passed = 0

    for _, r in results.items():
        if r.get("status") == "PASS":
            passed += 1

    failed = total - passed
    return total, passed, failed


def overall_state(results: dict):
    total, passed, failed = count_device_statuses(results)

    if total == 0:
        return "unknown"
    if passed == total:
        return "all_pass"
    if failed == total:
        return "none_pass"
    return "mixed"


def battery_reserve_hours(result_row: dict):
    try:
        batt = float(result_row.get("batt", 0))
        power = max(float(result_row.get("power", 0.01)), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def device_blackout_days(result_row: dict):
    try:
        pct = result_row.get("overall_empty_battery_pct")
        if pct is None:
            return None
        return round(365 * float(pct) / 100.0)
    except Exception:
        return None


def overall_conclusion_text(results: dict) -> str:
    state = overall_state(results)
    total, _, _ = count_device_statuses(results)

    if total == 1:
        if state == "all_pass":
            return "The selected device meets the required operating profile."
        if state == "none_pass":
            return "The selected device does not meet the required operating profile."
        return "The selected device could not be fully assessed."

    if state == "all_pass":
        return "All selected devices meet the required operating profile."
    if state == "none_pass":
        return "None of the selected devices meet the required operating profile."
    if state == "mixed":
        return "Some selected devices meet the required operating profile."
    return "The selected device set could not be fully assessed."


def overall_interpretation_text(results: dict) -> str:
    total, passed, _ = count_device_statuses(results)
    state = overall_state(results)

    if total == 1:
        if state == "all_pass":
            return "The selected operating profile is supported year-round."
        if state == "none_pass":
            return "The selected device does not support the selected operating profile year-round."
        return "The selected device could not be fully assessed."

    if state == "all_pass":
        return "The selected operating profile is supported year-round by all selected devices."

    if state == "none_pass":
        return "No selected device supports the selected operating profile year-round."

    if state == "mixed":
        return (
            f"{passed} of {total} selected devices support the operating profile. "
            "The system is not fully compliant because at least one device remains below requirement."
        )

    return "The selected device set could not be fully assessed."
