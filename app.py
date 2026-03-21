# app.py
# ACTION: REPLACE ENTIRE FILE

import os
import streamlit as st

# UI modules
from ui.setup import render_setup
from ui.cockpit import render_cockpit
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


# ---------------- INIT ----------------

init_state()
apply_global_styles()
render_header()


# ---------------- LAYOUT ----------------

# Sidebar (cockpit)
render_cockpit()

# Main flow

# RESULT (after simulation)
if st.session_state.get("results") is not None:
    render_result()

# SETUP
if not st.session_state.get("results"):
    render_setup()
else:
    with st.expander("Show study setup", expanded=False):
        render_setup()

# GRAPH + BATTERY
if st.session_state.get("results") is not None:
    render_graph()
    render_battery()
