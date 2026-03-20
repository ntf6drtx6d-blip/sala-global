import os
import time
import tempfile
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from devices import DEVICES
from simulate import simulate_for_devices
from report import make_pdf

st.set_page_config(page_title="SALA Solar Feasibility Simulator", layout="wide")

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


def build_results_table(results):
    rows = []
    for name, r in results.items():
        rows.append({
            "Device": name,
            "Engine": r["engine"],
            "PV (W)": r["pv"],
            "Battery (Wh)": r["batt"],
            "Power (W)": r["power"],
            "Tilt": r["tilt"],
            "Azimuth": round(r["azim"], 1),
            "Lowest-month difference (hrs)": round(r["min_margin"], 2),
            "Status": r["status"],
            "Fail months": ", ".join(r["fail_months"]) if r["fail_months"] else "-"
        })
    return pd.DataFrame(rows)


def get_device_battery_options(dspec):
    options = [("Std", dspec["batt"])]
    if "batt_ext" in dspec:
        options.append(("Ext", dspec["batt_ext"]))
    return options


def status_badge(text, ok=True):
    bg = "#0f9d58" if ok else "#d93025"
    return f"""
    <div style="
        display:inline-block;
        padding:6px 12px;
        border-radius:999px;
        background:{bg};
        color:white;
        font-weight:600;
        font-size:14px;
        margin-top:4px;
    ">
        {text}
    </div>
    """


# ---------- style ----------
st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
.card {
    border: 1px solid #e9edf3;
    border-radius: 18px;
    padding: 18px 18px 14px 18px;
    background: #ffffff;
    box-shadow: 0 2px 10px rgba(18, 38, 63, 0.04);
    margin-bottom: 14px;
}
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 8px;
}
.small-muted {
    color: #6b7280;
    font-size: 0.92rem;
}
.metric-box {
    border: 1px solid #edf1f7;
    border-radius: 14px;
    padding: 10px 12px;
    background: #fafcff;
    min-height: 76px;
}
.metric-label {
    color: #6b7280;
    font-size: 0.82rem;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.05rem;
    font-weight: 700;
}
.header-wrap {
    display:flex;
    align-items:center;
    gap:16px;
    margin-bottom: 8px;
}
.header-title {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
    margin: 0;
}
.header-subtitle {
    color:#6b7280;
    margin-top: 4px;
    font-size: 0.96rem;
}
</style>
""", unsafe_allow_html=True)


# ---------- session ----------
if "lat" not in st.session_state:
    st.session_state.lat = 0.0
if "lon" not in st.session_state:
    st.session_state.lon = 0.0
if "airport_label" not in st.session_state:
    st.session_state.airport_label = ""


# ---------- header ----------
logo_col, title_col = st.columns([1, 8])

with logo_col:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=95)

with title_col:
    st.markdown("""
    <div class="header-wrap">
        <div>
            <div class="header-title">Solar Feasibility Simulator</div>
            <div class="header-subtitle">Airport search, map preview, custom power setup, battery mode selection, PDF export</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("")


