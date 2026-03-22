# ui/result.py
# FINAL CLEAN VERSION

import math
import textwrap

import folium
import streamlit as st
from streamlit_folium import st_folium


def format_required_hours(hours: float) -> str:
    return f"{math.ceil(float(hours))} hrs/day"


def format_achievable_hours(hours: float) -> str:
    return f"{math.floor(float(hours))} hrs/day"


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


def worst_sustainable_hours(results: dict):
    mins = []
    for _, r in results.items():
        hours = r.get("hours", [])
        if hours:
            try:
                mins.append(min(float(x) for x in hours))
            except Exception:
                pass
    if not mins:
        return None
    return min(mins)


def overall_conclusion_text(results: dict) -> str:
    days, _ = annual_empty_battery_stats(results)
    if days is None:
        return "The selected configuration could not be fully assessed."
    if days == 0:
        return "The selected configuration supports the required operating profile throughout the year."
    return "The selected configuration does not support the required operating profile throughout the year."


def overall_interpretation_text(results: dict) -> str:
    days, pct = annual_empty_battery_stats(results)
    if days is None or pct is None:
        return "The annual blackout risk could not be calculated."

    if days == 0:
        return "No blackout days are expected at the selected operating profile."
    return f"Blackout risk is expected on {days} days/year ({pct:.1f}%) at the selected operating profile."


def render_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    bg: str = "#ffffff",
    border: str = "#e6eaf0",
    color: str = "#1f2937",
    min_height: int = 170,
):
    html = textwrap.dedent(
        """
        <div style="
            border:1px solid {border};
            border-radius:16px;
            padding:18px 20px;
            background:{bg};
            min-height:{min_height}px;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
            display:flex;
            flex-direction:column;
            justify-content:space-between;">
            <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div style="font-size:2.1rem;color:{color};font-weight:900;line-height:1.1;word-break:break-word;">{value}</div>
            <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.45;">{subtitle}</div>
        </div>
        """
    ).format(
        title=title,
        value=value,
        subtitle=subtitle,
        bg=bg,
        border=border,
        color=color,
        min_height=min_height,
    )
    st.markdown(html, unsafe_allow_html=True)


def render_required_time_card(hours_value: float, mode_text: str):
    rounded_hours = math.ceil(float(hours_value))
    window_text = operating_window_example(hours_value)
    pct = max(0, min(100, (float(hours_value) / 24.0) * 100))

    html = (
        f'<div style="border:1px solid #e6eaf0;border-radius:16px;padding:18px 20px;'
        f'background:#ffffff;min-height:220px;box-shadow:0 2px 10px rgba(16,24,40,0.04);">'
        f'<div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">'
        f'Airport lighting requirement</div>'
        f'<div style="font-size:2.2rem;color:#1f2937;font-weight:900;line-height:1.05;">'
        f'{rounded_hours} hrs/day</div>'
        f'<div style="font-size:1rem;color:#667085;margin-top:8px;">{mode_text}</div>'
        f'<div style="margin-top:16px;">'
        f'<div style="font-size:0.88rem;color:#475467;font-weight:700;margin-bottom:8px;">'
        f'Required daily lighting window</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#667085;margin-bottom:6px;">'
        f'<span>00:00</span><span>24:00</span></div>'
        f'<div style="position:relative;width:100%;height:12px;background:#eef2f6;border-radius:999px;overflow:hidden;">'
        f'<div style="width:{pct:.1f}%;height:100%;background:#1f4fbf;border-radius:999px;"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:flex-end;margin-top:8px;">'
        f'<span style="font-size:0.88rem;color:#1f4fbf;font-weight:800;background:#eef4ff;'
        f'padding:4px 10px;border-radius:999px;">{rounded_hours} h</span>'
        f'</div>'
        f'<div style="font-size:0.88rem;color:#667085;margin-top:8px;">'
        f'Example operating window: {window_text}</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_blackout_card(days_value, pct_value):
    if days_value is None or pct_value is None:
        main = "N/A"
        secondary = "Annual blackout risk not available"
        bg = "#ffffff"
        border = "#e6eaf0"
        color = "#1f2937"
    else:
        main = f"{days_value} days/year"
        secondary = f"{pct_value:.1f}% of the year"
        if int(days_value) == 0:
            bg = "#ecfdf3"
            border = "#abefc6"
            color = "#067647"
        else:
            bg = "#fef3f2"
            border = "#fecdca"
            color = "#b42318"

    html = (
        f'<div style="border:1px solid {border};border-radius:16px;padding:18px 20px;'
        f'background:{bg};min-height:220px;box-shadow:0 2px 10px rgba(16,24,40,0.04);">'
        f'<div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">'
        f'Blackout days</div>'
        f'<div style="font-size:2.2rem;color:{color};font-weight:900;line-height:1.05;">'
        f'{main}</div>'
        f'<div style="font-size:1rem;color:#667085;margin-top:10px;">{secondary}</div>'
        f'<div style="font-size:0.9rem;color:#475467;margin-top:12px;line-height:1.45;">'
        f'Days per year when the selected operating profile is not expected to be supported.'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_location_map(lat: float, lon: float, airport_name: str):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=10,
        control_scale=True,
        tiles="CartoDB positron",
    )

    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color="#c0392b",
        fill=True,
        fill_color="#c0392b",
        fill_opacity=0.9,
        weight=2,
        tooltip=airport_name or "Selected study point",
    ).add_to(fmap)

    st_folium(
        fmap,
        width=None,
        height=320,
        returned_objects=[],
        key="result_location_map",
    )


