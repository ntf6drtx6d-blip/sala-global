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


# ---------------------------------------------------------
# Page setup
# ---------------------------------------------------------
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
    params = {"q": query, "format": "jsonv2", "limit": 1}
    headers = {"User-Agent": "SALA-Simulator/1.0"}

    resp = requests.get(url, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        return None

    top = data[0]
    return {
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name", query),
    }


def create_map(lat, lon, label):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=14,
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
        popup=label if label else f"{lat:.6f}, {lon:.6f}",
        tooltip=label if label else "Selected study point",
    ).add_to(fmap)

    folium.Circle(
        location=[lat, lon],
        radius=100,
        color="#c0392b",
        weight=1.2,
        fill=True,
        fill_color="#c0392b",
        fill_opacity=0.07,
    ).add_to(fmap)

    return fmap


def build_results_table(results):
    rows = []
    for key, r in results.items():
        rows.append(
            {
                "Device": short_device_label(key),
                "Result": r["status"],
                "Engine": r["engine"],
                "PV (W)": r["pv"],
                "Battery (Wh)": r["batt"],
                "Power (W)": round(r["power"], 2),
                "Battery reserve (hrs)": round(calc_battery_reserve_hours(r), 1),
                "Fail months": ", ".join(r["fail_months"]) if r["fail_months"] else "—",
            }
        )
    return pd.DataFrame(rows)


def build_monthly_df(results, required_hrs):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)
        for i, month in enumerate(months):
            hours = float(r["hours"][i])
            diff = hours - float(required_hrs)
            rows.append(
                {
                    "Month": month,
                    "MonthIndex": i + 1,
                    "Device": label,
                    "Hours": hours,
                    "RequiredHours": float(required_hrs),
                    "Difference": diff,
                    "StatusBand": "Above requirement" if diff >= 0 else "Below requirement",
                    "FillTop": max(hours, float(required_hrs)),
                    "FillBottom": min(hours, float(required_hrs)),
                }
            )

    return pd.DataFrame(rows)


def calc_battery_reserve_hours(result_row):
    # User asked to explain battery energy reserve separately from solar feasibility.
    # Usable battery assumed at 70%.
    batt = float(result_row["batt"])
    power = max(float(result_row["power"]), 0.01)
    return batt * 0.70 / power


def recommendation_text(results, required_hrs):
    fail_rows = []
    for key, r in results.items():
        if r["status"] == "FAIL":
            fail_rows.append((short_device_label(key), r["fail_months"]))

    if not fail_rows:
        return (
            f"All selected configurations meet the required operating profile of "
            f"{required_hrs:.1f} hrs/day across the full annual cycle."
        )

    parts = []
    for device, fail_months in fail_rows:
        months = ", ".join(fail_months) if fail_months else "one or more months"
        parts.append(f"{device} fails in {months}")

    return (
        "Some selected configurations do not meet the required daily operating profile. "
        + "; ".join(parts)
        + ". Recommended next step: increase energy reserve, reduce power demand, "
          "or select a stronger Solar Engine / different device configuration."
    )


def checked_devices_summary(results):
    rows = []
    for key, r in results.items():
        label = short_device_label(key)
        if r["status"] == "PASS":
            comment = "Meets required operation all year"
        else:
            comment = f"Fails in {', '.join(r['fail_months'])}"
        rows.append({"Device": label, "Result": r["status"], "Comment": comment})
    return pd.DataFrame(rows)


