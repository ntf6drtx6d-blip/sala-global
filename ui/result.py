# ui/result.py
# ACTION: REPLACE ENTIRE FILE

import math
import streamlit as st


def short_device_label(full_name: str) -> str:
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def format_hours_compact(hours: float) -> str:
    """
    Show duration as:
    - 12 hrs/day
    - 4 h 30 min/day
    """
    h = float(hours)
    whole = int(h)
    minutes = int(round((h - whole) * 60))

    if minutes == 60:
        whole += 1
        minutes = 0

    if minutes == 0:
        return f"{whole} hrs/day"
    return f"{whole} h {minutes:02d} min/day"


def operating_mode_name() -> str:
    mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
    if mode == "24/7":
        return "24/7 operation"
    if mode == "Dusk to dawn":
        return "Dusk-to-Dawn"
    return "Custom operation"


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


def overall_conclusion_text(results: dict) -> str:
    mode_name = operating_mode_name()
    required_hours = float(st.session_state.get("required_hours", 0))
    all_pass = all(r.get("status") == "PASS" for r in results.values())

    if all_pass:
        return (
            f"Selected devices can sustain {mode_name} "
            f"({required_hours:.1f} hrs/day) throughout the year."
        )

    return (
        f"Selected devices cannot sustain {mode_name} "
        f"({required_hours:.1f} hrs/day) throughout the year."
    )


def overall_interpretation_text(results: dict) -> str:
    all_pass = all(r.get("status") == "PASS" for r in results.values())
    if all_pass:
        return "The selected configuration meets the required operating window in all months."
    return "At least one selected configuration falls below the required operating window in part of the year."


def device_empty_battery_line(r: dict) -> str:
    pct = r.get("overall_empty_battery_pct")
    if pct is None:
        return "Days with empty battery: not available"

    try:
        pct = float(pct)
    except Exception:
        return "Days with empty battery: not available"

    days = round(365 * pct / 100.0)
    return f"{days} days/year ({pct:.1f}%)"


def device_worst_month_line(r: dict) -> str:
    monthly_days = r.get("empty_battery_days_by_month")
    if not monthly_days:
        return "Worst month: not available"

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    idx = max(range(12), key=lambda i: monthly_days[i])
    worst_days = monthly_days[idx]
    worst_pct = 0.0
    monthly_pct = r.get("empty_battery_pct_by_month")
    if monthly_pct and idx < len(monthly_pct):
        try:
            worst_pct = float(monthly_pct[idx])
        except Exception:
            worst_pct = 0.0

    return f"{months[idx]} ({worst_days} days, {worst_pct:.1f}% of days in that month)"


def _recommended_hours_floor(result_row: dict):
    hours = result_row.get("hours", [])
    if not hours:
        return None
    return math.floor(min(hours) * 10) / 10


def _is_external_engine_device(result_row: dict) -> bool:
    return result_row.get("system_type") == "external_engine"


def recommendation_text(device_name: str, result_row: dict) -> str:
    status = result_row.get("status", "FAIL")

    if status == "PASS":
        return "No configuration change is required for year-round feasibility."

    recommended_hours = _recommended_hours_floor(result_row)
    if recommended_hours is None:
        return "Review the selected configuration and operating requirement."

    if _is_external_engine_device(result_row):
        return (
            f"To achieve year-round feasibility, reduce required daily operation to "
            f"{recommended_hours:.1f} hrs/day, or select a stronger Solar Engine / larger battery configuration."
        )

    return (
        f"To achieve year-round feasibility, reduce required daily operation to "
        f"{recommended_hours:.1f} hrs/day for this device, or select a different light configuration "
        f"with higher energy capacity."
    )


def graph_meaning_text(result_row: dict) -> str:
    status = result_row.get("status", "FAIL")
    fail_months = result_row.get("fail_months", [])

    if status == "PASS":
        return "The guaranteed operating time stays at or above the required threshold in all months."

    if not fail_months:
        return "The selected configuration does not fully meet the required operating threshold."

    if len(fail_months) == 12:
        return "The guaranteed operating time stays below the required threshold in all months."

    if len(fail_months) == 1:
        return f"The guaranteed operating time falls below the required threshold in {fail_months[0]}."

    return (
        "The guaranteed operating time falls below the required threshold in "
        f"{', '.join(fail_months)}."
    )


def battery_difference_text(result_row: dict) -> str:
    reserve = None
    try:
        batt = float(result_row.get("batt", 0))
        power = max(float(result_row.get("power", 0.01)), 0.01)
        reserve = batt * 0.70 / power
    except Exception:
        pass

    if reserve is None:
        return (
            "Battery autonomy shows how long the light can run from stored battery energy only. "
            "Annual solar feasibility shows whether the system can recover enough energy day after day throughout the year."
        )

    return (
        f"Battery autonomy for this configuration is approximately {reserve:.1f} hrs from stored battery energy only. "
        "This is different from annual solar feasibility, which shows whether the system can recover enough energy "
        "day after day throughout the year."
    )


