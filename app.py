# app.py
# ACTION: REPLACE ENTIRE FILE

import os
import streamlit as st

from ui.setup import render_setup
from ui.cockpit import render_cockpit, _run_simulation, reset_study
from ui.result import render_result
from ui.graph import render_graph
from ui.battery import render_battery
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
        "run_progress": 0,
        "run_stage": "Ready",
        "run_log": [],
        "trigger_run": False,
        "study_point_confirmed": False,
        "study_ready": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def apply_global_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.6rem;
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
            margin-bottom: 0.2rem;
            color: #1f2937;
        }
        .top-action-wrap {
            border: 1px solid #e8edf4;
            border-radius: 16px;
            padding: 12px 14px;
            background: #ffffff;
            box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
            margin-bottom: 16px;
        }
        .top-action-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #344054;
            margin-bottom: 8px;
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


def render_top_action_bar():
    st.markdown('<div class="top-action-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="top-action-title">Actions</div>', unsafe_allow_html=True)

    ready = bool(st.session_state.get("study_ready", False))

    if not st.session_state.get("running") and st.session_state.get("results") is None:
        c1, c2 = st.columns([1.2, 4])

        with c1:
            if st.button(
                "Run simulation",
                type="primary",
                use_container_width=True,
                key="top_run_simulation",
                disabled=not ready,
            ):
                st.session_state.running = True
                st.session_state.run_stage = "Preparing simulation"
                st.session_state.trigger_run = True
                st.rerun()

        with c2:
            if ready:
                st.caption("Start the feasibility check using the selected study setup.")
            else:
                st.caption("Select an airport or study point and at least one device to enable simulation.")

    elif st.session_state.get("running"):
        c1, c2 = st.columns([1.5, 4])

        with c1:
            st.markdown("**Simulation in progress**")

        with c2:
            st.caption(st.session_state.get("run_stage", "Processing"))

    else:
        c1, c2 = st.columns([1.2, 4])

        with c1:
            if st.button("Start new study", use_container_width=True, key="top_start_new_study"):
                reset_study()

        with c2:
            st.caption("Simulation finished. You can review the results below or start a new study.")

    st.markdown('</div>', unsafe_allow_html=True)


init_state()
apply_global_styles()
render_header()
render_top_action_bar()
render_cockpit()

if st.session_state.get("trigger_run"):
    st.session_state.trigger_run = False
    _run_simulation()

if st.session_state.get("results") is not None:
    render_result()

if not st.session_state.get("results"):
    render_setup()
else:
    with st.expander("Show study setup", expanded=False):
        render_setup()

if st.session_state.get("results") is not None:
    render_graph()
    render_battery()
    render_weather_basis()