# ---------- top layout ----------
left, right = st.columns([1.1, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Location</div>', unsafe_allow_html=True)

    airport_query = st.text_input(
        "Airport name",
        value=st.session_state.airport_label,
        placeholder="e.g. Schiphol Airport or Torreón Airport"
    )

    if st.button("Find airport"):
        try:
            result = geocode_airport(airport_query)
            if result:
                st.session_state.lat = result["lat"]
                st.session_state.lon = result["lon"]
                st.session_state.airport_label = airport_query.strip() or result["display_name"]
                st.success(f"Found: {result['display_name']}")
            else:
                st.error("Airport not found. Enter coordinates manually.")
        except Exception as e:
            st.error(f"Search error: {e}")

    col_a, col_b = st.columns(2)
    with col_a:
        lat = st.number_input("Latitude", format="%.6f", value=float(st.session_state.lat))
    with col_b:
        lon = st.number_input("Longitude", format="%.6f", value=float(st.session_state.lon))

    st.session_state.lat = lat
    st.session_state.lon = lon

    col_c, col_d = st.columns(2)
    with col_c:
        required_hrs = st.number_input(
            "Required operating hours/day",
            min_value=0.0,
            max_value=24.0,
            value=8.0,
            step=0.5
        )
    with col_d:
        airport_name_for_report = st.text_input(
            "Airport label for report",
            value=st.session_state.airport_label
        )

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Map</div>', unsafe_allow_html=True)
    try:
        map_df = pd.DataFrame([{"lat": lat, "lon": lon}])
        st.map(map_df, zoom=7)
        st.caption(f"Selected point: {lat:.6f}, {lon:.6f}")
    except Exception:
        st.info("Map will appear after valid coordinates are entered.")
    st.markdown('</div>', unsafe_allow_html=True)


# ---------- device selection ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Select devices</div>', unsafe_allow_html=True)

device_options = {f"{k}. {v['name']}": k for k, v in DEVICES.items()}
selected_labels = st.multiselect(
    "Choose devices to analyze",
    list(device_options.keys()),
    default=list(device_options.keys())[:2]
)
selected_ids = [device_options[x] for x in selected_labels]

st.markdown('</div>', unsafe_allow_html=True)


# ---------- device config cards ----------
batt_mode_by_engine = {}
power_override = {}

if selected_ids:
    st.markdown('<div class="section-title">Device configuration</div>', unsafe_allow_html=True)

for did in selected_ids:
    dspec = DEVICES[did]
    device_name = dspec["name"]
    engine_name = dspec["engine"]
    default_power = float(dspec["power"])
    pv = dspec["pv"]
    batt_std = dspec["batt"]
    has_ext = "batt_ext" in dspec
    batt_ext = dspec.get("batt_ext")

    st.markdown('<div class="card">', unsafe_allow_html=True)

    top1, top2 = st.columns([2, 3])

    with top1:
        st.markdown(f"### {did}. {device_name}")
        st.markdown(f'<div class="small-muted">Engine: {engine_name}</div>', unsafe_allow_html=True)

    with top2:
        m1, m2, m3 = st.columns(3)
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
                <div class="metric-label">Solar panel</div>
                <div class="metric-value">{pv} W</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            batt_text = f"{batt_std} Wh"
            if has_ext:
                batt_text += f" / {batt_ext} Wh"
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Battery</div>
                <div class="metric-value">{batt_text}</div>
            </div>
            """, unsafe_allow_html=True)

    cfg1, cfg2 = st.columns([1.2, 1])

    with cfg1:
        use_default = st.checkbox(
            f"Use default power for {did}",
            value=True,
            key=f"use_default_power_{did}"
        )

        if use_default:
            power_override[did] = default_power
            st.caption(f"Using default power: {default_power:.2f} W")
        else:
            manual_power = st.number_input(
                f"Manual power for {did} (W)",
                min_value=0.01,
                value=float(default_power),
                step=0.01,
                key=f"manual_power_{did}"
            )
            power_override[did] = float(manual_power)

    with cfg2:
        if has_ext:
            batt_mode = st.radio(
                f"Battery mode for {engine_name}",
                options=["Std", "Ext"],
                horizontal=True,
                key=f"battery_mode_{did}"
            )
            batt_mode_by_engine[engine_name] = batt_mode
            selected_batt = batt_std if batt_mode == "Std" else batt_ext
            st.caption(f"Selected battery: {selected_batt} Wh")
        else:
            batt_mode_by_engine[engine_name] = "Std"
            st.caption(f"Battery mode: Standard ({batt_std} Wh)")

    st.markdown('</div>', unsafe_allow_html=True)


# ---------- run ----------
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
                batt_mode_by_engine=batt_mode_by_engine,
                power_override=power_override,
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
            res1, res2, res3 = st.columns([1, 1, 2])

            with res1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("**Overall result**")
                st.markdown(status_badge(overall, ok=(overall == "PASS")), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with res2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("**Worst-case device**")
                st.markdown(f"**{worst_name}**")
                st.caption(f"Gap vs requirement: {round(abs(worst_gap), 2)} hrs")
                st.markdown('</div>', unsafe_allow_html=True)

            with res3:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("**Location**")
                st.markdown(f"**{loc['label']}**")
                st.caption(f"{lat:.6f}, {lon:.6f}")
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

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                make_pdf(
                    tmp.name,
                    loc,
                    required_hrs,
                    results,
                    overall,
                    worst_name,
                    abs(worst_gap),
                    "varies",
                    airport_name_for_report.strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    None
                )

                with open(tmp.name, "rb") as f:
                    st.download_button(
                        "Download PDF report",
                        f,
                        file_name="solar_report.pdf",
                        mime="application/pdf"
                    )

        except Exception as e:
            st.error(f"Simulation failed: {e}")