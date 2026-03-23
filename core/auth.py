# core/auth.py

import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash

from core.db import get_user_by_email, update_last_login


# =========================
# PASSWORD
# =========================

def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


# =========================
# SESSION
# =========================

def init_auth_state():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
        st.session_state.auth_user_id = None
        st.session_state.auth_email = None
        st.session_state.auth_role = None


def is_logged_in():
    return bool(st.session_state.get("auth_ok", False))


def is_admin():
    return st.session_state.get("auth_role") == "admin"


def logout():
    st.session_state.auth_ok = False
    st.session_state.auth_user_id = None
    st.session_state.auth_email = None
    st.session_state.auth_role = None
    st.rerun()


# =========================
# LOGIN
# =========================

def login_user(email: str, password: str) -> bool:
    user = get_user_by_email(email)

    if not user:
        return False

    if not user["is_active"]:
        return False

    if not verify_password(password, user["password_hash"]):
        return False

    # SUCCESS
    st.session_state.auth_ok = True
    st.session_state.auth_user_id = user["id"]
    st.session_state.auth_email = user["email"]
    st.session_state.auth_role = user["role"]

    update_last_login(user["id"])

    return True
