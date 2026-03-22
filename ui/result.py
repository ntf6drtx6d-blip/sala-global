# ui/result.py
# FINAL FILE — SUMMARY DECISION

import streamlit as st


def format_hours_compact(hours: float) -> str:
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
    all_pass = all(r.get("status") == "PASS" for r in results.values())

    if all_pass:
        return "The selected configuration meets the required operating profile throughout the year."
    return "The selected configuration does not meet the required operating profile throughout the year."


def overall_interpretation_text(results: dict) -> str:
    days, pct = annual_empty_battery_stats(results)

    if days is None or pct is None:
        return "The annual blackout risk could not be calculated."

    if days == 0:
        return "No blackout days are expected at the selected operating profile."
    return f"Blackout risk is expected on {days} days/year ({pct:.1f}%) at the selected operating profile."


def render_text_kpi_card(title: str, value: str, subtitle: str = ""):
    html = """
    <div style="
        border:1px solid #e6eaf0;
        border-radius:16px;
        padding:18px 20px;
        background:#ffffff;
        min-height:170px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);
        display:flex;
        flex-direction:column;
        justify-content:space-between;">
        <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
        <div style="font-size:1.75rem;color:#1f2937;font-weight:800;line-height:1.15;word-break:break-word;">{value}</div>
        <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.4;">{subtitle}</div>
    </div>
    """.format(title=title, value=value, subtitle=subtitle)

    st.markdown(html, unsafe_allow_html=True)


def render_required_time_kpi_card(hours_value: float, mode_text: str, subtitle: str = ""):
    big_value = format_hours_compact(hours_value)
    window_text = operating_window_example(hours_value)
    pct = max(0, min(100, (float(hours_value) / 24.0) * 100))

    html = """
    <div style="
        border:1px solid #e6eaf0;
        border-radius:16px;
        padding:18px 20px;
        background:#ffffff;
        min-height:220px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);
        display:flex;
        flex-direction:column;
        justify-content:space-between;">

        <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">
            Airport lighting requirement
        </div>

        <div>
            <div style="
                font-size:2.35rem;
                color:#1f2937;
                font-weight:900;
                line-height:1.05;">
                {big_value}
            </div>

            <div style="
                font-size:1rem;
                color:#667085;
                margin-top:8px;">
                {mode_text}
            </div>
        </div>

        <div style="margin-top:14px;">
            <div style="
                display:flex;
                justify-content:space-between;
                font-size:0.82rem;
                color:#667085;
                margin-bottom:6px;">
                <span>00:00</span>
                <span>24:00</span>
            </div>

            <div style="
                width:100%;
                height:10px;
                background:#eef2f6;
                border-radius:999px;
                overflow:hidden;">
                <div style="
                    width:{pct}%;
                    height:100%;
                    background:#1f4fbf;
                    border-radius:999px;">
                </div>
            </div>

            <div style="
                font-size:0.88rem;
                color:#475467;
                margin-top:8px;
                font-weight:600;">
                Daily lighting need
            </div>

            <div style="
                font-size:0.88rem;
                color:#667085;
                margin-top:4px;">
                Example operating window: {window_text}
            </div>
        </div>

        <div style="
            font-size:0.9rem;
            color:#667085;
            margin-top:14px;
            line-height:1.4;">
            {subtitle}
        </div>
    </div>
    """.format(
        big_value=big_value,
        mode_text=mode_text,
        pct=f"{pct:.1f}",
        window_text=window_text,
        subtitle=subtitle,
    )

    st.markdown(html, unsafe_allow_html=True)


def render_blackout_days_kpi_card(title: str, days_value, pct_value, subtitle: str = ""):
    if days_value is None or pct_value is None:
        main = "N/A"
        secondary = "Annual blackout risk not available"
        bg = "#ffffff"
        border = "#e6eaf0"
        color = "#1f2937"
    else:
        main = f"{days_value} days/year"
        secondary = f"{pct_value:.1f}%"

        if int(days_value) == 0:
            bg = "#ecfdf3"
            border = "#abefc6"
            color = "#067647"
        else:
            bg = "#fef3f2"
            border = "#fecdca"
            color = "#b42318"

    html = """
    <div style="
        border:1px solid {border};
        border-radius:16px;
        padding:18px 20px;
        background:{bg};
        min-height:220px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);
        display:flex;
        flex-direction:column;
        justify-content:space-between;">

        <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">
            {title}
        </div>

        <div>
            <div style="
                font-size:2.35rem;
                color:{color};
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

        <div style="
            font-size:0.9rem;
            color:#667085;
            margin-top:14px;
            line-height:1.4;">
            {subtitle}
        </div>
    </div>
    """.format(
        border=border,
        bg=bg,
        title=title,
        color=color,
        main=main,
        secondary=secondary,
        subtitle=subtitle,
    )

    st.markdown(html, unsafe_allow_html=True)


def render_explanation_block(results: dict):
    days, pct = annual_empty_battery_stats(results)
    required_hours = float(st.session_state.get("required_hours", 0))

    if days is None or pct is None:
        blackout_line = "The annual blackout risk could not be calculated for the selected operating profile."
    elif days == 0:
        blackout_line = (
            "At the selected operating profile, no blackout days are expected. "
            "This means the system is expected to keep enough stored energy throughout the year."
        )
    else:
        blackout_line = (
            f"At the selected operating profile, blackout risk is expected on {days} days/year ({pct:.1f}%). "
            "This means the system does not recover enough solar energy during certain periods of the year."
        )

    st.markdown("### What this means")
    st.write(
        "This study checks whether the selected light can deliver the required daily operating time "
        "throughout the year at the chosen usage profile."
    )

    st.markdown("**Selected operating profile**")
    st.write(
        f"The airport requires {format_hours_compact(required_hours)} of lighting per day."
    )

    st.markdown("**Annual blackout risk**")
    st.write(blackout_line)

    st.markdown("**How to interpret battery reserve**")
    st.write(
        "Battery reserve is additional stored energy that can be used occasionally to extend operation. "
        "It is not meant to be used every day as the normal operating mode. "
        "Repeated overuse reduces solar energy recovery and eventually creates blackout days."
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

    summary_html = """
    <div style="
        border:1px solid {border};
        border-radius:18px;
        padding:22px 24px;
        background:{box_bg};
        box-shadow:0 2px 10px rgba(16,24,40,0.04);
        margin-bottom:22px;">
        <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">
            Overall conclusion
        </div>
        <div style="font-size:2rem;line-height:1.2;font-weight:800;color:{box_fg};margin-bottom:12px;">
            {headline}
        </div>
        <div style="font-size:1rem;color:#475467;">
            {subtext}
        </div>
    </div>
    """.format(
        border=border,
        box_bg=box_bg,
        box_fg=box_fg,
        headline=overall_conclusion_text(results),
        subtext=overall_interpretation_text(results),
    )

    st.markdown(summary_html, unsafe_allow_html=True)

    st.markdown("### Key takeaways")

    c1, c2, c3 = st.columns(3)

    with c1:
        render_text_kpi_card(
            "Airport",
            airport_name,
            "Study location used for the feasibility assessment",
        )

    with c2:
        render_required_time_kpi_card(
            required_hours,
            mode_name,
            "Daily lighting time required by the airport.",
        )

    with c3:
        render_blackout_days_kpi_card(
            "Blackout days",
            days,
            pct,
            "Days per year when the selected operating profile is not expected to be supported.",
        )

    render_explanation_block(results)