def pvgis_short_card():
    st.markdown(
        """
        <div style="
            border:1px solid #d9e2ef;
            border-radius:14px;
            padding:12px 14px;
            background:#f8fbff;
            margin-top:4px;
            margin-bottom:8px;">
            <div style="font-weight:700; color:#12355b; margin-bottom:5px;">
                Powered by PVGIS
            </div>
            <div style="font-size:0.90rem; color:#475467; line-height:1.45;">
                <b>PVGIS — Photovoltaic Geographical Information System</b><br/>
                Joint Research Centre, European Commission<br/>
                Dataset: <b>PVGIS-SARAH3</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(text, ok=True):
    bg = "#0f9d58" if ok else "#c0392b"
    return f"""
    <div style="
        display:inline-block;
        padding:8px 14px;
        border-radius:999px;
        background:{bg};
        color:white;
        font-weight:700;
        font-size:14px;
        margin-top:6px;">
        {text}
    </div>
    """


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------
st.markdown(
    """
<style>
.block-container {
    padding-top: 0.85rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}
header[data-testid="stHeader"] {
    background: rgba(255,255,255,0);
}
.main-title {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.05;
    margin-bottom: 0.2rem;
    color: #1f2937;
}
.sub-title {
    font-size: 1rem;
    color: #6b7280;
    margin-bottom: 0.45rem;
}
.card {
    border: 1px solid #e8edf4;
    border-radius: 18px;
    padding: 16px 16px 12px 16px;
    background: #ffffff;
    box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
    margin-bottom: 14px;
}
.section-title {
    font-size: 1.12rem;
    font-weight: 800;
    margin-bottom: 10px;
    color: #1f2937;
}
.metric-box {
    border: 1px solid #edf1f7;
    border-radius: 14px;
    padding: 10px 12px;
    background: linear-gradient(180deg, #fbfdff 0%, #f6f9fc 100%);
    min-height: 78px;
}
.metric-label {
    color: #6b7280;
    font-size: 0.80rem;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.04rem;
    font-weight: 800;
    color: #1f2937;
}
.device-title {
    font-size: 1.08rem;
    font-weight: 800;
    margin-bottom: 0.15rem;
}
.engine-tag {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 999px;
    background: #eef4ff;
    color: #234ea5;
    font-size: 0.80rem;
    font-weight: 700;
    margin-top: 4px;
}
.builtin-tag {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 999px;
    background: #edf7ed;
    color: #1d7a43;
    font-size: 0.80rem;
    font-weight: 700;
    margin-top: 4px;
}
.field-note {
    color:#667085;
    font-size:0.87rem;
    margin-top:4px;
    line-height:1.4;
}
.map-note {
    color:#6b7280;
    font-size:0.90rem;
    margin-top:8px;
}
.log-box {
    border: 1px solid #e5eaf1;
    border-radius: 12px;
    padding: 10px 12px;
    background: #fbfcfe;
}
.cockpit-label {
    color:#667085;
    font-size:0.80rem;
    margin-bottom:2px;
}
.cockpit-value {
    font-weight:700;
    font-size:0.95rem;
    margin-bottom:8px;
}
.small-muted {
    color:#667085;
    font-size:0.85rem;
    line-height:1.4;
}
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    border-radius: 12px !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------
defaults = {
    "lat": 40.416775,
    "lon": -3.703790,
    "airport_label": "",
    "search_message": "",
    "map_click_info": "",
    "pdf_bytes": None,
    "pdf_name": "sala_standardized_feasibility_study.pdf",
    "results": None,
    "overall": None,
    "elapsed": None,
    "last_run_completed": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
c1, c2 = st.columns([1, 8])

with c1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=95)

with c2:
    st.markdown(
        '<div class="main-title">SALA Standardized Feasibility Study for Solar AGL</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-title">PVGIS-based annual feasibility workflow for Solar AGL, PAPI and A-PAPI systems</div>',
        unsafe_allow_html=True,
    )

# placeholders for top-run status / results
run_status_top = st.container()
result_summary_top = st.container()


# ---------------------------------------------------------
# Inputs
# ---------------------------------------------------------
left, right = st.columns([1.0, 1.0])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">1. Study setup</div>', unsafe_allow_html=True)

    a1, a2 = st.columns([1.4, 1.0])

    with a1:
        airport_query = st.text_input(
            "Airport name",
            value=st.session_state.airport_label,
            placeholder="e.g. Schiphol Airport, Radom Airport, Torreón Airport",
        )
    with a2:
        required_hours = st.number_input(
            "Required daily operation (hrs/day)",
            min_value=0.0,
            max_value=24.0,
            value=8.0,
            step=0.5,
            help=(
                "Total number of hours per day the system must operate. "
                "This may include multiple operating periods within a day."
            ),
        )

    st.markdown(
        '<div class="field-note"><b>Important:</b> this is the total number of hours per day the system must operate. '
        'It can include multiple periods (for example 06–08, 12–20, 22–02). '
        'It is not the same as battery autonomy and not the same as solar range.</div>',
        unsafe_allow_html=True,
    )

    a3, a4 = st.columns([1.2, 1.2])
    with a3:
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
                    st.session_state.search_message = "Airport not found. You can click the map or use Advanced coordinates."
                    st.rerun()
            except Exception as e:
                st.session_state.search_message = f"Search error: {e}"
                st.rerun()

    with a4:
        airport_label_for_report = st.text_input(
            "Airport label for report",
            value=st.session_state.airport_label
        )

    if st.session_state.search_message:
        if st.session_state.search_message.startswith("Found:"):
            st.success(st.session_state.search_message)
        else:
            st.warning(st.session_state.search_message)

    with st.expander("Advanced coordinates", expanded=False):
        c_lat, c_lon = st.columns(2)
        with c_lat:
            lat = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=float(st.session_state.lat),
                format="%.6f",
            )
        with c_lon:
            lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=float(st.session_state.lon),
                format="%.6f",
            )

        st.session_state.lat = lat
        st.session_state.lon = lon

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Exact study point</div>', unsafe_allow_html=True)

    selected_label = airport_label_for_report.strip() if airport_label_for_report.strip() else "Selected study point"
    fmap = create_map(st.session_state.lat, st.session_state.lon, selected_label)

    map_data = st_folium(
        fmap,
        width=None,
        height=430,
        returned_objects=["last_clicked"],
        key="study_map_v5",
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
        f'<div class="map-note"><b>Study point sent to PVGIS:</b> {st.session_state.lat:.6f}, {st.session_state.lon:.6f}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Devices selection
# ---------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">2. Select devices</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="small-muted">PAPI and A-PAPI are separate device types and should be selected independently.</div>',
    unsafe_allow_html=True,
)

