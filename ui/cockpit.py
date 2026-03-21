# ui/cockpit.py
# ACTION: REPLACE ENTIRE FILE

import os
import time
import tempfile
from datetime import datetime

import streamlit as st

from core.simulate import simulate_for_devices
from report.report import make_pdf

EU_LOGO_PATH = "logo_en.gif"


# ---------------- HELPERS ----------------

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


def reset_study():
    keep = {
        "airport_label": st.session_state.get("airport_label", ""),
        "lat": st.session_state.get("lat", 40.416775),
        "lon": st.session_state.get("lon", -3.703790),
        "required_hours": st.session_state.get("required_hours", 8.0),
        "selected_ids": st.session_state.get("selected_ids", []),
        "per_device_config": st.session_state.get("per_device_config", {}),
        "search_message": st.session_state.get("search_message", ""),
        "map_click_info": st.session_state.get("map_click_info", ""),
    }

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    for k, v in keep.items():
        st.session_state[k] = v

    st.session_state.results = None
    st.session_state.overall = None
    st.session_state.pdf_bytes = None
    st.session_state.pdf_name = "sala_standardized_feasibility_study.pdf"
    st.session_state.elapsed = None

    st.rerun()


def _run_simulation():
    st.session_state.running = True
    st.session_state.run_progress = 0
    st.session_state.run_stage = "Starting simulation"
    st.session_state.run_log = []

    progress_host = st.container()

    with progress_host:
        st.markdown("## Simulation in progress")
        st.write(
            "The study is validating inputs, requesting solar/off-grid data from PVGIS, "
            "checking monthly performance and building the annual feasibility result."
        )

        progress_bar = st.progress(0)
        progress_text = st.empty()
        stage_text = st.empty()
        log_box = st.empty()

        def add_log(message):
            logs = st.session_state.get("run_log", [])
            logs.append(f"**{now_ts()}** — {message}")
            st.session_state.run_log = logs[-5:]
            log_box.markdown(
                '<div style="border:1px solid #e5eaf1;border-radius:12px;padding:10px 12px;background:#fbfcfe;">'
                + "<br/>".join(st.session_state.run_log)
                + "</div>",
                unsafe_allow_html=True,
            )

        def render_stage(percent):
            if percent < 12:
                return "Step 1 — Validating study inputs"
            elif percent < 30:
                return "Step 2 — Requesting PVGIS data"
            elif percent < 60:
                return "Step 3 — Processing monthly off-grid results"
            elif percent < 85:
                return "Step 4 — Checking annual requirement month by month"
            return "Step 5 — Building final conclusion and report"

        add_log("Checking selected airport inputs.")
        add_log("Preparing PVGIS request parameters.")

        loc = {
            "lat": st.session_state.lat,
            "lon": st.session_state.lon,
            "label": st.session_state.airport_label or f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
            "country": "",
        }

        started = time.time()

        def progress_callback(done, total, pct, elapsed, eta, device_name, month_name):
            percent = int(pct * 100)
            st.session_state.run_progress = percent
            st.session_state.run_stage = render_stage(percent)

            progress_bar.progress(min(percent, 100))
            progress_text.markdown(
                f"**Running:** {percent}%  \n"
                f"**Elapsed:** {format_seconds(elapsed)}  \n"
                f"**Estimated time left:** {format_seconds(eta)}"
            )
            stage_text.info(st.session_state.run_stage)

            if done == 1:
                add_log("Connecting to PVGIS — Photovoltaic Geographical Information System.")
                add_log("Using the Joint Research Centre, European Commission engine.")
            if month_name == "Jan":
                add_log(f"Starting annual assessment for {device_name}.")
            if month_name == "Jun":
                add_log(f"Reviewing mid-year off-grid performance for {device_name}.")
            if month_name == "Dec":
                add_log(f"Checking winter performance for {device_name}.")

        results, overall, worst_name, worst_gap, slope = simulate_for_devices(
            loc=loc,
            required_hrs=st.session_state.required_hours,
            selected_ids=st.session_state.selected_ids,
            per_device_config=st.session_state.per_device_config,
            az_override=None,
            progress_callback=progress_callback,
        )

        elapsed = time.time() - started

        st.session_state.results = results
        st.session_state.overall = overall
        st.session_state.elapsed = elapsed
        st.session_state.running = False
        st.session_state.run_progress = 100
        st.session_state.run_stage = "Completed"

        add_log("PVGIS responses received for all selected configurations.")
        add_log("Preparing annual feasibility conclusion.")
        add_log("Generating consultant-style PDF report.")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            make_pdf(
                tmp.name,
                loc,
                st.session_state.required_hours,
                results,
                overall,
                worst_name,
                abs(worst_gap),
                f"{round(slope)}°",
                st.session_state.airport_label,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                None,
            )
            with open(tmp.name, "rb") as f:
                st.session_state.pdf_bytes = f.read()

        st.success("Simulation completed successfully.")
        st.rerun()


# ---------------- MAIN COCKPIT ----------------

def render_cockpit():
    if "running" not in st.session_state:
        st.session_state.running = False
    if "run_progress" not in st.session_state:
        st.session_state.run_progress = 0
    if "run_stage" not in st.session_state:
        st.session_state.run_stage = "Ready"
    if "run_log" not in st.session_state:
        st.session_state.run_log = []

    with st.sidebar:
        st.markdown("## Study cockpit")

        st.markdown("**Airport**")
        st.write(st.session_state.get("airport_label", "") or "Not defined")

        st.markdown("**Planned daily operating hours**")
        st.write(f"{float(st.session_state.get('required_hours', 8.0)):.1f} hrs/day")

        st.markdown("**Devices selected**")
        st.write(len(st.session_state.get("selected_ids", [])))

        st.markdown("---")
        st.markdown("### Controls")

        # Running state
        if st.session_state.running:
            st.button(
                f"Running… {st.session_state.run_progress}%",
                disabled=True,
                use_container_width=True,
            )
            st.info(st.session_state.run_stage)

        # Fresh / not yet run
        elif st.session_state.get("results") is None:
            if st.button("Run simulation", type="primary", use_container_width=True):
                _run_simulation()

        # Completed
        else:
            if st.session_state.overall == "PASS":
                st.success("Completed — PASS")
            else:
                st.error("Completed — FAIL")

            if st.session_state.elapsed is not None:
                st.write(f"Run time: {format_seconds(st.session_state.elapsed)}")

            if st.button("Start new study", use_container_width=True):
                reset_study()

        if st.session_state.get("pdf_bytes") is not None:
            st.download_button(
                "Download report",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.get("pdf_name", "sala_standardized_feasibility_study.pdf"),
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("Download report", disabled=True, use_container_width=True)

        st.markdown("---")

        if os.path.exists(EU_LOGO_PATH):
            st.image(EU_LOGO_PATH, width=110)

        pvgis_short_card()

        with st.expander("About PVGIS-SARAH3", expanded=False):
            st.write(
                "PVGIS-SARAH3 is a satellite-based solar radiation dataset used in PVGIS. "
                "It covers Europe, Africa, most of Asia, and parts of South America."
            )
            st.write(
                "SALA uses this independent dataset and the European Commission JRC PVGIS engine "
                "to build the feasibility assessment."
            )
