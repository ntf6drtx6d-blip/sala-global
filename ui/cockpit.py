# ui/cockpit.py
# ACTION: REPLACE ENTIRE FILE

import os
import time
import tempfile
from datetime import datetime

import streamlit as st

from core.simulate import simulate_for_devices
from core.devices import DEVICES
from report.report import make_pdf

EU_LOGO_PATH = "logo_en.gif"


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


def short_device_label_from_id(device_id):
    try:
        d = DEVICES[device_id]
        return d.get("code", str(device_id))
    except Exception:
        return str(device_id)


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
        "airport_label": "",
        "airport_query": "",
        "lat": st.session_state.get("lat", 40.416775),
        "lon": st.session_state.get("lon", -3.703790),
        "required_hours": 12.0,
        "operating_profile_mode": "Custom hours per day",
        "selected_ids": [],
        "per_device_config": {},
        "search_message": "",
        "map_click_info": "",
        "study_point_confirmed": False,
        "study_ready": False,
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
    st.session_state.running = False
    st.session_state.run_progress = 0
    st.session_state.run_stage = "Ready"
    st.session_state.run_log = []
    st.session_state.trigger_run = False

    st.rerun()


def _run_simulation():
    st.session_state.running = True
    st.session_state.run_stage = "Preparing simulation"
    st.session_state.run_log = []

    def add_log(message):
        logs = st.session_state.get("run_log", [])
        logs.append(f"**{now_ts()}** — {message}")
        st.session_state.run_log = logs[-5:]

    def render_stage(percent):
        if percent < 12:
            return "Validating study inputs"
        elif percent < 30:
            return "Requesting PVGIS data"
        elif percent < 60:
            return "Processing monthly off-grid results"
        elif percent < 85:
            return "Checking annual requirement month by month"
        return "Building final conclusion and report"

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
            "",
            0,
            "",
            st.session_state.airport_label,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            None,
        )
        with open(tmp.name, "rb") as f:
            st.session_state.pdf_bytes = f.read()

    st.rerun()


def render_cockpit():
    if "running" not in st.session_state:
        st.session_state.running = False
    if "run_stage" not in st.session_state:
        st.session_state.run_stage = "Ready"
    if "run_log" not in st.session_state:
        st.session_state.run_log = []
    if "study_ready" not in st.session_state:
        st.session_state.study_ready = False

    with st.sidebar:
        st.markdown("## Feasibility dashboard")

        st.markdown("**Airport**")
        st.write(st.session_state.get("airport_label", "") or "Not selected")

        st.markdown("**Operating profile**")
        st.write(st.session_state.get("operating_profile_mode", "Custom hours per day"))

        st.markdown("**Applied daily operation**")
        st.write(f"{float(st.session_state.get('required_hours', 12.0)):.1f} hrs/day")

        st.markdown("**Selected devices**")
        selected_ids = st.session_state.get("selected_ids", [])
        if selected_ids:
            for did in selected_ids:
                st.write(f"• {short_device_label_from_id(did)}")
        else:
            st.write("No devices selected")

        st.markdown("---")
        st.markdown("### Simulation")

        if st.session_state.running:
            st.markdown("**Simulation in progress**")
            st.caption(st.session_state.run_stage)

        elif st.session_state.get("results") is None:
            ready = bool(st.session_state.get("study_ready", False))

            if st.button(
                "Run simulation",
                type="primary",
                use_container_width=True,
                disabled=not ready
            ):
                st.session_state.running = True
                st.session_state.run_stage = "Preparing simulation"
                st.session_state.trigger_run = True
                st.rerun()

            if not ready:
                st.caption("To start the study, select an airport or study point and at least one device.")

        else:
            st.success("Simulation completed")
            if st.session_state.overall == "PASS":
                st.markdown("**Feasibility result:** PASS")
            else:
                st.markdown("**Feasibility result:** FAIL")

            if st.session_state.elapsed is not None:
                st.write(f"Run time: {format_seconds(st.session_state.elapsed)}")

        if st.session_state.running and st.session_state.run_log:
            st.markdown("---")
            st.markdown("### Live status")
            st.markdown(
                '<div style="border:1px solid #e5eaf1;border-radius:12px;padding:10px 12px;background:#fbfcfe;">'
                + "<br/>".join(st.session_state.run_log[-5:])
                + "</div>",
                unsafe_allow_html=True,
            )

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
