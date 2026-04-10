
import streamlit as st

def reset_run_state_after_success():
    st.session_state["running"] = False
    st.session_state["trigger_run"] = False
    st.session_state["run_stage"] = "Completed"
