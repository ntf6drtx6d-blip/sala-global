# ui/login_page.py

import base64
from pathlib import Path

import streamlit as st
from core.auth import login_user


LOGIN_BG_PATH = "assets/login_bg.jpg"
LOGO_PATH = "sala_logo.png"


def _img_to_base64(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def render_login_page():
    bg_b64 = _img_to_base64(LOGIN_BG_PATH)

    if bg_b64:
        bg_css = f"""
        background-image:
            linear-gradient(rgba(12,18,28,0.42), rgba(12,18,28,0.42)),
            url("data:image/jpeg;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        """
    else:
        bg_css = """
        background:
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 45%, #334155 100%);
        """

    st.markdown(
        f"""
        <style>
        .block-container {{
            max-width: 1000px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}

        .sala-login-shell {{
            min-height: 78vh;
            border-radius: 24px;
            overflow: hidden;
            position: relative;
            {bg_css}
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.20);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255,255,255,0.10);
        }}

        .sala-login-blur {{
            position: absolute;
            inset: 0;
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
        }}

        .sala-login-card {{
            position: relative;
            z-index: 2;
            width: 100%;
            max-width: 430px;
            background: rgba(255,255,255,0.90);
            border: 1px solid rgba(255,255,255,0.65);
            border-radius: 22px;
            padding: 28px 28px 22px 28px;
            box-shadow: 0 20px 60px rgba(15,23,42,0.22);
        }}

        .sala-login-logo-wrap {{
            display: flex;
            justify-content: center;
            margin-bottom: 10px;
        }}

        .sala-login-title {{
            text-align: center;
            font-size: 1.5rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.15;
            margin-bottom: 8px;
        }}

        .sala-login-subtitle {{
            text-align: center;
            color: #475467;
            font-size: 0.96rem;
            line-height: 1.45;
            margin-bottom: 20px;
        }}

        .sala-login-note {{
            text-align: center;
            color: #667085;
            font-size: 0.88rem;
            line-height: 1.45;
            margin-top: 14px;
        }}

        .sala-locked-badge {{
            display: inline-block;
            margin: 0 auto 14px auto;
            padding: 6px 12px;
            border-radius: 999px;
            background: #eef4ff;
            color: #1f4fbf;
            font-size: 0.82rem;
            font-weight: 700;
        }}

        div[data-testid="stTextInput"] > div {{
            background: transparent !important;
        }}

        div[data-testid="stTextInput"] input {{
            border-radius: 12px !important;
        }}

        div[data-testid="stButton"] > button {{
            min-height: 46px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sala-login-shell"><div class="sala-login-blur"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sala-login-card">', unsafe_allow_html=True)

    if Path(LOGO_PATH).exists():
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image(LOGO_PATH, width=120)

    st.markdown('<div class="sala-locked-badge">Member access required</div>', unsafe_allow_html=True)
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

    st.markdown("</div></div>", unsafe_allow_html=True)
