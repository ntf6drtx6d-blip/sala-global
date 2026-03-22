# ui/result.py

import math
import textwrap

import folium
import streamlit as st
from streamlit_folium import st_folium

from ui.result_helpers import (
    annual_empty_battery_stats,
    count_device_statuses,
    operating_mode_name,
    operating_window_example,
    overall_conclusion_text,
    overall_interpretation_text,
    overall_state,
)
from ui.result_devices import render_device_capability_cards


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


def render_airport_name_box(airport_name: str):
    html = textwrap.dedent(
        """
        <div style="
            border:1px solid #e6eaf0;
            border-radius:14px;
            padding:14px 16px;
            background:#ffffff;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
            margin-bottom:14px;">
            <div style="font-size:0.88rem;color:#667085;font-weight:700;margin-bottom:6px;">Airport / study point</div>
            <div style="font-size:1.35rem;color:#1f2937;font-weight:900;line-height:1.15;">{airport_name}</div>
        </div>
        """
    ).format(airport_name=airport_name)
    st.markdown(html, unsafe_allow_html=True)


def render_required_time_card(hours_value: float, mode_text: str):
    rounded_hours = math.ceil(float(hours_value))
    window_text = operating_window_example(hours_value)

    html = f"""
    <div style="
        border:1px solid #e6eaf0;
        border-radius:16px;
        padding:18px 20px;
        background:#ffffff;
        min-height:220px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">

        <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">
            Airport lighting requirement
        </div>

        <div style="font-size:2.2rem;color:#1f2937;font-weight:900;line-height:1.05;">
            {rounded_hours} hrs/day
        </div>

        <div style="font-size:0.95rem;color:#667085;margin-top:10px;">
            {mode_text}
        </div>

        <div style="font-size:0.95rem;color:#344054;margin-top:14px;font-weight:700;">
            {window_text}
        </div>

    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_blackout_card(days_value, pct_value):
    if days_value is None or pct_value is None:
        main = "N/A"
        secondary = "Worst-device blackout risk not available"
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
        f'Worst device blackout risk</div>'
        f'<div style="font-size:2.2rem;color:{color};font-weight:900;line-height:1.05;">'
        f'{main}</div>'
        f'<div style="font-size:1rem;color:#667085;margin-top:10px;">{secondary}</div>'
        f'<div style="font-size:0.9rem;color:#475467;margin-top:12px;line-height:1.45;">'
        f'Highest blackout exposure found within the selected device set.'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_device_summary_line(results: dict):
    total, passed, failed = count_device_statuses(results)

    if total <= 1:
        return

    if failed == 0:
        text = f"{passed} of {total} devices meet requirement"
        color = "#067647"
        bg = "#ecfdf3"
        border = "#abefc6"
    else:
        text = f"{failed} of {total} devices below requirement"
        color = "#b42318"
        bg = "#fef3f2"
        border = "#fecdca"

    html = f"""
    <div style="
        border:1px solid {border};
        background:{bg};
        color:{color};
        padding:16px 18px;
        border-radius:16px;
        font-weight:800;
        font-size:1.02rem;
        margin-top:18px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">
        {text}
    </div>
    """
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


def render_result():
    st.markdown("## Feasibility result")
    results = st.session_state.get("results", {})
    if not results:
        return

    state = overall_state(results)
    days, pct = annual_empty_battery_stats(results)

    airport_name = st.session_state.get("airport_label", "") or "Selected study point"
    required_hours = float(st.session_state.get("required_hours", 0))
    mode_name = operating_mode_name()
    lat = float(st.session_state.get("lat", 0))
    lon = float(st.session_state.get("lon", 0))

    if state == "all_pass":
        box_bg = "#ecfdf3"
        box_fg = "#067647"
        border = "#abefc6"
    elif state == "none_pass":
        box_bg = "#fef3f2"
        box_fg = "#b42318"
        border = "#fecdca"
    else:
        box_bg = "#fff7db"
        box_fg = "#7a5a00"
        border = "#f5c451"

    left, right = st.columns([1.05, 1.6], gap="large")

    with left:
        render_airport_name_box(airport_name)
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

        if len(results) > 1:
            render_device_summary_line(results)


__all__ = ["render_result", "render_device_capability_cards"]
