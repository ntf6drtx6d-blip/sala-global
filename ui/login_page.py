# ui/login_page.py

import base64
from pathlib import Path

import streamlit as st
from core.auth import login_user


LOGIN_BG_PATH = "assets/login_bg.jpg"
LOGO_PATH = "sala_logo.png"


def _img_to_base64(path: str):
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def render_login_page():
    bg_b64 = _img_to_base64(LOGIN_BG_PATH)

    if bg_b64:
        bg_css = f"""
        background-image:
            linear-gradient(rgba(15, 23, 42, 0.40), rgba(15, 23, 42, 0.40)),
            url("data:image/jpeg;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        """
    else:
        bg_css = """
        background: linear-gradient(135deg, #1e3a8a 0%, #334155 100%);
        """

    st.markdown(
        f"""
        <style>
        .block-container {{
            max-width: 1200px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }}

        .sala-login-hero {{
            {bg_css}
            min-height: 320px;
            border-radius: 26px;
            border: 1px solid rgba(255,255,255,0.14);
            box-shadow: 0 18px 60px rgba(15, 23, 42, 0.18);
            margin-bottom: 28px;
        }}

        .sala-login-badge {{
            display: inline-block;
            padding: 7px 14px;
            border-radius: 999px;
            background: #eef4ff;
            color: #1f4fbf;
            font-size: 0.84rem;
            font-weight: 700;
            margin-bottom: 14px;
        }}

        .sala-login-title {{
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 800;
            color: #0f172a;
            text-align: center;
            margin-bottom: 10px;
        }}

        .sala-login-subtitle {{
            color: #475467;
            font-size: 1rem;
            line-height: 1.5;
            text-align: center;
            margin-bottom: 24px;
        }}

        .sala-login-note {{
            color: #667085;
            font-size: 0.92rem;
            line-height: 1.45;
            text-align: center;
            margin-top: 18px;
        }}

        div[data-testid="stTextInput"] input {{
            border-radius: 12px !important;
        }}

        div[data-testid="stButton"] > button {{
            min-height: 48px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sala-login-hero"></div>', unsafe_allow_html=True)

    outer_left, center, outer_right = st.columns([1.2, 2.4, 1.2])

    with center:
        if Path(LOGO_PATH).exists():
            logo_left, logo_mid, logo_right = st.columns([1.3, 1, 1.3])
            with logo_mid:
                st.image(LOGO_PATH, width=120)

        badge_left, badge_mid, badge_right = st.columns([1, 1.6, 1])
        with badge_mid:
            st.markdown(
                '<div style="text-align:center;"><span class="sala-login-badge">Member access required</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="sala-login-title">SALA Standardized Feasibility Study for Solar AGL</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sala-login-subtitle">Please log in to access the SALA feasibility calculator and member tools.</div>',
            unsafe_allow_html=True,
        )

        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log in", type="primary", use_container_width=True, key="login_submit"):
            ok = login_user(email.strip(), password)
            if ok:
                st.success("Logged in.")
                st.rerun()
            else:
                st.error("Invalid credentials or inactive account.")

        st.markdown(
            '<div class="sala-login-note">Access is restricted to approved SALA members and registered external users.</div>',
            unsafe_allow_html=True,
        )
