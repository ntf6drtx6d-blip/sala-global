
import streamlit as st

def reset_state():
    st.session_state["running"] = False
    st.session_state["trigger_run"] = False
