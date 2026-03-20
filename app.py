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
            "Lowest-month difference (hrs)": round(r["min_margin"], 2),
            "Status": r["status"],
            "Fail months": ", ".join(r["fail_months"]) if r["fail_months"] else "-"
        })
    return pd.DataFrame(rows)


def build_chart_df(results, required_hrs):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows = []

    for device_name, r in results.items():
        for i, m in enumerate(months):
            rows.append({
                "Month": m,
                "Hours": round(r["hours"][i], 2),
                "Series": device_name
            })

    for m in months:
        rows.append({
            "Month": m,
            "Hours": required_hrs,
            "Series": "Required operating hours"
        })

    return pd.DataFrame(rows)


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


st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
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
.map-note {
    color:#6b7280;
    font-size:0.92rem;
    margin-top:8px;
}
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)


if "lat" not in st.session_state:
    st.session_state.lat = 40.416775
if "lon" not in st.session_state:
    st.session_state.lon = -3.703790
if "airport_label" not in st.session_state:
    st.session_state.airport_label = ""
if "search_message" not in st.session_state:
    st.session_state.search_message = ""


h1, h2 = st.columns([1, 8])

with h1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=95)

with h2:
    st.markdown('<div class="main-title">SALA Standardized Feasibility Study for Solar AGL</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Airport search, PVGIS-based transparency, manual/default power setup, solar engine selection, graph preview, PDF export</div>',
        unsafe_allow_html=True
    )


left, right = st.columns([1.05, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Location</div>', unsafe_allow_html=True)

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
            else:
                st.session_state.search_message = "Airport not found. Enter coordinates manually."
        except Exception as e:
            st.session_state.search_message = f"Search error: {e}"

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
            "Required operating hours/day",
            min_value=0.0,
            max_value=24.0,
            value=8.0,
            step=0.5
        )
    with c4:
        airport_name_for_report = st.text_input(
            "Airport label for report",
            value=st.session_state.airport_label
        )

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Map</div>', unsafe_allow_html=True)

    try:
        selected_label = airport_name_for_report.strip() if airport_name_for_report.strip() else "Selected airport"
        fmap = create_map(lat, lon, selected_label)
        st_folium(fmap, width=None, height=430, returned_objects=[])
        st.markdown(
            f'<div class="map-note"><b>Selected point:</b> {lat:.6f}, {lon:.6f}</div>',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.info(f"Map could not be displayed: {e}")

    st.markdown('</div>', unsafe_allow_html=True)


st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Select devices</div>', unsafe_allow_html=True)

device_options = {f"{k}. {v['code']} — {v['name']}": k for k, v in DEVICES.items()}
selected_labels = st.multiselect(
    "Choose devices to analyze",
    list(device_options.keys()),
    default=list(device_options.keys())[:2]
)
selected_ids = [device_options[x] for x in selected_labels]

st.markdown('</div>', unsafe_allow_html=True)


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
        default_engine = SOLAR_ENGINES[default_engine_key]
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


st.write("")
run = st.button("Run simulation", type="primary")

if run:
    if not selected_ids:
        st.error("Select at least one device.")
    else:
        loc = {
            "lat": lat,
            "lon": lon,
            "label": airport_name_for_report.strip() if airport_name_for_report.strip() else f"{lat:.4f}, {lon:.4f}",
            "country": ""
        }

        progress_bar = st.progress(0)
        progress_text = st.empty()
        current_step_text = st.empty()

        def on_progress(done, total, pct, elapsed, eta, device_name, month_name):
            percent_value = int(pct * 100)
            progress_bar.progress(min(percent_value, 100))
            progress_text.markdown(
                f"**Progress:** {percent_value}%  \n"
                f"**Elapsed:** {format_seconds(elapsed)}  \n"
                f"**Time left:** {format_seconds(eta)}"
            )
            current_step_text.caption(f"Now calculating: {device_name} • {month_name}")

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

            progress_bar.progress(100)
            total_time = time.time() - started
            progress_text.markdown(
                f"**Progress:** 100%  \n"
                f"**Elapsed:** {format_seconds(total_time)}  \n"
                f"**Time left:** 0s"
            )
            current_step_text.caption("Simulation completed.")

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
                st.caption(f"Gap vs requirement: {round(abs(worst_gap), 2)} hrs")
                st.markdown('</div>', unsafe_allow_html=True)

            with r3:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("**Location**")
                st.markdown(f"**{loc['label']}**")
                st.caption(f"{lat:.6f}, {lon:.6f}")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Results graph")

            chart_df = build_chart_df(results, required_hrs)
            chart = alt.Chart(chart_df).mark_line(point=True).encode(
                x=alt.X("Month:N", sort=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]),
                y=alt.Y("Hours:Q", title="Autonomy (hours/day)"),
                color=alt.Color("Series:N", title="Series"),
                tooltip=["Series:N", "Month:N", "Hours:Q"]
            ).properties(height=420)

            st.altair_chart(chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Results table")
            df = build_results_table(results)
            st.dataframe(df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Monthly autonomy")
            month_rows = []
            months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            for i, m in enumerate(months):
                row = {"Month": m, "Required hrs": required_hrs}
                for name, r in results.items():
                    row[name] = round(r["hours"][i], 2)
                month_rows.append(row)
            st.dataframe(pd.DataFrame(month_rows), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### PVGIS transparency")
            st.write(
                "This tool does **not replace PVGIS with an internal solar model**. "
                "It sends selected inputs to PVGIS endpoints, retrieves the responses, "
                "and then SALA organizes them into a device-level feasibility assessment."
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

                    st.info(meta["explanation"])

            st.markdown('</div>', unsafe_allow_html=True)

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
                    st.download_button(
                        "Download PDF report",
                        f,
                        file_name="sala_standardized_feasibility_study.pdf",
                        mime="application/pdf"
                    )

        except Exception as e:
            st.error(f"Simulation failed: {e}")