def render_explanation_blocks(results: dict):
    days, pct = annual_empty_battery_stats(results)
    sustainable = worst_sustainable_hours(results)

    if days is None or pct is None:
        result_text = "The annual blackout risk could not be calculated for the selected operating profile."
        confidence_text = "Simulation result is incomplete."
        action_text = "Review the selected inputs and rerun the study."
        result_value = "Review needed"
        result_bg = "#fff7db"
        result_border = "#f5c451"
        result_color = "#7a5a00"
    elif days == 0:
        result_text = "Required daily operation is supported throughout the full annual cycle."
        confidence_text = "No blackout days are expected at the selected operating profile."
        action_text = "Configuration can be used as selected."
        result_value = "Supported"
        result_bg = "#ecfdf3"
        result_border = "#abefc6"
        result_color = "#067647"
    else:
        result_text = f"Blackout risk is expected on {days} days/year ({pct:.1f}%)."
        confidence_text = "This means the selected daily operating profile is not sustained year-round."
        action_text = "Reduce daily operating hours or strengthen the system configuration."
        result_value = "Not supported"
        result_bg = "#fef3f2"
        result_border = "#fecdca"
        result_color = "#b42318"

    c1, c2, c3 = st.columns(3)

    with c1:
        render_kpi_card(
            "What this result means",
            result_value,
            result_text,
            bg=result_bg,
            border=result_border,
            color=result_color,
            min_height=200,
        )

    with c2:
        value = format_achievable_hours(sustainable) if sustainable is not None else "N/A"
        subtitle = (
            "Lowest daily operating time the system can sustain continuously during the weakest solar period."
            if sustainable is not None
            else "Could not be calculated."
        )
        render_kpi_card(
            "Operational confidence",
            value,
            subtitle,
            min_height=200,
        )

    with c3:
        render_kpi_card(
            "Recommended action",
            "No change required" if days == 0 else "Adjust setup",
            action_text,
            min_height=200,
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
    lat = float(st.session_state.get("lat", 0))
    lon = float(st.session_state.get("lon", 0))

    box_bg = "#ecfdf3" if all_pass else "#fef3f2"
    box_fg = "#067647" if all_pass else "#b42318"
    border = "#abefc6" if all_pass else "#fecdca"

    left, right = st.columns([1.05, 1.6], gap="large")

    with left:
        st.markdown("### Location")
        st.markdown(f"**{airport_name}**")
        render_location_map(lat, lon, airport_name)
        st.caption(f"{lat:.6f}, {lon:.6f}")

    with right:
        summary_html = textwrap.dedent(
            """
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
            """
        ).format(
            border=border,
            box_bg=box_bg,
            box_fg=box_fg,
            headline=overall_conclusion_text(results),
            subtext=overall_interpretation_text(results),
        )

        st.markdown(summary_html, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            render_required_time_card(required_hours, mode_name)
        with c2:
            render_blackout_card(days, pct)

    st.markdown("### What this means")
    render_explanation_blocks(results)
