import os
import time
import tempfile
from datetime import datetime

import altair as alt
import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from devices import DEVICES, SOLAR_ENGINES
from simulate import simulate_for_devices
from report import make_pdf


st.set_page_config(
    page_title="SALA Standardized Feasibility Study for Solar AGL",
    layout="wide"
)

LOGO_PATH = "sala_logo.png"
EU_LOGO_PATH = "logo_en.gif"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def format_seconds(seconds):
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def now_ts():
    return datetime.now().strftime("%H:%M:%S")


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def geocode_airport(query):
    if not query or not query.strip():
        return None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1
    }
    headers = {
        "User-Agent": "SALA-Simulator/1.0"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        return None

    top = data[0]
    return {
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name", query)
    }


def create_map(lat, lon, label):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=14,
        control_scale=True,
        tiles="CartoDB positron"
    )

    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color="#d9534f",
        fill=True,
        fill_color="#d9534f",
        fill_opacity=0.9,
        weight=2,
        popup=label if label else f"{lat:.6f}, {lon:.6f}",
        tooltip=label if label else "Selected airport"
    ).add_to(fmap)

    folium.Circle(
        location=[lat, lon],
        radius=90,
        color="#d9534f",
        weight=1.5,
        fill=True,
        fill_color="#d9534f",
        fill_opacity=0.08
    ).add_to(fmap)

    return fmap


def build_results_table(results):
    rows = []
    for key, r in results.items():
        rows.append({
            "Device": short_device_label(key),
            "Engine": r["engine"],
            "PV (W)": r["pv"],
            "Battery (Wh)": r["batt"],
            "Power (W)": r["power"],
            "Tilt (deg)": r["tilt"],
            "Azimuth (deg)": round(r["azim"], 1),
            "Lowest-month difference (hrs/day)": round(r["min_margin"], 2),
            "Status": r["status"],
            "Fail months": ", ".join(r["fail_months"]) if r["fail_months"] else "-"
        })
    return pd.DataFrame(rows)


def build_monthly_df(results, required_hrs):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)
        for i, m in enumerate(months):
            value = float(r["hours"][i])
            diff = value - float(required_hrs)
            rows.append({
                "Month": m,
                "MonthNum": i + 1,
                "Device": label,
                "Hours": value,
                "RequiredHours": float(required_hrs),
                "Difference": diff,
                "StatusBand": "Above requirement" if diff >= 0 else "Below requirement",
                "Explanation": (
                    f"{label}: {value:.2f} hrs/day in {m}. "
                    f"Required profile: {required_hrs:.2f} hrs/day."
                )
            })

    return pd.DataFrame(rows)


def build_fill_data(monthly_df):
    above = monthly_df[monthly_df["Hours"] >= monthly_df["RequiredHours"]].copy()
    below = monthly_df[monthly_df["Hours"] < monthly_df["RequiredHours"]].copy()

    above["FillBottom"] = above["RequiredHours"]
    above["FillTop"] = above["Hours"]

    below["FillBottom"] = below["Hours"]
    below["FillTop"] = below["RequiredHours"]

    return above, below


def generate_recommendation(overall, worst_name, results):
    if overall == "PASS":
        return (
            "Recommended next step: proceed to installation-specific validation, "
            "including exact mounting geometry, shading review and final hardware selection."
        )

    weak = results.get(worst_name, {})
    fail_months = weak.get("fail_months", [])
    fail_months_text = ", ".join(fail_months) if fail_months else "one or more months"

    return (
        f"Recommended next step: review the weakest configuration "
        f"({short_device_label(worst_name)}) which falls below the target in {fail_months_text}. "
        f"Consider a stronger Solar Engine, higher battery reserve, lower power demand, "
        f"or a reduced required daily operating window."
    )


