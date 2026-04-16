import os
import hmac
import base64
import hashlib
import streamlit as st

from core.db import get_user_by_email, update_last_login


_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    dk_b64 = base64.b64encode(dk).decode("utf-8")
    return f"pbkdf2_sha256${_ITERATIONS}${salt_b64}${dk_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, expected_b64 = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(expected_b64.encode("utf-8"))

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def init_auth_state():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
        st.session_state.auth_user_id = None
        st.session_state.auth_email = None
        st.session_state.auth_role = None
        st.session_state.auth_full_name = None
        st.session_state.auth_organization = None


def is_logged_in():
    return bool(st.session_state.get("auth_ok", False))


def is_admin():
    return st.session_state.get("auth_role") == "admin"


def logout():
    st.session_state.auth_ok = False
    st.session_state.auth_user_id = None
    st.session_state.auth_email = None
    st.session_state.auth_role = None
    st.session_state.auth_full_name = None
    st.session_state.auth_organization = None
    st.rerun()


def login_user(email: str, password: str) -> bool:
    user = get_user_by_email(email)

    if not user:
        return False

    if not user["is_active"]:
        return False

    if not verify_password(password, user["password_hash"]):
        return False

    st.session_state.auth_ok = True
    st.session_state.auth_user_id = user["id"]
    st.session_state.auth_email = user["email"]
    st.session_state.auth_role = user["role"]
    st.session_state.auth_full_name = user["full_name"]
    st.session_state.auth_organization = user.get("organization")

    update_last_login(user["id"])
    return True
