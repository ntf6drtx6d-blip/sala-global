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
        radius=14,
        color="#d9534f",
        fill=True,
        fill_color="#d9534f",
        fill_opacity=0.92,
        weight=3,
        popup=label if label else f"{lat:.6f}, {lon:.6f}",
        tooltip=label if label else "Selected airport"
    ).add_to(fmap)

    folium.Circle(
        location=[lat, lon],
        radius=220,
        color="#d9534f",
        weight=2,
        fill=True,
        fill_color="#d9534f",
        fill_opacity=0.10
    ).add_to(fmap)

    return fmap


def build_results_table(results):
    rows = []
    for key, r in results.items():
        rows.append({
            "Device": key,
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
        for i, m in enumerate(months):
            value = float(r["hours"][i])
            rows.append({
                "Month": m,
                "Device": device_name,
                "Hours": value,
                "RequiredHours": float(required_hrs),
                "Difference": value - float(required_hrs),
                "StatusBand": "Above requirement" if value >= float(required_hrs) else "Below requirement",
                "Explanation": (
                    f"{device_name} can operate for {value:.2f} hrs/day in {m}. "
                    f"Required profile is {required_hrs:.2f} hrs/day."
                )
            })
    return pd.DataFrame(rows)


def build_fill_data(monthly_df):
    above = monthly_df[monthly_df["Hours"] >= monthly_df["RequiredHours"]].copy()
    below = monthly_df[monthly_df["Hours"] < monthly_df["RequiredHours"]].copy()

    above["y_low"] = above["RequiredHours"]
    above["y_high"] = above["Hours"]

    below["y_low"] = below["Hours"]
    below["y_high"] = below["RequiredHours"]

    return above, below


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
        margin-top:8px;
    ">
        {text}
    </div>
    """


def pvgis_note_html():
    return """
    <div style="
        border:1px solid #d9e2ef;
        border-radius:16px;
        padding:14px 16px;
        background:#f8fbff;
        margin-top:6px;
        margin-bottom:10px;">
        <div style="font-weight:700; color:#12355b; margin-bottom:6px;">
            Data engine: PVGIS / Joint Research Centre (European Commission)
        </div>
        <div style="font-size:0.94rem; color:#475467; line-height:1.5;">
            This simulation uses PVGIS as the external calculation engine and source of solar/off-grid performance data.
            SALA sends the selected inputs to PVGIS, retrieves the results, and then organizes them into a feasibility assessment.
        </div>
    </div>
    """


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 0.9rem;
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
    margin-bottom: 0.25rem;
    color: #1f2937;
}
.sub-title {
    font-size: 1rem;
    color: #6b7280;
    margin-bottom: 0.55rem;
}
.card {
    border: 1px solid #e8edf4;
    border-radius: 20px;
    padding: 20px 20px 16px 20px;
    background: #ffffff;
    box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
    margin-bottom: 16px;
}
.section-title {
    font-size: 1.2rem;
    font-weight: 800;
    margin-bottom: 14px;
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
    font-size: 1.2rem;
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
}
.map-note {
    color:#6b7280;
    font-size:0.92rem;
    margin-top:8px;
}
.action-card {
    border: 1px solid #e3eaf5;
    border-radius: 18px;
    padding: 14px 16px;
    background: linear-gradient(180deg, #fcfdff 0%, #f7fafe 100%);
    margin-bottom: 16px;
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
if "lat" not in st.session_state:
    st.session_state.lat = 40.416775
if "lon" not in st.session_state:
    st.session_state.lon = -3.703790
if "airport_label" not in st.session_state:
    st.session_state.airport_label = ""
if "search_message" not in st.session_state:
    st.session_state.search_message = ""
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = "sala_standardized_feasibility_study.pdf"
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_overall" not in st.session_state:
    st.session_state.last_overall = None
if "last_worst_name" not in st.session_state:
    st.session_state.last_worst_name = None
if "last_worst_gap" not in st.session_state:
    st.session_state.last_worst_gap = None
if "last_slope" not in st.session_state:
    st.session_state.last_slope = None
if "map_click_info" not in st.session_state:
    st.session_state.map_click_info = ""


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
        '<div class="sub-title">PVGIS-based solar feasibility tool for airfield lighting, PAPI and A-PAPI systems</div>',
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Top action bar
# ---------------------------------------------------------
st.markdown('<div class="action-card">', unsafe_allow_html=True)
a1, a2, a3 = st.columns([2, 1, 1])

with a1:
    st.markdown(pvgis_note_html(), unsafe_allow_html=True)

with a2:
    run_top = st.button("Run simulation", type="primary", use_container_width=True)

with a3:
    if st.session_state.pdf_bytes is not None:
        st.download_button(
            "Download PDF",
            data=st.session_state.pdf_bytes,
            file_name=st.session_state.pdf_name,
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.button("Download PDF", disabled=True, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Location and map
# ---------------------------------------------------------
left, right = st.columns([1.02, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Location and operating profile</div>', unsafe_allow_html=True)

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
                st.session_state.search_message = "Airport not found. Enter coordinates manually or click the map."
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
                "This means how many hours per day the light or device must be able to operate year-round. "
                "It is NOT battery autonomy in isolation and NOT 'solar range'. "
                "Example: if runway lights must work 8 hours every day, enter 8."
            )
        )
        st.markdown(
            '<div class="field-note">Enter the actual daily operating requirement. '
            'This is the most critical input and is often confused with battery autonomy or solar range.</div>',
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
    st.markdown('<div class="section-title">Map — click to select location</div>', unsafe_allow_html=True)

    selected_label = airport_name_for_report.strip() if airport_name_for_report.strip() else "Selected airport"
    fmap = create_map(lat, lon, selected_label)

    map_data = st_folium(
        fmap,
        width=None,
        height=530,
        returned_objects=["last_clicked"],
        key="airport_map"
    )

    clicked = map_data.get("last_clicked") if isinstance(map_data, dict) else None
    if clicked:
        clicked_lat = float(clicked["lat"])
        clicked_lon = float(clicked["lng"])
        if abs(clicked_lat - st.session_state.lat) > 1e-7 or abs(clicked_lon - st.session_state.lon) > 1e-7:
            st.session_state.lat = clicked_lat
            st.session_state.lon = clicked_lon
            st.session_state.map_click_info = f"Point selected from map: {clicked_lat:.6f}, {clicked_lon:.6f}"
            st.rerun()

    if st.session_state.map_click_info:
        st.success(st.session_state.map_click_info)

    st.markdown(
        f'<div class="map-note"><b>Selected point:</b> {st.session_state.lat:.6f}, {st.session_state.lon:.6f}</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="field-note">Tip: zoom in and click directly on the airport area to place the simulation point.</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Devices
# ---------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Select devices</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="field-note">PAPI and A-PAPI are treated as two separate device types and should be selected independently.</div>',
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
# Device configuration cards
# ---------------------------------------------------------
per_device_config = {}

if selected_ids:
    st.markdown('<div class="section-title">Device configuration</div>', unsafe_allow_html=True)

for did in selected_ids:
    dspec = DEVICES[did]
    system_type = dspec["system_type"]
    default_power = float(dspec["default_power"])

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
# Simulation run
# ---------------------------------------------------------
if run_top:
    if not selected_ids:
        st.error("Select at least one device.")
    else:
        loc = {
            "lat": st.session_state.lat,
            "lon": st.session_state.lon,
            "label": airport_name_for_report.strip() if airport_name_for_report.strip() else f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
            "country": ""
        }

        status_card = st.container()
        progress_card = st.container()

        with status_card:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Simulation status")
            st.markdown(
                "Connecting to **PVGIS** — the external solar and off-grid calculation engine provided by the **Joint Research Centre (European Commission)**."
            )
            stage_placeholder = st.empty()
            detail_placeholder = st.empty()
            st.markdown('</div>', unsafe_allow_html=True)

        with progress_card:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            progress_bar = st.progress(0)
            progress_text = st.empty()
            step_text = st.empty()
            st.markdown('</div>', unsafe_allow_html=True)

        def on_progress(done, total, pct, elapsed, eta, device_name, month_name):
            percent_value = int(pct * 100)
            progress_bar.progress(min(percent_value, 100))

            if percent_value < 10:
                stage = "Preparing inputs for PVGIS"
            elif percent_value < 35:
                stage = "Sending requests to PVGIS"
            elif percent_value < 85:
                stage = "Retrieving and validating monthly off-grid results from PVGIS"
            else:
                stage = "Building annual feasibility assessment"

            stage_placeholder.info(f"Current stage: {stage}")
            detail_placeholder.write(
                f"PVGIS source active • Device: **{device_name}** • Month: **{month_name}**"
            )

            progress_text.markdown(
                f"**Simulation progress:** {percent_value}%  \n"
                f"**Elapsed time:** {format_seconds(elapsed)}  \n"
                f"**Estimated time left:** {format_seconds(eta)}"
            )
            step_text.caption(
                "PVGIS is calculating solar/off-grid performance. "
                "SALA is organizing the returned data into an annual feasibility result."
            )

        started = time.time()

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
            progress_bar.progress(100)
            stage_placeholder.success("Current stage: Simulation completed successfully")
            detail_placeholder.write(
                "PVGIS responses received and processed. Annual feasibility assessment completed."
            )
            progress_text.markdown(
                f"**Simulation progress:** 100%  \n"
                f"**Elapsed time:** {format_seconds(total_time)}  \n"
                f"**Estimated time left:** 0s"
            )
            step_text.caption(
                "Result confidence note: the solar/off-grid dataset was sourced from PVGIS / European Commission JRC."
            )

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

        except Exception as e:
            st.error(f"Simulation failed: {e}")


# ---------------------------------------------------------
# Results section
# ---------------------------------------------------------
if st.session_state.last_results is not None:
    results = st.session_state.last_results
    overall = st.session_state.last_overall
    worst_name = st.session_state.last_worst_name
    worst_gap = st.session_state.last_worst_gap

    st.write("")
    r1, r2, r3 = st.columns([1, 1, 2])

    with r1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Overall result**")
        st.markdown(status_badge(overall, ok=(overall == "PASS")), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with r2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Worst-case device**")
        st.markdown(f"**{worst_name}**")
        st.caption(f"Gap vs requirement: {round(abs(worst_gap), 2)} hrs/day")
        st.markdown('</div>', unsafe_allow_html=True)

    with r3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Result interpretation**")
        if overall == "PASS":
            st.write(
                "All selected configurations stay above the required daily operating window in every month of the year."
            )
        else:
            st.write(
                "At least one selected configuration falls below the required daily operating window in one or more months."
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Results graph")

    monthly_df = build_monthly_df(results, required_hrs)
    all_devices = list(monthly_df["Device"].unique())

    visible_devices = st.multiselect(
        "Devices shown on graph",
        all_devices,
        default=all_devices,
        help="Untick devices to hide them from the chart."
    )

    chart_df = monthly_df[monthly_df["Device"].isin(visible_devices)].copy()
    above_df, below_df = build_fill_data(chart_df)

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    base = alt.Chart(chart_df).encode(
        x=alt.X(
            "Month:N",
            sort=month_order,
            title="Month of the year"
        )
    )

    green_area = alt.Chart(above_df).mark_area(opacity=0.16).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("y_high:Q", title="Guaranteed operating hours per day"),
        y2="y_low:Q",
        color=alt.Color(
            "Device:N",
            legend=alt.Legend(title="Device"),
            scale=alt.Scale(scheme="greens")
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated operating hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Difference:Q", title="Difference vs requirement", format=".2f"),
            alt.Tooltip("Explanation:N", title="Meaning")
        ]
    )

    red_area = alt.Chart(below_df).mark_area(opacity=0.18).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("y_high:Q"),
        y2="y_low:Q",
        color=alt.Color(
            "Device:N",
            legend=None,
            scale=alt.Scale(scheme="reds")
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated operating hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Difference:Q", title="Difference vs requirement", format=".2f"),
            alt.Tooltip("Explanation:N", title="Meaning")
        ]
    )

    device_lines = base.mark_line(point=True, strokeWidth=2.5).encode(
        y=alt.Y("Hours:Q", title="Guaranteed operating hours per day"),
        color=alt.Color(
            "Device:N",
            legend=alt.Legend(title="Device"),
            scale=alt.Scale(scheme="tableau10")
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated operating hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Difference:Q", title="Difference vs requirement", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Result band"),
            alt.Tooltip("Explanation:N", title="Meaning")
        ]
    )

    req_line_df = pd.DataFrame({
        "Month": month_order,
        "Required": [float(required_hrs)] * 12,
        "Label": [f"Required daily operating window = {required_hrs:.2f} hrs/day"] * 12
    })

    req_line = alt.Chart(req_line_df).mark_line(
        strokeDash=[8, 5],
        strokeWidth=2.2,
        color="#111827"
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Required:Q"),
        tooltip=[
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Required:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Label:N", title="Explanation")
        ]
    )

    chart = (green_area + red_area + device_lines + req_line).properties(
        height=470
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        '<div class="field-note">'
        '<b>How to read this chart:</b> the black dashed line is the required daily operating window. '
        'Green transparent fill means the selected system is above the requirement. '
        'Red transparent fill means it is below the requirement for that month. '
        'Hover on any line or area to see the detailed meaning.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Results table")
    df = build_results_table(results)
    st.dataframe(df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Monthly autonomy")
    month_rows = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i, m in enumerate(months):
        row = {"Month": m, "Required hrs/day": required_hrs}
        for name, r in results.items():
            row[name] = round(r["hours"][i], 2)
        month_rows.append(row)
    st.dataframe(pd.DataFrame(month_rows), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### PVGIS transparency")
    st.write(
        "This simulation is designed to build trust around an external public source. "
        "The solar and off-grid performance data are requested from **PVGIS**, developed by the "
        "**Joint Research Centre of the European Commission**."
    )
    st.write(
        "SALA does not replace PVGIS with a separate hidden solar dataset. "
        "It uses PVGIS responses and organizes them into an airfield-lighting feasibility assessment."
    )

    for device_name, r in results.items():
        meta = r["pvgis_meta"]
        with st.expander(f"Show PVGIS request details — {device_name}"):
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

            st.info(
                "PVGIS performs the solar/off-grid calculation. "
                "SALA uses that output to build the annual feasibility result."
            )

    st.markdown('</div>', unsafe_allow_html=True)