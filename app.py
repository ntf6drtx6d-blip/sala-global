# app.py
# ACTION: REPLACE ENTIRE FILE

import os
import streamlit as st

from ui.setup import render_setup
from ui.cockpit import _run_simulation, reset_study
from ui.result import render_result
from ui.graph import render_graph
from ui.battery import render_battery_section
from ui.weather_basis import render_weather_basis


st.set_page_config(
    page_title="SALA Standardized Feasibility Study for Solar AGL",
    layout="wide"
)

LOGO_PATH = "sala_logo.png"


def init_state():
    defaults = {
        "airport_label": "",
        "airport_query": "",
        "lat": 40.416775,
        "lon": -3.703790,
        "required_hours": 12.0,
        "operating_profile_mode": "Custom hours per day",
        "selected_ids": [],
        "per_device_config": {},
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "sala_standardized_feasibility_study.pdf",
        "elapsed": None,
        "search_message": "",
        "map_click_info": "",
        "running": False,
        "run_progress": 0.0,
        "run_stage": "Ready",
        "run_log": [],
        "trigger_run": False,
        "study_point_confirmed": False,
        "study_ready": False,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def refresh_study_ready_from_state():
    selected_ids = st.session_state.get("selected_ids", [])
    study_point_confirmed = bool(st.session_state.get("study_point_confirmed", False))
    mode = st.session_state.get("operating_profile_mode")
    required_hours = st.session_state.get("required_hours")

    mode_ready = False
    if mode == "24/7":
        mode_ready = True
    elif mode == "Dusk to dawn":
        mode_ready = required_hours is not None
    elif mode == "Custom hours per day":
        mode_ready = required_hours is not None and float(required_hours) > 0

    st.session_state.study_ready = bool(
        len(selected_ids) > 0 and study_point_confirmed and mode_ready
    )


def apply_global_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        header[data-testid="stHeader"] {
            background: rgba(255,255,255,0);
        }

        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: 0.2rem;
            color: #1f2937;
        }

        .top-action-wrap {
            border: 1px solid #e8edf4;
            border-radius: 16px;
            padding: 12px 14px;
            background: #ffffff;
            box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
            margin-top: 10px;
            margin-bottom: 18px;
        }

        .top-action-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #344054;
            margin-bottom: 10px;
        }

        .secondary-note {
            color: #667085;
            font-size: 0.95rem;
            line-height: 1.45;
            margin-top: 8px;
        }

        div[data-testid="stDownloadButton"] > button {
            background: #1f4fbf !important;
            color: white !important;
            border: 1px solid #1f4fbf !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            min-height: 46px !important;
        }

        div[data-testid="stDownloadButton"] > button:hover {
            background: #183f98 !important;
            border-color: #183f98 !important;
            color: white !important;
        }

        /* make all normal buttons rounded and aligned */
        div[data-testid="stButton"] > button {
            border-radius: 12px !important;
            min-height: 46px !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.write("")
    c1, c2 = st.columns([1, 8])

    with c1:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=110)

    with c2:
        st.markdown(
            '<div class="main-title">SALA Standardized Feasibility Study for Solar AGL</div>',
            unsafe_allow_html=True,
        )


def _trigger_simulation():
    st.session_state.running = True
    st.session_state.run_stage = "Validating study inputs"
    st.session_state.run_progress = 0.0
    st.session_state.trigger_run = True
    st.rerun()

