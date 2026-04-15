# ui/auth.py

import hmac
import os
import streamlit as st
from core.i18n import t


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
    lang = st.session_state.get("language", "en")

    if st.session_state.auth_ok:
        return True

    with st.expander(t("ui.login_required_pdf", lang), expanded=False):
        st.markdown(t("ui.enter_credentials_pdf", lang))

        username = st.text_input(t("ui.username", lang), key="pdf_login_username")
        password = st.text_input(t("ui.password", lang), type="password", key="pdf_login_password")

        if st.button(t("ui.log_in", lang), key="pdf_login_button", use_container_width=True):
            valid_username, valid_password = _get_login_credentials()

            user_ok = hmac.compare_digest(username.strip(), valid_username)
            pass_ok = hmac.compare_digest(password, valid_password)

            if user_ok and pass_ok:
                st.session_state.auth_ok = True
                st.success(t("ui.login_successful", lang))
                st.rerun()
            else:
                st.error(t("ui.invalid_username_password", lang))

    return False
