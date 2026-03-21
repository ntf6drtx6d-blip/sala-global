# app.py
# ACTION: REPLACE ENTIRE FILE

import os
import streamlit as st

from ui.setup import render_setup
from ui.cockpit import render_cockpit, _run_simulation, reset_study
from ui.result import render_result
from ui.graph import render_graph
from ui.battery import render_battery


# ---------------- CONFIG ----------------

st.set_page_config(
    page_title="SALA Standardized Feasibility Study for Solar AGL",
    layout="wide"
)

LOGO_PATH = "sala_logo.png"


# ---------------- SESSION STATE ----------------

def init_state():
    defaults = {
        "airport_label": "",
        "lat": 40.416775,
        "lon": -3.703790,
        "required_hours": 8.0,
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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------- STYLES ----------------

def apply_global_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.8rem;
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
            margin-bottom: 0.5rem;
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


# ---------------- HEADER ----------------

def render_header():
    c1, c2 = st.columns([1, 8])
    with c1:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=90)
    with c2:
        st.markdown(
            '<div class="main-title">SALA Standardized Feasibility Study for Solar AGL</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sub-title">PVGIS-based annual feasibility workflow for Solar AGL, PAPI and A-PAPI systems</div>',
            unsafe_allow_html=True,
        )


# ---------------- TOP ACTION BAR ----------------

def render_top_action_bar():
    st.markdown('<div class="top-action-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="top-action-title">Actions</div>', unsafe_allow_html=True)

    # BEFORE RUN
    if not st.session_state.get("running") and st.session_state.get("results") is None:
        c1, c2 = st.columns([1.2, 4])

        with c1:
            if st.button("Run simulation", type="primary", use_container_width=True, key="top_run_simulation"):
                st.session_state.running = True
                st.session_state.run_progress = 0
                st.session_state.run_stage = "Preparing simulation"
                st.session_state.trigger_run = True
                st.rerun()

        with c2:
            st.caption("Start the feasibility check using the selected study setup.")

    # DURING RUN
    elif st.session_state.get("running"):
        c1, c2 = st.columns([2.2, 3])

        with c1:
            st.progress(st.session_state.get("run_progress", 0) / 100.0)
            st.caption(f"Running… {st.session_state.get('run_progress', 0)}%")

        with c2:
            st.caption(st.session_state.get("run_stage", "Simulation in progress"))

    # AFTER RUN
    else:
        c1, c2, c3 = st.columns([1.2, 1.2, 3])

        with c1:
            if st.session_state.get("pdf_bytes") is not None:
                st.download_button(
                    "Download report",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_name,
                    mime="application/pdf",
                    use_container_width=True,
                    key="top_download_report",
                )
            else:
                st.button("Download report", disabled=True, use_container_width=True, key="top_download_disabled")

        with c2:
            if st.button("Start new study", use_container_width=True, key="top_start_new_study"):
                reset_study()

        with c3:
            st.caption("Simulation finished. You can download the report or reset the study and start again.")

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------- INIT ----------------

init_state()
apply_global_styles()
render_header()

# Top action bar first
render_top_action_bar()

# Desktop sidebar dashboard
render_cockpit()

# Trigger actual simulation AFTER rerender so top bar shows running-state
if st.session_state.get("trigger_run"):
    st.session_state.trigger_run = False
    _run_simulation()

# Main flow
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
