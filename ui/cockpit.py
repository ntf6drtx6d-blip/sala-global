
import os
import time
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

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
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%H:%M:%S")


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
    auth_keys = {
        "auth_ok": st.session_state.get("auth_ok", False),
        "auth_user_id": st.session_state.get("auth_user_id"),
        "auth_email": st.session_state.get("auth_email"),
        "auth_role": st.session_state.get("auth_role"),
        "auth_full_name": st.session_state.get("auth_full_name"),
    }

    keep = {
        "airport_label": "",
        "airport_query": "",
        "lat": st.session_state.get("lat", 40.416775),
        "lon": st.session_state.get("lon", -3.703790),
        "required_hours": 12.0,
        "operating_profile_mode": "Custom hours per day",
        "selected_ids": [],
        "selected_simulation_keys": [],
        "per_device_config": {},
        "search_message": "",
        "map_click_info": "",
        "study_point_confirmed": False,
        "study_ready": False,
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "sala_standardized_feasibility_study.pdf",
        "elapsed": None,
        "running": False,
        "run_progress": 0,
        "run_stage": "Ready",
        "run_log": [],
        "trigger_run": False,
        "study_saved_for_current_result": False,
    }

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    for k, v in auth_keys.items():
        st.session_state[k] = v
    for k, v in keep.items():
        st.session_state[k] = v

    st.rerun()


def _run_simulation(progress_callback=None):
    st.session_state.running = True
    st.session_state.run_stage = "Preparing simulation"
    st.session_state.run_progress = 0
    st.session_state.run_log = []

    def add_log(message):
        logs = st.session_state.get("run_log", [])
        logs.append(f"**{now_ts()}** — {message}")
        st.session_state.run_log = logs[-5:]

    def render_stage(percent):
        if percent < 10:
            return "Validating study inputs"
        elif percent < 25:
            return "Preparing PVGIS requests"
        elif percent < 45:
            return "Requesting solar and off-grid data from PVGIS"
        elif percent < 70:
            return "Checking monthly performance"
        elif percent < 90:
            return "Calculating annual feasibility"
        return "Generating results"

    def push_progress(percent, stage):
        percent = max(0, min(100, int(percent)))
        st.session_state.run_progress = percent
        st.session_state.run_stage = stage
        if progress_callback:
            progress_callback(percent, stage)

    add_log("Checking selected airport inputs.")
    push_progress(5, "Validating study inputs")

    add_log("Preparing PVGIS request parameters.")
    push_progress(12, "Preparing PVGIS requests")

    loc = {
        "lat": st.session_state.lat,
        "lon": st.session_state.lon,
        "label": st.session_state.airport_label or f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
        "country": st.session_state.get("airport_country", ""),
    }

    started = time.time()

    def simulation_progress(done, total, pct, elapsed, eta, device_name, month_name):
        percent = int(pct * 100)
        stage = render_stage(percent)

        push_progress(percent, stage)

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
        selected_ids=st.session_state.get("selected_simulation_keys") or st.session_state.selected_ids,
        per_device_config=st.session_state.per_device_config,
        az_override=None,
        progress_callback=simulation_progress,
    )

    elapsed = time.time() - started

    push_progress(92, "Calculating annual feasibility")
    add_log("PVGIS responses received for all selected configurations.")
    add_log("Preparing annual feasibility conclusion.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    make_pdf(
        results=results,
        overall=overall,
        airport_label=st.session_state.airport_label,
        created_at=datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M"),
        author_name=st.session_state.get("auth_full_name") or st.session_state.get("auth_email", ""),
        required_hours=st.session_state.required_hours,
        output_path=tmp_path,
        lat=st.session_state.lat,
        lon=st.session_state.lon,
        selected_ids=st.session_state.get("selected_simulation_keys") or st.session_state.selected_ids,
    )

    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    push_progress(100, "Generating results")
    add_log("Simulation complete.")
    add_log(f"Total elapsed time: {format_seconds(elapsed)}.")

    st.session_state.results = results
    st.session_state.overall = overall
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_name = "sala_standardized_feasibility_study.pdf"
    st.session_state.elapsed = elapsed
    st.session_state.running = False
    st.session_state.trigger_run = False
    st.session_state.run_stage = "Completed"
    st.rerun()
