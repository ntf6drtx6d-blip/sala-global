# app.py
# ACTION: REPLACE ENTIRE FILE

import os
import streamlit as st

from ui.setup import render_setup
from ui.cockpit import _run_simulation, reset_study
from ui.result import render_result
from ui.graph import render_graph
from ui.battery import render_battery_section
from ui.weather_basis import render_weather_basis


st.set_page_config(
    page_title="SALA Standardized Feasibility Study for Solar AGL",
    layout="wide"
)

LOGO_PATH = "sala_logo.png"


def init_state():
    defaults = {
        "airport_label": "",
        "airport_query": "",
        "lat": 40.416775,
        "lon": -3.703790,
        "required_hours": 12.0,
        "operating_profile_mode": "Custom hours per day",
        "selected_ids": [],
        "per_device_config": {},
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "sala_standardized_feasibility_study.pdf",
        "elapsed": None,
        "search_message": "",
        "map_click_info": "",
        "running": False,
        "run_progress": 0,
        "run_stage": "Ready",
        "run_log": [],
        "trigger_run": False,
        "study_point_confirmed": False,
        "study_ready": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def refresh_study_ready_from_state():
    selected_ids = st.session_state.get("selected_ids", [])
    study_point_confirmed = bool(st.session_state.get("study_point_confirmed", False))
    mode = st.session_state.get("operating_profile_mode")
    required_hours = st.session_state.get("required_hours")

    mode_ready = False
    if mode == "24/7":
        mode_ready = True
    elif mode == "Dusk to dawn":
        mode_ready = required_hours is not None
    elif mode == "Custom hours per day":
        mode_ready = required_hours is not None and float(required_hours) > 0

    st.session_state.study_ready = bool(
        len(selected_ids) > 0 and study_point_confirmed and mode_ready
    )


def apply_global_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        header[data-testid="stHeader"] {
            background: rgba(255,255,255,0);
        }

        .main-title {
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: 0.2rem;
            color: #1f2937;
        }

        .top-action-wrap {
            border: 1px solid #e8edf4;
            border-radius: 16px;
            padding: 12px 14px;
            background: #ffffff;
            box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
            margin-bottom: 16px;
        }

        .top-action-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #344054;
            margin-bottom: 8px;
        }

        div[data-testid="stDownloadButton"] > button {
            background: #1f4fbf !important;
            color: white !important;
            border: 1px solid #1f4fbf !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            min-height: 46px !important;
        }

        div[data-testid="stDownloadButton"] > button:hover {
            background: #183f98 !important;
            border-color: #183f98 !important;
            color: white !important;
        }

        .secondary-note {
            color: #667085;
            font-size: 0.95rem;
            line-height: 1.45;
            margin-top: 6px;
        }

        button[kind="secondary"] {
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.write("")
    c1, c2 = st.columns([1, 8])
    with c1:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=110)
    with c2:
        st.markdown(
            '<div class="main-title">SALA Standardized Feasibility Study for Solar AGL</div>',
            unsafe_allow_html=True,
        )


def _trigger_simulation():
    st.session_state.running = True
    st.session_state.run_stage = "Preparing simulation"
    st.session_state.trigger_run = True
    st.rerun()


# ui/result.py

import streamlit as st
import folium
from streamlit_folium import st_folium


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


def render_kpi_card(title: str, value: str, subtitle: str = "", bg="#ffffff", border="#e6eaf0", color="#1f2937"):
    html = """
    <div style="
        border:1px solid {border};
        border-radius:16px;
        padding:18px 20px;
        background:{bg};
        min-height:170px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);
        display:flex;
        flex-direction:column;
        justify-content:space-between;">
        <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
        <div style="font-size:2.15rem;color:{color};font-weight:900;line-height:1.1;word-break:break-word;">{value}</div>
        <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.4;">{subtitle}</div>
    </div>
    """.format(title=title, value=value, subtitle=subtitle, bg=bg, border=border, color=color)
    st.markdown(html, unsafe_allow_html=True)


