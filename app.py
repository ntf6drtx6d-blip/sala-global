import os
import time
import tempfile
import requests
import pandas as pd
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
            "Tilt": r["tilt"],
            "Azimuth": round(r["azim"], 1),
            "Lowest-month difference (hrs)": round(r["min_margin"], 2),
            "Status": r["status"],
            "Fail months": ", ".join(r["fail_months"]) if r["fail_months"] else "-",
            "Power (W)": r["power"],
        })
    return pd.DataFrame(rows)

if os.path.exists(LOGO_PATH):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image(LOGO_PATH, width=260)

st.title("Solar Feasibility Simulator")
st.caption("Airport name or manual coordinates • map preview • PDF export")

if "lat" not in st.session_state:
    st.session_state.lat = 0.0
if "lon" not in st.session_state:
    st.session_state.lon = 0.0
if "airport_label" not in st.session_state:
    st.session_state.airport_label = ""
if "location_found" not in st.session_state:
    st.session_state.location_found = False

left, right = st.columns([1, 1])

with left:
    st.subheader("Location")

    airport_query = st.text_input(
        "Airport name",
        value=st.session_state.airport_label,
        placeholder="e.g. Logroño Airport or Torreón Airport"
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Find airport"):
            try:
                result = geocode_airport(airport_query)
                if result:
                    st.session_state.lat = result["lat"]
                    st.session_state.lon = result["lon"]
                    st.session_state.airport_label = airport_query.strip() or result["display_name"]
                    st.session_state.location_found = True
                    st.success(f"Found: {result['display_name']}")
                else:
                    st.session_state.location_found = False
                    st.error("Airport not found. Enter coordinates manually.")
            except Exception as e:
                st.session_state.location_found = False
                st.error(f"Search error: {e}")

    lat = st.number_input("Latitude", format="%.6f", value=float(st.session_state.lat))
    lon = st.number_input("Longitude", format="%.6f", value=float(st.session_state.lon))
    required_hrs = st.number_input(
        "Required operating hours/day",
        min_value=0.0,
        max_value=24.0,
        value=8.0,
        step=0.5
    )

    airport_name_for_report = st.text_input(
        "Airport label for report",
        value=st.session_state.airport_label
    )

with right:
    st.subheader("Map")
    try:
        map_df = pd.DataFrame([{"lat": lat, "lon": lon}])
        st.map(map_df, zoom=6)
    except Exception:
        st.info("Map will appear after valid coordinates are entered.")

st.subheader("Devices")

device_options = {f"{k}. {v['name']}": k for k, v in DEVICES.items()}
selected_labels = st.multiselect(
    "Select devices",
    list(device_options.keys()),
    default=list(device_options.keys())[:3]
)
selected_ids = [device_options[x] for x in selected_labels]

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
                batt_mode_by_engine={},
                power_override={},
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

            st.subheader("Overall result")
            if overall == "PASS":
                st.success("PASS")
            else:
                st.error("FAIL")

            st.subheader("Results table")
            df = build_results_table(results)
            st.dataframe(df, use_container_width=True)

            st.subheader("Monthly autonomy")
            month_rows = []
            months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            for i, m in enumerate(months):
                row = {"Month": m, "Required hrs": required_hrs}
                for name, r in results.items():
                    row[name] = round(r["hours"][i], 2)
                month_rows.append(row)
            st.dataframe(pd.DataFrame(month_rows), use_container_width=True)

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
                    "Auto-generated",
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