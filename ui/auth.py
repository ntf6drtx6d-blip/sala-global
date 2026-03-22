# ui/auth.py

import hmac
import os
import streamlit as st


def _get_login_credentials():
    username = os.getenv("APP_LOGIN_USERNAME", "admin")
    password = os.getenv("APP_LOGIN_PASSWORD", "change-me-now")
    return username, password


def init_auth_state():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False


def logout():
    st.session_state.auth_ok = False


def is_logged_in() -> bool:
    return bool(st.session_state.get("auth_ok", False))


def render_login_inline():
    init_auth_state()

    if st.session_state.auth_ok:
        return True

    with st.expander("Login required to download PDF", expanded=False):
        st.markdown("Enter credentials to unlock PDF download.")

        username = st.text_input("Username", key="pdf_login_username")
        password = st.text_input("Password", type="password", key="pdf_login_password")

        if st.button("Log in", key="pdf_login_button", use_container_width=True):
            valid_username, valid_password = _get_login_credentials()

            user_ok = hmac.compare_digest(username.strip(), valid_username)
            pass_ok = hmac.compare_digest(password, valid_password)

            if user_ok and pass_ok:
                st.session_state.auth_ok = True
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    return False