def render_required_time_card(hours_value: float, mode_text: str):
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
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">

        <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">
            Airport lighting requirement
        </div>

        <div style="font-size:2.2rem;color:#1f2937;font-weight:900;line-height:1.05;">
            {big_value}
        </div>

        <div style="font-size:1rem;color:#667085;margin-top:8px;">
            {mode_text}
        </div>

        <div style="margin-top:14px;">
            <div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#667085;margin-bottom:6px;">
                <span>00:00</span><span>24:00</span>
            </div>

            <div style="width:100%;height:10px;background:#eef2f6;border-radius:999px;overflow:hidden;">
                <div style="width:{pct}%;height:100%;background:#1f4fbf;border-radius:999px;"></div>
            </div>

            <div style="font-size:0.88rem;color:#475467;margin-top:8px;font-weight:600;">
                Daily lighting need
            </div>

            <div style="font-size:0.88rem;color:#667085;margin-top:4px;">
                Example operating window: {window_text}
            </div>
        </div>
    </div>
    """.format(big_value=big_value, mode_text=mode_text, pct=f"{pct:.1f}", window_text=window_text)

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
        secondary = f"{pct_value:.1f}%"
        if int(days_value) == 0:
            bg = "#ecfdf3"
            border = "#abefc6"
            color = "#067647"
        else:
            bg = "#fef3f2"
            border = "#fecdca"
            color = "#b42318"

    render_kpi_card(
        "Blackout days",
        main,
        "Days per year when the selected operating profile is not expected to be supported.",
        bg=bg,
        border=border,
        color=color,
    )
    st.markdown(f"<div style='margin-top:-22px;color:#667085;font-size:1rem;'>{secondary}</div>", unsafe_allow_html=True)


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

    st_folium(fmap, width=None, height=320, returned_objects=[], key="result_location_map")


def render_explanation_blocks(results: dict):
    days, pct = annual_empty_battery_stats(results)
    required_hours = float(st.session_state.get("required_hours", 0))

    if days is None or pct is None:
        result_text = "The annual blackout risk could not be calculated for the selected operating profile."
    elif days == 0:
        result_text = (
            "At the selected operating profile, no blackout days are expected. "
            "This means the system is expected to keep enough stored energy throughout the year."
        )
    else:
        result_text = (
            f"At the selected operating profile, blackout risk is expected on {days} days/year ({pct:.1f}%). "
            "This means the system does not recover enough solar energy during certain periods of the year."
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        render_kpi_card(
            "What the airport needs",
            format_hours_compact(required_hours),
            "Daily lighting time required by the airport.",
        )

    with c2:
        render_kpi_card(
            "What the result means",
            "PASS" if days == 0 else "FAIL",
            result_text,
            bg="#ecfdf3" if days == 0 else "#fef3f2",
            border="#abefc6" if days == 0 else "#fecdca",
            color="#067647" if days == 0 else "#b42318",
        )

    with c3:
        render_kpi_card(
            "What to do next",
            "Keep profile" if days == 0 else "Adjust setup",
            "If blackout days are above zero, reduce operating hours or strengthen the system configuration.",
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
        render_location_map(lat, lon, airport_name)
        st.caption(airport_name)
        st.caption(f"{lat:.6f}, {lon:.6f}")

    with right:
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

        c1, c2 = st.columns(2)
        with c1:
            render_required_time_card(required_hours, mode_name)
        with c2:
            render_blackout_card(days, pct)

    st.markdown("### What this means")
    render_explanation_blocks(results)


init_state()
apply_global_styles()
render_header()

if not st.session_state.get("results"):
    render_setup()
else:
    with st.expander("Show study setup", expanded=False):
        render_setup()

refresh_study_ready_from_state()
render_top_action_bar()

if st.session_state.get("trigger_run"):
    st.session_state.trigger_run = False
    _run_simulation()

if st.session_state.get("results") is not None:
    results = st.session_state.get("results")
    render_result()
    render_graph()
    render_battery_section(results)
    render_weather_basis()