device_options = {f"{k}. {v['code']} — {v['name']}": k for k, v in DEVICES.items()}
selected_labels = st.multiselect(
    "Devices included in this study",
    list(device_options.keys()),
    default=list(device_options.keys())[:2],
)
selected_ids = [device_options[label] for label in selected_labels]
st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Device configuration
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
                key=f"engine_mode_{did}",
            )

            compatible_engine_keys = dspec.get("compatible_engines", list(SOLAR_ENGINES.keys()))

            if engine_mode == "Use default Solar Engine":
                engine_key = default_engine_key
            else:
                engine_options = {
                    f"{SOLAR_ENGINES[k]['short_name']} — {SOLAR_ENGINES[k]['name']}": k
                    for k in compatible_engine_keys
                }
                value_list = list(engine_options.values())
                chosen_label = st.selectbox(
                    f"Choose Solar Engine for {dspec['code']}",
                    list(engine_options.keys()),
                    index=value_list.index(default_engine_key) if default_engine_key in value_list else 0,
                    key=f"engine_select_{did}",
                )
                engine_key = engine_options[chosen_label]

            eng = SOLAR_ENGINES[engine_key]
            engine_label = eng["short_name"]

            if eng.get("batt_ext"):
                battery_mode = st.radio(
                    f"Battery mode for {dspec['code']}",
                    options=["Std", "Ext"],
                    horizontal=True,
                    key=f"battery_mode_{did}",
                )
                batt_display = eng["batt_ext"] if battery_mode == "Ext" else eng["batt"]
            else:
                batt_display = eng["batt"]

            pv_display = eng["pv"]

        with t2:
            m1, m2, m3, m4 = st.columns(4)

            with m1:
                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-label">Default power</div>
                        <div class="metric-value">{default_power:.2f} W</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with m2:
                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-label">Solar panel</div>
                        <div class="metric-value">{pv_display} W</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with m3:
                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-label">Battery</div>
                        <div class="metric-value">{batt_display} Wh</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with m4:
                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-label">Active source</div>
                        <div class="metric-value">{engine_label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.write("")

        power_mode = st.radio(
            f"Power setup for {dspec['code']}",
            options=["Use default power", "Enter power manually"],
            horizontal=True,
            key=f"power_mode_{did}",
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
                key=f"manual_power_{did}",
            )

        per_device_config[did] = {
            "power": float(selected_power),
            "engine_key": engine_key,
            "battery_mode": battery_mode,
        }

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Compact cockpit sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## Study cockpit")

    st.markdown('<div class="cockpit-label">Airport</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="cockpit-value">{airport_label_for_report or airport_query or "Not defined"}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cockpit-label">Required daily operation</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cockpit-value">{required_hours:.1f} hrs/day</div>', unsafe_allow_html=True)

    st.markdown('<div class="cockpit-label">Devices selected</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cockpit-value">{len(selected_ids)}</div>', unsafe_allow_html=True)

    st.markdown("---")

    if os.path.exists(EU_LOGO_PATH):
        st.image(EU_LOGO_PATH, width=110)

    pvgis_short_card()

    with st.expander("About PVGIS-SARAH3", expanded=False):
        st.write(
            "PVGIS-SARAH3 is a satellite-based solar radiation dataset calculated by CM SAF "
            "to replace SARAH-2. It covers Europe, Africa, most of Asia, and parts of South America."
        )
        st.write(
            "SALA uses this independent dataset and the European Commission JRC PVGIS engine "
            "to build the feasibility assessment."
        )

    st.markdown("---")
    st.markdown("### Status")

    if st.session_state.results is None:
        st.info("Ready to run")
        run_clicked = st.button("Run simulation", type="primary", use_container_width=True)
    else:
        st.markdown(
            status_badge(f"Completed — {st.session_state.overall}", ok=(st.session_state.overall == "PASS")),
            unsafe_allow_html=True,
        )
        if st.session_state.elapsed is not None:
            st.write(f"**Run time:** {format_seconds(st.session_state.elapsed)}")
        run_clicked = False
        st.button("Simulation completed", disabled=True, use_container_width=True)

    if st.session_state.pdf_bytes is not None:
        st.download_button(
            "Download report",
            data=st.session_state.pdf_bytes,
            file_name=st.session_state.pdf_name,
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.button("Download report", disabled=True, use_container_width=True)


# ---------------------------------------------------------
# Run simulation
# ---------------------------------------------------------
if run_clicked:
    with run_status_top:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 4. Simulation in progress")

        pvgis_short_card()
        st.write(
            "The study is validating inputs, requesting solar/off-grid data from PVGIS, "
            "checking monthly performance, and building the annual feasibility result."
        )

        progress_bar = st.progress(0)
        progress_summary = st.empty()

        step_placeholders = [st.empty() for _ in range(5)]
        log_box = st.empty()
        live_log = []
        current_step = {"idx": 0}

        def render_steps(active_idx):
            step_labels = [
                "Step 1 — Validating study inputs",
                "Step 2 — Requesting PVGIS data",
                "Step 3 — Processing monthly off-grid results",
                "Step 4 — Checking annual requirement month by month",
                "Step 5 — Building final conclusion and report",
            ]

            for i, label in enumerate(step_labels):
                if i < active_idx:
                    step_placeholders[i].success(f"{label} — completed")
                elif i == active_idx:
                    step_placeholders[i].info(f"{label} — running")
                else:
                    step_placeholders[i].write(label)

        def add_log(message):
            live_log.append(f"**{now_ts()}** — {message}")
            visible = live_log[-5:]
            log_box.markdown(
                '<div class="log-box">' + "<br/>".join(visible) + "</div>",
                unsafe_allow_html=True,
            )

        def progress_callback(done, total, pct, elapsed, eta, device_name, month_name):
            percent = int(pct * 100)
            progress_bar.progress(min(percent, 100))
            progress_summary.markdown(
                f"**Progress:** {percent}%  \n"
                f"**Elapsed:** {format_seconds(elapsed)}  \n"
                f"**Estimated time left:** {format_seconds(eta)}"
            )

            if percent < 12:
                step_idx = 0
            elif percent < 30:
                step_idx = 1
            elif percent < 60:
                step_idx = 2
            elif percent < 85:
                step_idx = 3
            else:
                step_idx = 4

            if step_idx != current_step["idx"]:
                current_step["idx"] = step_idx
                render_steps(step_idx)

            short_name = short_device_label(device_name)

            if done == 1:
                add_log("Connecting to PVGIS — Photovoltaic Geographical Information System.")
                add_log("Using the Joint Research Centre, European Commission engine.")
            if month_name == "Jan":
                add_log(f"Starting annual assessment for {short_name}.")
            if month_name == "Jun":
                add_log(f"Reviewing mid-year off-grid performance for {short_name}.")
            if month_name == "Dec":
                add_log(f"Checking winter performance for {short_name}.")

        render_steps(0)
        add_log("Checking selected airport inputs.")
        add_log("Preparing PVGIS request parameters.")

        loc = {
            "lat": st.session_state.lat,
            "lon": st.session_state.lon,
            "label": airport_label_for_report.strip()
            if airport_label_for_report.strip()
            else f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
            "country": "",
        }

        started = time.time()

        try:
            results, overall, worst_name, worst_gap, slope = simulate_for_devices(
                loc=loc,
                required_hrs=required_hours,
                selected_ids=selected_ids,
                per_device_config=per_device_config,
                az_override=None,
                progress_callback=progress_callback,
            )

            elapsed = time.time() - started
            st.session_state.elapsed = elapsed
            st.session_state.results = results
            st.session_state.overall = overall

            progress_bar.progress(100)
            progress_summary.markdown(
                f"**Progress:** 100%  \n"
                f"**Elapsed:** {format_seconds(elapsed)}  \n"
                f"**Estimated time left:** 0s"
            )

            render_steps(5)
            add_log("PVGIS responses received for all selected configurations.")
            add_log("Preparing annual feasibility conclusion.")
            add_log("Generating consultant-style PDF report.")

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                make_pdf(
                    tmp.name,
                    loc,
                    required_hours,
                    results,
                    overall,
                    worst_name,
                    abs(worst_gap),
                    f"{round(slope)}°",
                    airport_label_for_report.strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    None,
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
# Results summary at the top
# ---------------------------------------------------------
if st.session_state.results is not None:
    results = st.session_state.results
    overall = st.session_state.overall

    with result_summary_top:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 5. Decision summary")

        c1, c2, c3, c4 = st.columns([1, 1.7, 2.2, 1.2])

        with c1:
            st.markdown("**Overall result**")
            st.markdown(status_badge(overall, ok=(overall == "PASS")), unsafe_allow_html=True)

        with c2:
            st.markdown("**Checked devices**")
            summary_df = checked_devices_summary(results)
            for _, row in summary_df.iterrows():
                icon = "🟢" if row["Result"] == "PASS" else "🔴"
                st.write(f"{icon} **{row['Device']}** — {row['Result']}")

        with c3:
            st.markdown("**What this means**")
            st.write(recommendation_text(results, required_hours))

        with c4:
            st.markdown("**Report**")
            if st.session_state.pdf_bytes is not None:
                st.download_button(
                    "Download report",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_name,
                    mime="application/pdf",
                    use_container_width=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Detailed results
# ---------------------------------------------------------
if st.session_state.results is not None:
    results = st.session_state.results

    # Battery reserve vs annual feasibility
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Battery reserve vs annual solar feasibility")
    st.markdown(
        '<div class="small-muted">'
        'Battery reserve is not the same as annual solar feasibility. '
        'Battery reserve shows how long the device can operate from stored battery energy only. '
        'Annual solar feasibility shows whether the system can maintain the required daily operation throughout the year.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    for device_name, r in results.items():
        d1, d2, d3 = st.columns([1.3, 1, 1])
        with d1:
            st.markdown(f"**{short_device_label(device_name)}**")
        with d2:
            st.metric("Battery reserve", f"{calc_battery_reserve_hours(r):.1f} hrs")
        with d3:
            st.metric("Annual solar check", r["status"])
    st.markdown('</div>', unsafe_allow_html=True)

    # Graph
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Annual operating profile")

    chart_df = build_monthly_df(results, required_hours)
    device_labels = list(chart_df["Device"].unique())

    visible_devices = st.multiselect(
        "Devices shown on graph",
        device_labels,
        default=device_labels,
        help="Untick devices to hide them from the graph.",
    )

    plot_df = chart_df[chart_df["Device"].isin(visible_devices)].copy()
    above_df = plot_df[plot_df["Hours"] >= plot_df["RequiredHours"]].copy()
    below_df = plot_df[plot_df["Hours"] < plot_df["RequiredHours"]].copy()

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    green_fill = alt.Chart(above_df).mark_area(
        color="#16a34a",
        opacity=0.17
    ).encode(
        x=alt.X("Month:N", sort=month_order, title="Month of the year (annual profile)"),
        y=alt.Y("FillTop:Q", scale=alt.Scale(domain=[0, 24]), title="Guaranteed operating hours per day"),
        y2="FillBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
        ],
    )

    red_fill = alt.Chart(below_df).mark_area(
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
            alt.Tooltip("StatusBand:N", title="Status"),
        ],
    )

    line_chart = alt.Chart(plot_df).mark_line(point=True, strokeWidth=2.8).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        color=alt.Color(
            "Device:N",
            title="Device",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="top-right"),
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
        ],
    )

    req_df = pd.DataFrame({
        "Month": month_order,
        "Required": [float(required_hours)] * 12,
        "Legend": [f"Required daily operation = {required_hours:.1f} hrs/day"] * 12,
    })

    req_line = alt.Chart(req_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=3.2
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Required:Q", title="Required hrs/day", format=".1f"),
            alt.Tooltip("Legend:N", title="Reference"),
        ],
    )

    # subtle highlighted band around required hours
    highlight_df = pd.DataFrame({
        "x1": [0],
        "x2": [1],
        "y1": [max(required_hours - 0.15, 0)],
        "y2": [min(required_hours + 0.15, 24)],
    })

    # easier: use rule only + strong caption, since band across categorical x is awkward in Altair
    chart = (green_fill + red_fill + line_chart + req_line).properties(height=470).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        '<div class="field-note"><b>How to read this graph:</b> '
        'Each coloured line is one selected device. '
        'The thick black dashed line is the required daily operation. '
        '<span style="color:#16a34a;"><b>Green fill</b></span> means the device is above the requirement in that month. '
        '<span style="color:#dc2626;"><b>Red fill</b></span> means it is below the requirement. '
        'The vertical scale is fixed from 0 to 24 hrs/day.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Checked devices table
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Checked devices")
    st.dataframe(build_results_table(results), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Monthly operating profile
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Monthly operating profile")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_rows = []
    for i, month in enumerate(months):
        row = {"Month": month, "Required hrs/day": required_hours}
        for name, r in results.items():
            row[short_device_label(name)] = round(r["hours"][i], 2)
        month_rows.append(row)
    st.dataframe(pd.DataFrame(month_rows), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # PVGIS transparency
    with st.expander("6. PVGIS transparency", expanded=False):
        pvgis_short_card()
        st.write(
            "SALA uses PVGIS as the external solar and off-grid calculation engine. "
            "PVGIS provides the solar and off-grid responses used to build the annual feasibility assessment."
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

    # Meaning of study inputs
    with st.expander("7. Meaning of study inputs", expanded=False):
        st.write(
            "**Location** defines the exact study point sent to PVGIS."
        )
        st.write(
            "**Required daily operation** defines the total number of hours per day the system must operate. "
            "This may include multiple periods within a day."
        )
        st.write(
            "**Power** defines the electrical load used in the feasibility assessment."
        )
        st.write(
            "**Battery reserve** shows how long the device can run from stored battery energy only."
        )
        st.write(
            "**Annual solar feasibility** shows whether the selected configuration can maintain the required daily operation throughout the year."
        )
        st.write(
            "**Solar Engine / Battery mode** defines the external power configuration for supported devices."
        )