def pvgis_data_card():
    st.markdown(
        """
        <div style="
            border:1px solid #d9e2ef;
            border-radius:16px;
            padding:14px 16px;
            background:#f8fbff;
            margin-top:4px;
            margin-bottom:10px;">
            <div style="font-weight:700; color:#12355b; margin-bottom:6px;">
                External data and calculation engine
            </div>
            <div style="font-size:0.92rem; color:#475467; line-height:1.45;">
                <b>PVGIS — Photovoltaic Geographical Information System</b><br/>
                <b>Institution:</b> Joint Research Centre, European Commission<br/>
                <b>Dataset:</b> PVGIS-SARAH3
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def status_badge(text, ok=True):
    bg = "#0f9d58" if ok else "#d93025"
    return f"""
    <div style="
        display:inline-block;
        padding:8px 14px;
        border-radius:999px;
        background:{bg};
        color:white;
        font-weight:700;
        font-size:14px;
        margin-top:6px;
    ">
        {text}
    </div>
    """


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 0.85rem;
    padding-bottom: 2rem;
    max-width: 1520px;
}
header[data-testid="stHeader"] {
    background: rgba(255,255,255,0);
}
.main-title {
    font-size: 2.0rem;
    font-weight: 800;
    line-height: 1.05;
    margin-bottom: 0.22rem;
    color: #1f2937;
}
.sub-title {
    font-size: 1rem;
    color: #6b7280;
    margin-bottom: 0.5rem;
}
.card {
    border: 1px solid #e8edf4;
    border-radius: 20px;
    padding: 18px 18px 14px 18px;
    background: #ffffff;
    box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
    margin-bottom: 16px;
}
.section-title {
    font-size: 1.16rem;
    font-weight: 800;
    margin-bottom: 12px;
    color: #1f2937;
}
.metric-box {
    border: 1px solid #edf1f7;
    border-radius: 16px;
    padding: 12px 14px;
    background: linear-gradient(180deg, #fbfdff 0%, #f6f9fc 100%);
    min-height: 82px;
}
.metric-label {
    color: #6b7280;
    font-size: 0.82rem;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.08rem;
    font-weight: 800;
    color: #1f2937;
}
.device-title {
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}
.engine-tag {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #eef4ff;
    color: #234ea5;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 4px;
}
.builtin-tag {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #edf7ed;
    color: #1d7a43;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 4px;
}
.field-note {
    color:#667085;
    font-size:0.88rem;
    margin-top:4px;
    line-height:1.42;
}
.map-note {
    color:#6b7280;
    font-size:0.92rem;
    margin-top:8px;
}
.log-box {
    border: 1px solid #e5eaf1;
    border-radius: 14px;
    padding: 10px 12px;
    background: #fbfcfe;
}
.cockpit-label {
    color:#667085;
    font-size:0.83rem;
    margin-bottom:2px;
}
.cockpit-value {
    font-weight:700;
    font-size:0.98rem;
    margin-bottom:10px;
}
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------
defaults = {
    "lat": 40.416775,
    "lon": -3.703790,
    "airport_label": "",
    "search_message": "",
    "pdf_bytes": None,
    "pdf_name": "sala_standardized_feasibility_study.pdf",
    "last_results": None,
    "last_overall": None,
    "last_worst_name": None,
    "last_worst_gap": None,
    "last_slope": None,
    "map_click_info": "",
    "last_elapsed": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
h1, h2 = st.columns([1, 8])

with h1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=95)

with h2:
    st.markdown('<div class="main-title">SALA Standardized Feasibility Study for Solar AGL</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">A guided feasibility workflow using PVGIS solar and off-grid simulation outputs</div>',
        unsafe_allow_html=True
    )

# Top dynamic containers
simulation_area = st.container()
results_top_area = st.container()

# ---------------------------------------------------------
# Inputs
# ---------------------------------------------------------
left, right = st.columns([1.02, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">1. Define study location and operating profile</div>', unsafe_allow_html=True)

    airport_query = st.text_input(
        "Airport name",
        value=st.session_state.airport_label,
        placeholder="e.g. Schiphol Airport, Radom Airport, Torreón Airport"
    )

    if st.button("Find airport"):
        try:
            result = geocode_airport(airport_query)
            if result:
                st.session_state.lat = result["lat"]
                st.session_state.lon = result["lon"]
                st.session_state.airport_label = airport_query.strip() or result["display_name"]
                st.session_state.search_message = f"Found: {result['display_name']}"
                st.rerun()
            else:
                st.session_state.search_message = "Airport not found. Enter coordinates manually or click on the map."
                st.rerun()
        except Exception as e:
            st.session_state.search_message = f"Search error: {e}"
            st.rerun()

    if st.session_state.search_message:
        if st.session_state.search_message.startswith("Found:"):
            st.success(st.session_state.search_message)
        else:
            st.warning(st.session_state.search_message)

    c1, c2 = st.columns(2)
    with c1:
        lat = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=float(st.session_state.lat),
            format="%.6f"
        )
    with c2:
        lon = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=float(st.session_state.lon),
            format="%.6f"
        )

    st.session_state.lat = lat
    st.session_state.lon = lon

    c3, c4 = st.columns(2)
    with c3:
        required_hrs = st.number_input(
            "Required daily operating window (hrs/day)",
            min_value=0.0,
            max_value=24.0,
            value=8.0,
            step=0.5,
            help=(
                "How many hours per day the system must operate reliably throughout the year. "
                "This is not battery autonomy in isolation and not solar range."
            )
        )
        st.markdown(
            '<div class="field-note">'
            '<b>Critical input.</b> Enter the actual daily operating requirement. '
            'Example: if the lights must operate from 18:00 to 02:00 every day, enter 8.'
            '</div>',
            unsafe_allow_html=True
        )

    with c4:
        airport_name_for_report = st.text_input(
            "Airport label for report",
            value=st.session_state.airport_label
        )

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Map — click to define the exact study point</div>', unsafe_allow_html=True)

    selected_label = airport_name_for_report.strip() if airport_name_for_report.strip() else "Selected airport"
    fmap = create_map(lat, lon, selected_label)

    map_data = st_folium(
        fmap,
        width=None,
        height=520,
        returned_objects=["last_clicked"],
        key="airport_map_v4"
    )

    clicked = map_data.get("last_clicked") if isinstance(map_data, dict) else None
    if clicked:
        clicked_lat = float(clicked["lat"])
        clicked_lon = float(clicked["lng"])
        if abs(clicked_lat - st.session_state.lat) > 1e-7 or abs(clicked_lon - st.session_state.lon) > 1e-7:
            st.session_state.lat = clicked_lat
            st.session_state.lon = clicked_lon
            st.session_state.map_click_info = f"Study point updated: {clicked_lat:.6f}, {clicked_lon:.6f}"
            st.rerun()

    if st.session_state.map_click_info:
        st.success(st.session_state.map_click_info)

    st.markdown(
        f'<div class="map-note"><b>Selected point:</b> {st.session_state.lat:.6f}, {st.session_state.lon:.6f}</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="field-note">This exact point is used for the PVGIS calculation.</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Devices selection
# ---------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">2. Select devices</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="field-note">PAPI and A-PAPI are two separate device types and should be selected independently.</div>',
    unsafe_allow_html=True
)

device_options = {f"{k}. {v['code']} — {v['name']}": k for k, v in DEVICES.items()}
selected_labels = st.multiselect(
    "Choose devices to analyse",
    list(device_options.keys()),
    default=list(device_options.keys())[:2]
)
selected_ids = [device_options[x] for x in selected_labels]
st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Device config
# ---------------------------------------------------------
per_device_config = {}

if selected_ids:
    st.markdown('<div class="section-title">3. Configure selected devices</div>', unsafe_allow_html=True)

for did in selected_ids:
    dspec = DEVICES[did]
    system_type = dspec["system_type"]
    default_power = float(dspec["default_power"])

    with st.expander(f"{dspec['code']} — {dspec['name']}", expanded=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)

        t1, t2 = st.columns([2, 3])

        with t1:
            st.markdown(f'<div class="device-title">{dspec["code"]} — {dspec["name"]}</div>', unsafe_allow_html=True)
            if system_type == "builtin":
                st.markdown('<div class="builtin-tag">Built-in solar and battery</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="engine-tag">External Solar Engine</div>', unsafe_allow_html=True)

        engine_key = None
        battery_mode = "Std"
        pv_display = dspec.get("pv", 0)
        batt_display = dspec.get("batt", 0)
        engine_label = "BUILT-IN"

        if system_type == "external_engine":
            default_engine_key = dspec["default_engine"]
            engine_mode = st.radio(
                f"Solar Engine selection for {dspec['code']}",
                options=["Use default Solar Engine", "Choose Solar Engine manually"],
                horizontal=True,
                key=f"engine_mode_{did}"
            )

            compatible_engine_keys = dspec.get("compatible_engines", list(SOLAR_ENGINES.keys()))

            if engine_mode == "Use default Solar Engine":
                engine_key = default_engine_key
            else:
                engine_options = {
                    f"{SOLAR_ENGINES[k]['short_name']} — {SOLAR_ENGINES[k]['name']}": k
                    for k in compatible_engine_keys
                }
                engine_value_list = list(engine_options.values())
                chosen_label = st.selectbox(
                    f"Choose Solar Engine for {dspec['code']}",
                    list(engine_options.keys()),
                    index=engine_value_list.index(default_engine_key) if default_engine_key in engine_value_list else 0,
                    key=f"engine_select_{did}"
                )
                engine_key = engine_options[chosen_label]

            eng = SOLAR_ENGINES[engine_key]
            engine_label = eng["short_name"]

            if eng.get("batt_ext"):
                battery_mode = st.radio(
                    f"Battery mode for {dspec['code']}",
                    options=["Std", "Ext"],
                    horizontal=True,
                    key=f"battery_mode_{did}"
                )
                batt_display = eng["batt_ext"] if battery_mode == "Ext" else eng["batt"]
            else:
                battery_mode = "Std"
                batt_display = eng["batt"]

            pv_display = eng["pv"]

        with t2:
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Default power</div>
                    <div class="metric-value">{default_power:.2f} W</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Solar panel size</div>
                    <div class="metric-value">{pv_display} W</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Battery size</div>
                    <div class="metric-value">{batt_display} Wh</div>
                </div>
                """, unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Active source</div>
                    <div class="metric-value">{engine_label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.write("")

        power_mode = st.radio(
            f"Power setup for {dspec['code']}",
            options=["Use default power", "Enter power manually"],
            horizontal=True,
            key=f"power_mode_{did}"
        )

        if power_mode == "Use default power":
            selected_power = default_power
            st.caption(f"Using default power: {default_power:.2f} W")
        else:
            selected_power = st.number_input(
                f"Manual power for {dspec['code']} (W)",
                min_value=0.01,
                value=float(default_power),
                step=0.01,
                key=f"manual_power_{did}"
            )

        per_device_config[did] = {
            "power": float(selected_power),
            "engine_key": engine_key,
            "battery_mode": battery_mode,
        }

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Sidebar cockpit
# ---------------------------------------------------------
sidebar_status_placeholder = st.sidebar.empty()
sidebar_actions_placeholder = st.sidebar.empty()

with st.sidebar:
    st.markdown("## Study cockpit")

    st.markdown('<div class="cockpit-label">Location</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cockpit-value">{airport_name_for_report or "Not defined"}</div>', unsafe_allow_html=True)

    st.markdown('<div class="cockpit-label">Coordinates</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cockpit-value">{st.session_state.lat:.5f}, {st.session_state.lon:.5f}</div>', unsafe_allow_html=True)

    st.markdown('<div class="cockpit-label">Required operation</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cockpit-value">{required_hrs:.1f} hrs/day</div>', unsafe_allow_html=True)

    st.markdown('<div class="cockpit-label">Devices selected</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cockpit-value">{len(selected_ids)}</div>', unsafe_allow_html=True)

    st.markdown("---")

    if os.path.exists(EU_LOGO_PATH):
        st.image(EU_LOGO_PATH, width=110)

    pvgis_data_card()

    with st.expander("About PVGIS-SARAH3", expanded=False):
        st.write(
            "PVGIS-SARAH3 is a satellite-based solar radiation dataset used in PVGIS. "
            "It was calculated by CM SAF to replace SARAH-2 and covers Europe, Africa, "
            "most of Asia, and parts of South America."
        )
        st.write(
            "SALA uses this independent dataset and the European Commission JRC PVGIS engine "
            "to organize the feasibility assessment."
        )


run_clicked = False

with sidebar_status_placeholder.container():
    st.sidebar.markdown("### Status")
    if st.session_state.last_results is None:
        st.sidebar.info("Not run")
    else:
        st.sidebar.markdown(
            status_badge(
                f"Completed — {st.session_state.last_overall}",
                ok=(st.session_state.last_overall == "PASS")
            ),
            unsafe_allow_html=True
        )
        st.sidebar.write(f"**Weakest device:** {short_device_label(st.session_state.last_worst_name)}")
        st.sidebar.write(f"**Gap:** {round(abs(st.session_state.last_worst_gap), 2)} hrs/day")
        if st.session_state.last_elapsed is not None:
            st.sidebar.write(f"**Run time:** {format_seconds(st.session_state.last_elapsed)}")

with sidebar_actions_placeholder.container():
    st.sidebar.markdown("### Actions")
    if st.session_state.last_results is None:
        run_clicked = st.sidebar.button("Run simulation", type="primary", use_container_width=True)
    else:
        st.sidebar.button("Simulation completed", disabled=True, use_container_width=True)

    if st.session_state.pdf_bytes is not None:
        st.sidebar.download_button(
            "Download report",
            data=st.session_state.pdf_bytes,
            file_name=st.session_state.pdf_name,
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.sidebar.button("Download report", disabled=True, use_container_width=True)


# ---------------------------------------------------------
# Run simulation
# ---------------------------------------------------------
if run_clicked:
    with simulation_area:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 4. Run simulation")
        pvgis_data_card()

        st.write(
            "The study is now validating inputs, requesting solar/off-grid data from PVGIS, "
            "checking monthly performance and building the annual feasibility conclusion."
        )

        # step states
        step_placeholders = [st.empty() for _ in range(5)]
        progress_summary = st.empty()
        progress_bar = st.progress(0)
        log_box = st.empty()

        live_log = []
        current_step = {"idx": 0}

        def render_steps(active_idx):
            steps = [
                "Step 1 — Validating study inputs",
                "Step 2 — Requesting PVGIS data",
                "Step 3 — Processing monthly off-grid responses",
                "Step 4 — Checking weakest month against required operation",
                "Step 5 — Building final conclusion and report package",
            ]
            for i, txt in enumerate(steps):
                if i < active_idx:
                    step_placeholders[i].success(f"{txt} — completed")
                elif i == active_idx:
                    step_placeholders[i].info(f"{txt} — running")
                else:
                    step_placeholders[i].write(txt)

        def add_log(msg):
            live_log.append(f"**{now_ts()}** — {msg}")
            visible = live_log[-6:]
            log_box.markdown(
                '<div class="log-box">' + "<br/>".join(visible) + "</div>",
                unsafe_allow_html=True
            )

        render_steps(0)
        add_log("Checking selected airport coordinates and operating profile.")
        add_log("Preparing the PVGIS study request.")

        loc = {
            "lat": st.session_state.lat,
            "lon": st.session_state.lon,
            "label": airport_name_for_report.strip() if airport_name_for_report.strip() else f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
            "country": ""
        }

        started = time.time()

        def on_progress(done, total, pct, elapsed, eta, device_name, month_name):
            percent_value = int(pct * 100)
            progress_bar.progress(min(percent_value, 100))
            progress_summary.markdown(
                f"**Progress:** {percent_value}%  \n"
                f"**Elapsed:** {format_seconds(elapsed)}  \n"
                f"**Estimated time left:** {format_seconds(eta)}"
            )

            if percent_value < 12:
                step_idx = 0
            elif percent_value < 30:
                step_idx = 1
            elif percent_value < 65:
                step_idx = 2
            elif percent_value < 88:
                step_idx = 3
            else:
                step_idx = 4

            if step_idx != current_step["idx"]:
                current_step["idx"] = step_idx
                render_steps(step_idx)

            short_name = short_device_label(device_name)

            if done == 1:
                add_log("Connecting to PVGIS — Photovoltaic Geographical Information System.")
                add_log("Using the Joint Research Centre, European Commission engine and solar dataset.")
            if month_name == "Jan":
                add_log(f"Starting annual assessment for {short_name}.")
            if month_name == "Jun":
                add_log(f"Checking mid-year performance for {short_name}.")
            if month_name == "Dec":
                add_log(f"Verifying weakest winter performance for {short_name}.")

        try:
            results, overall, worst_name, worst_gap, slope = simulate_for_devices(
                loc=loc,
                required_hrs=required_hrs,
                selected_ids=selected_ids,
                per_device_config=per_device_config,
                az_override=None,
                progress_callback=on_progress
            )

            total_time = time.time() - started
            st.session_state.last_elapsed = total_time

            render_steps(5)
            progress_bar.progress(100)
            progress_summary.markdown(
                f"**Progress:** 100%  \n"
                f"**Elapsed:** {format_seconds(total_time)}  \n"
                f"**Estimated time left:** 0s"
            )

            add_log("PVGIS responses received for all selected configurations.")
            add_log("Comparing annual weakest-month performance against the required daily operation.")
            add_log("Preparing the final feasibility result and report package.")

            st.session_state.last_results = results
            st.session_state.last_overall = overall
            st.session_state.last_worst_name = worst_name
            st.session_state.last_worst_gap = worst_gap
            st.session_state.last_slope = slope

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                make_pdf(
                    tmp.name,
                    loc,
                    required_hrs,
                    results,
                    overall,
                    worst_name,
                    abs(worst_gap),
                    f"{round(slope)}°",
                    airport_name_for_report.strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    None
                )
                with open(tmp.name, "rb") as f:
                    st.session_state.pdf_bytes = f.read()
                st.session_state.pdf_name = "sala_standardized_feasibility_study.pdf"

            st.success("Simulation completed successfully.")
            st.rerun()

        except Exception as e:
            st.error(f"Simulation failed: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Results top
# ---------------------------------------------------------
if st.session_state.last_results is not None:
    with results_top_area:
        results = st.session_state.last_results
        overall = st.session_state.last_overall
        worst_name = st.session_state.last_worst_name
        worst_gap = st.session_state.last_worst_gap

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 5. Decision summary")

        s1, s2, s3, s4 = st.columns([1, 1.2, 2.2, 1.2])

        with s1:
            st.markdown("**Decision**")
            st.markdown(status_badge(overall, ok=(overall == "PASS")), unsafe_allow_html=True)

        with s2:
            st.markdown("**Reason**")
            st.write(f"Weakest device: {short_device_label(worst_name)}")
            st.write(f"Gap: {round(abs(worst_gap), 2)} hrs/day")

        with s3:
            st.markdown("**Recommendation**")
            st.write(generate_recommendation(overall, worst_name, results))

        with s4:
            if st.session_state.pdf_bytes is not None:
                st.download_button(
                    "Download report",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_name,
                    mime="application/pdf",
                    use_container_width=True
                )

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Detailed results
# ---------------------------------------------------------
if st.session_state.last_results is not None:
    results = st.session_state.last_results

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Results graph")

    monthly_df = build_monthly_df(results, required_hrs)
    all_devices = list(monthly_df["Device"].unique())

    visible_devices = st.multiselect(
        "Devices shown on graph",
        all_devices,
        default=all_devices,
        help="Untick devices to hide them from the graph."
    )

    chart_df = monthly_df[monthly_df["Device"].isin(visible_devices)].copy()
    above_df, below_df = build_fill_data(chart_df)

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    green_area = alt.Chart(above_df).mark_area(
        color="#16a34a",
        opacity=0.18
    ).encode(
        x=alt.X("Month:N", sort=month_order, title="Month of the year"),
        y=alt.Y(
            "FillTop:Q",
            title="Guaranteed operating hours per day",
            scale=alt.Scale(domain=[0, 24])
        ),
        y2="FillBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Difference:Q", title="Surplus vs requirement", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
            alt.Tooltip("Explanation:N", title="Meaning")
        ]
    )

    red_area = alt.Chart(below_df).mark_area(
        color="#dc2626",
        opacity=0.22
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("FillTop:Q", scale=alt.Scale(domain=[0, 24])),
        y2="FillBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Difference:Q", title="Deficit vs requirement", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
            alt.Tooltip("Explanation:N", title="Meaning")
        ]
    )

    device_lines = alt.Chart(chart_df).mark_line(point=True, strokeWidth=2.8).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        color=alt.Color(
            "Device:N",
            title="Device lines",
            scale=alt.Scale(scheme="tableau10")
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Difference:Q", title="Difference vs requirement", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
            alt.Tooltip("Explanation:N", title="Meaning")
        ]
    )

    req_line_df = pd.DataFrame({
        "Month": month_order,
        "Required": [float(required_hrs)] * 12,
        "Legend": [f"Required daily operation = {required_hrs:.2f} hrs/day"] * 12
    })

    req_line = alt.Chart(req_line_df).mark_line(
        strokeDash=[10, 5],
        strokeWidth=3.0,
        color="#111827"
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Required:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Legend:N", title="Reference")
        ]
    )

    chart = (green_area + red_area + device_lines + req_line).properties(
        height=470
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        '<div class="field-note">'
        '<b>How to read this chart:</b> each coloured line is one selected device. '
        'The thick black dashed line is the required daily operating window. '
        '<span style="color:#16a34a;"><b>Green fill</b></span> means the device is above the requirement. '
        '<span style="color:#dc2626;"><b>Red fill</b></span> means it is below the requirement. '
        'The vertical axis is fixed from 0 to 24 hrs/day.'
        '</div>',
        unsafe_allow_html=True
    )

    legend_df = pd.DataFrame({
        "Series": ["Required daily operation"],
        "Type": ["Black dashed reference line"]
    })
    st.dataframe(legend_df, use_container_width=False, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Results table")
    st.dataframe(build_results_table(results), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Monthly operating profile")
    month_rows = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i, m in enumerate(months):
        row = {"Month": m, "Required hrs/day": required_hrs}
        for name, r in results.items():
            row[short_device_label(name)] = round(r["hours"][i], 2)
        month_rows.append(row)
    st.dataframe(pd.DataFrame(month_rows), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("6. PVGIS transparency", expanded=False):
        pvgis_data_card()
        st.write(
            "SALA uses PVGIS as the external solar and off-grid calculation engine. "
            "PVGIS then provides the responses used to build the annual feasibility assessment."
        )
        for device_name, r in results.items():
            meta = r["pvgis_meta"]
            with st.expander(f"Show PVGIS request details — {short_device_label(device_name)}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**PVGIS endpoints used**")
                    st.write(f"- {meta['pvcalc_endpoint']}")
                    st.write(f"- {meta['shs_endpoint']}")
                    st.write(f"- Dataset: {meta['dataset']}")
                    st.markdown("**PVcalc parameters**")
                    st.json(meta["pvcalc_params"])
                with c2:
                    st.markdown("**SHScalc parameters**")
                    st.json(meta["shs_params"])

                st.markdown("**Example PVcalc request URL**")
                st.code(meta["pvcalc_url_example"], language="text")

                st.markdown("**Example SHScalc request URL**")
                st.code(meta["shs_url_example"], language="text")

    with st.expander("7. Meaning of study inputs", expanded=False):
        st.markdown("""
        **Location**  
        Defines the exact study point used for PVGIS solar and off-grid calculations.

        **Required daily operating window (hrs/day)**  
        Defines how many hours per day the system must operate reliably throughout the year.  
        This is not the same as standalone battery autonomy and not the same as "solar range".

        **Power**  
        Defines the device load used during the feasibility assessment.

        **Solar panel size**  
        Defines the available PV generation capacity.

        **Battery size**  
        Defines the stored energy reserve available to support operation when solar generation is not sufficient.

        **Solar Engine / Battery mode**  
        Defines the external power source configuration for supported devices.
        """)

    if st.session_state.pdf_bytes is not None:
        st.download_button(
            "Download PDF report",
            data=st.session_state.pdf_bytes,
            file_name=st.session_state.pdf_name,
            mime="application/pdf",
            use_container_width=False
        )