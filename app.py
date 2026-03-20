import streamlit as st
import tempfile
from devices import DEVICES
from simulate import simulate_for_devices
from report import make_pdf

st.title("S4GA Solar Feasibility Simulator")

airport = st.text_input("Airport name")
lat = st.number_input("Latitude", format="%.6f")
lon = st.number_input("Longitude", format="%.6f")
required_hrs = st.number_input("Required operating hours/day", min_value=0.0, max_value=24.0, value=8.0)

device_options = {f"{k}. {v['name']}": k for k, v in DEVICES.items()}
selected_labels = st.multiselect("Select devices", list(device_options.keys()))
selected_ids = [device_options[x] for x in selected_labels]

if st.button("Run simulation"):
    if not selected_ids:
        st.error("Select at least one device")
    else:
        loc = {
            "lat": lat,
            "lon": lon,
            "label": airport or f"{lat:.4f}, {lon:.4f}",
            "country": ""
        }

        results, overall, worst_name, worst_gap, slope = simulate_for_devices(
            loc=loc,
            required_hrs=required_hrs,
            selected_ids=selected_ids,
            batt_mode_by_engine={},
            power_override={},
            az_override=None
        )

        st.write("### Results")
        st.write(results)

        st.write("### Overall result")
        st.success(overall)

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
                airport,
                "Auto-generated",
                None
            )

            with open(tmp.name, "rb") as f:
                st.download_button(
                    "Download PDF Report",
                    f,
                    file_name="solar_report.pdf"
                )