def render_top_action_bar():
    st.markdown('<div class="top-action-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="top-action-title">Actions</div>', unsafe_allow_html=True)

    ready = bool(st.session_state.get("study_ready", False))
    has_results = st.session_state.get("results") is not None
    is_running = bool(st.session_state.get("running", False))

    action_state = {
        "progress_bar": None,
        "progress_text": None,
        "stage_text": None,
    }

    if is_running:
        st.markdown("**Simulation in progress**")

        progress_cols = st.columns([6, 1])
        with progress_cols[0]:
            action_state["progress_bar"] = st.progress(0)
        with progress_cols[1]:
            action_state["progress_text"] = st.empty()

        action_state["stage_text"] = st.empty()

        # initial values
        pct = int(st.session_state.get("run_progress", 0))
        stage = st.session_state.get("run_stage", "Preparing simulation")

        action_state["progress_bar"].progress(pct)
        action_state["progress_text"].markdown(
            f"<div style='text-align:right;font-weight:700;color:#667085;'>{pct}%</div>",
            unsafe_allow_html=True,
        )
        action_state["stage_text"].markdown(
            f"<div class='secondary-note'>{stage}</div>",
            unsafe_allow_html=True,
        )

    elif not has_results:
        c1, c2 = st.columns([1.4, 4])

        with c1:
            if st.button(
                "Run simulation",
                type="primary",
                use_container_width=True,
                disabled=not ready,
                key="top_run_simulation",
            ):
                _trigger_simulation()

        with c2:
            if ready:
                st.markdown(
                    '<div class="secondary-note">Setup is complete. You can start the feasibility check.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="secondary-note">Select an airport or study point and at least one device to enable simulation.</div>',
                    unsafe_allow_html=True,
                )

    else:
        c1, c2, c3 = st.columns(3)

        with c1:
            if st.session_state.get("pdf_bytes") is not None:
                st.download_button(
                    "📄 Download PDF report",
                    data=st.session_state.get("pdf_bytes"),
                    file_name=st.session_state.get("pdf_name", "sala_standardized_feasibility_study.pdf"),
                    mime="application/pdf",
                    use_container_width=True,
                    key="top_download_pdf_report",
                )

        with c2:
            if st.button(
                "Run updated simulation",
                type="primary",
                use_container_width=True,
                disabled=not ready,
                key="top_run_updated_simulation",
            ):
                _trigger_simulation()

        with c3:
            st.markdown(
                """
                <style>
                div[data-testid="stButton"] button[kind="secondary"] {
                    background: #fff7db !important;
                    border: 1px solid #f5c451 !important;
                    color: #7a5a00 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Start new study",
                use_container_width=True,
                key="top_start_new_study",
            ):
                reset_study()

        st.markdown(
            '<div class="secondary-note">You can keep the same location, update devices or operating profile, and run the study again.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    return action_state


# ---------------- APP FLOW ----------------

init_state()
apply_global_styles()
render_header()

# Setup block
if st.session_state.get("running", False):
    with st.expander("Show study setup", expanded=False):
        st.caption("Inputs are temporarily locked while the simulation is running.")
        render_setup(disabled=True)
elif not st.session_state.get("results"):
    render_setup(disabled=False)
else:
    with st.expander("Show study setup", expanded=False):
        render_setup(disabled=False)

# Refresh readiness AFTER setup fields may have changed
refresh_study_ready_from_state()

# Actions block
action_state = render_top_action_bar()

if st.session_state.get("trigger_run"):
    st.session_state.trigger_run = False

    def progress_callback(percent: int, stage: str):
        percent = max(0, min(100, int(percent)))
        st.session_state.run_progress = percent
        st.session_state.run_stage = stage

        if action_state["progress_bar"] is not None:
            action_state["progress_bar"].progress(percent)

        if action_state["progress_text"] is not None:
            action_state["progress_text"].markdown(
                f"<div style='text-align:right;font-weight:700;color:#667085;'>{percent}%</div>",
                unsafe_allow_html=True,
            )

        if action_state["stage_text"] is not None:
            action_state["stage_text"].markdown(
                f"<div class='secondary-note'>{stage}</div>",
                unsafe_allow_html=True,
            )

    _run_simulation(progress_callback=progress_callback)

# Results
if st.session_state.get("results") is not None:
    results = st.session_state.get("results")
    render_result()
    render_graph()
    render_battery_section(results)
    render_weather_basis()