def render_text_kpi_card(title: str, value: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            min-height:170px;
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            display:flex;
            flex-direction:column;
            justify-content:space-between;">
            <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div style="font-size:1.75rem;color:#1f2937;font-weight:800;line-height:1.15;word-break:break-word;">{value}</div>
            <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.4;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_time_kpi_card(title: str, hours_value: float, mode_text: str, subtitle: str = ""):
    big_value = format_hours_compact(hours_value)
    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            min-height:170px;
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            display:flex;
            flex-direction:column;
            justify-content:space-between;">
            <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div>
                <div style="
                    font-size:2.6rem;
                    color:#1f2937;
                    font-weight:900;
                    line-height:1.05;">
                    {big_value}
                </div>
                <div style="
                    font-size:1rem;
                    color:#667085;
                    margin-top:10px;">
                    {mode_text}
                </div>
            </div>
            <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.4;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_days_kpi_card(title: str, days_value, pct_value, subtitle: str = ""):
    if days_value is None or pct_value is None:
        main = "N/A"
        secondary = "PVGIS annual depletion metric not available"
    else:
        main = f"{days_value} days/year"
        secondary = f"{pct_value:.1f}%"

    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            min-height:170px;
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            display:flex;
            flex-direction:column;
            justify-content:space-between;">
            <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div>
                <div style="
                    font-size:2.6rem;
                    color:#1f2937;
                    font-weight:900;
                    line-height:1.05;">
                    {main}
                </div>
                <div style="
                    font-size:1rem;
                    color:#667085;
                    margin-top:10px;">
                    {secondary}
                </div>
            </div>
            <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.4;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_interpretation_block(device_name: str, r: dict):
    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);">
            <div style="font-size:1.05rem;font-weight:800;color:#1f2937;margin-bottom:12px;">
                Interpretation for {short_device_label(device_name)}
            </div>

            <div style="font-size:0.92rem;font-weight:800;color:#344054;margin-bottom:6px;">
                What the graph shows
            </div>
            <div style="font-size:0.95rem;color:#475467;line-height:1.55;">
                {graph_meaning_text(r)}
            </div>

            <div style="font-size:0.92rem;font-weight:800;color:#344054;margin-top:14px;margin-bottom:6px;">
                Battery autonomy vs annual solar feasibility
            </div>
            <div style="font-size:0.95rem;color:#475467;line-height:1.55;">
                {battery_difference_text(r)}
            </div>

            <div style="font-size:0.92rem;font-weight:800;color:#344054;margin-top:14px;margin-bottom:6px;">
                Recommended next step
            </div>
            <div style="font-size:0.95rem;color:#475467;line-height:1.55;">
                {recommendation_text(device_name, r)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.get("results", {})
    if not results:
        return

    all_pass = all(r.get("status") == "PASS" for r in results.values())
    days, pct = annual_empty_battery_stats(results)
    airport_name = st.session_state.get("airport_label", "") or "Selected study point"
    required_hours = float(st.session_state.get("required_hours", 0))
    mode_name = operating_mode_name()

    box_bg = "#ecfdf3" if all_pass else "#fef3f2"
    box_fg = "#067647" if all_pass else "#b42318"
    border = "#abefc6" if all_pass else "#fecdca"

    st.markdown(
        f"""
        <div style="
            border:1px solid {border};
            border-radius:18px;
            padding:22px 24px;
            background:{box_bg};
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            margin-bottom:22px;">
            <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">
                Overall conclusion
            </div>
            <div style="font-size:2rem;line-height:1.2;font-weight:800;color:{box_fg};margin-bottom:12px;">
                {overall_conclusion_text(results)}
            </div>
            <div style="font-size:1rem;color:#475467;">
                {overall_interpretation_text(results)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Key takeaways")

    c1, c2, c3 = st.columns(3)

    with c1:
        render_text_kpi_card(
            "Airport",
            airport_name,
            "Study location used for the feasibility assessment",
        )

    with c2:
        render_time_kpi_card(
            "Required operating time",
            required_hours,
            mode_name,
            "Applied requirement used for the study",
        )

    with c3:
        render_days_kpi_card(
            "Days with empty battery",
            days,
            pct,
            "Estimated annual battery depletion risk",
        )

    # Interpretation block only for selected / primary device if there is one,
    # otherwise show worst failing device, otherwise first device.
    primary_device_name = None

    if len(results) == 1:
        primary_device_name = next(iter(results.keys()))
    else:
        failing = [(name, r) for name, r in results.items() if r.get("status") != "PASS"]
        if failing:
            primary_device_name = min(failing, key=lambda item: min(item[1].get("hours", [999])))[0]
        elif results:
            primary_device_name = next(iter(results.keys()))

    if primary_device_name:
        st.markdown("### What this means")
        render_interpretation_block(primary_device_name, results[primary_device_name])
