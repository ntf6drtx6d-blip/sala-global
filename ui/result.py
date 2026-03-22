import math
import textwrap

import folium
import streamlit as st
from streamlit_folium import st_folium


# =========================
# FORMATTERS
# =========================

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


# =========================
# DATA HELPERS
# =========================

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


# =========================
# UI BLOCKS
# =========================

def render_kpi_card(title, value, subtitle="", bg="#fff", border="#e6eaf0", color="#1f2937"):
    html = f"""
    <div style="
        border:1px solid {border};
        border-radius:16px;
        padding:18px;
        background:{bg};
        min-height:150px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);
    ">
        <div style="font-size:0.9rem;color:#667085;font-weight:700;">{title}</div>
        <div style="font-size:2rem;font-weight:900;color:{color};margin-top:6px;">{value}</div>
        <div style="font-size:0.9rem;color:#667085;margin-top:8px;">{subtitle}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_airport_name_box(name):
    st.markdown(f"""
    <div style="
        border:1px solid #e6eaf0;
        border-radius:14px;
        padding:14px;
        background:white;
        margin-bottom:12px;
    ">
        <div style="font-size:0.85rem;color:#667085;font-weight:700;">Airport / study point</div>
        <div style="font-size:1.3rem;font-weight:900;">{name}</div>
    </div>
    """, unsafe_allow_html=True)


def render_location_map(lat, lon, name):
    m = folium.Map(location=[lat, lon], zoom_start=10, tiles="CartoDB positron")

    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color="#c0392b",
        fill=True
    ).add_to(m)

    st_folium(m, height=320)


# =========================
# MAIN RESULT
# =========================

def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.get("results", {})
    if not results:
        return

    airport = st.session_state.get("airport_label", "Selected study point")
    lat = st.session_state.get("lat", 0)
    lon = st.session_state.get("lon", 0)
    required = float(st.session_state.get("required_hours", 0))

    total, passed, failed = count_device_statuses(results)
    state = overall_state(results)
    days, pct = annual_empty_battery_stats(results)

    # =========================
    # HEADER
    # =========================

    left, right = st.columns([1, 1.6])

    with left:
        render_airport_name_box(airport)
        render_location_map(lat, lon, airport)

    with right:
        if state == "all_pass":
            color = "#067647"
            bg = "#ecfdf3"
            text = "All selected devices meet the required operating profile."
        elif state == "none_pass":
            color = "#b42318"
            bg = "#fef3f2"
            text = "None of the selected devices meet the required operating profile."
        else:
            color = "#7a5a00"
            bg = "#fff7db"
            text = f"{passed} of {total} devices meet the requirement."

        st.markdown(f"""
        <div style="border:1px solid {color};border-radius:16px;padding:20px;background:{bg}">
            <div style="font-weight:700;color:#667085">Overall conclusion</div>
            <div style="font-size:1.6rem;font-weight:900;color:{color}">{text}</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        with c1:
            render_kpi_card("Required operation", f"{int(required)} hrs/day")

        with c2:
            render_kpi_card("Worst-case blackout", f"{days} days/year" if days else "0")

    # =========================
    # WHAT THIS MEANS
    # =========================

    st.markdown("### What this means")

    c1, c2, c3 = st.columns(3)

    with c1:
        render_kpi_card("Devices OK", f"{passed}/{total}")

    with c2:
        render_kpi_card("Devices FAIL", f"{failed}/{total}")

    with c3:
        if state == "all_pass":
            action = "Use as is"
        elif state == "mixed":
            action = "Fix weakest device"
        else:
            action = "Increase system size"

        render_kpi_card("Recommended action", action)

    # =========================
    # PER DEVICE ANALYSIS
    # =========================

    st.markdown("## Device-level performance")

    for name, r in results.items():

        hours = r.get("hours", [])
        achievable = min(hours) if hours else None

        batt = r.get("batt", 0)
        power = max(r.get("power", 0.01), 0.01)
        reserve = batt * 0.7 / power

        status = r.get("status", "FAIL")

        st.markdown(f"### {name}")

        c1, c2, c3 = st.columns(3)

        with c1:
            render_kpi_card("Required", format_required_hours(required))

        with c2:
            render_kpi_card("Achievable", format_achievable_hours(achievable) if achievable else "N/A")

        with c3:
            render_kpi_card("Battery reserve", format_battery_hours(reserve))

        # KEY MESSAGE (ВАЖЛИВО — це твоя логіка)
        if achievable:
            msg = (
                f"Required {required:.1f} hrs/day. "
                f"In worst month: {achievable:.1f} hrs/day. "
                f"Battery reserve: {reserve:.1f} hrs. "
            )

            if status == "PASS":
                msg += "Device supports operation year-round."
            else:
                msg += "Limitation driven by insufficient solar recovery."

        else:
            msg = "Insufficient data."

        st.markdown(f"""
        <div style="
            border-left:4px solid #3b5ccc;
            background:#f8fafc;
            padding:14px;
            border-radius:10px;
            margin-top:10px;
        ">
        {msg}
        </div>
        """, unsafe_allow_html=True)
