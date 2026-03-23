# ui/login_page.py

from pathlib import Path

import streamlit as st
from core.auth import login_user
from core.db import create_access_request


LOGO_PATH = "sala_logo.png"


def render_login_page():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 760px;
            padding-top: 2.2rem;
            padding-bottom: 2rem;
        }

        .sala-login-logo-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 14px;
        }

        .sala-login-badge {
            display: inline-block;
            padding: 7px 14px;
            border-radius: 999px;
            background: #eef4ff;
            color: #1f4fbf;
            font-size: 0.84rem;
            font-weight: 700;
            margin-bottom: 14px;
        }

        .sala-login-title {
            font-size: 2.05rem;
            line-height: 1.08;
            font-weight: 800;
            color: #0f172a;
            text-align: center;
            margin-bottom: 10px;
        }

        .sala-login-subtitle {
            color: #475467;
            font-size: 1rem;
            line-height: 1.55;
            text-align: center;
            margin-bottom: 28px;
        }

        .sala-login-card {
            background: #ffffff;
            border: 1px solid #e6eaf0;
            border-radius: 20px;
            padding: 26px 26px 22px 26px;
            box-shadow: 0 10px 30px rgba(16,24,40,0.06);
            margin-bottom: 22px;
        }

        .sala-section-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 6px;
        }

        .sala-section-subtitle {
            color: #667085;
            font-size: 0.92rem;
            line-height: 1.5;
            margin-bottom: 16px;
        }

        .sala-divider {
            height: 1px;
            background: #eef2f6;
            margin: 22px 0;
        }

        .sala-note {
            color: #667085;
            font-size: 0.92rem;
            line-height: 1.5;
            text-align: center;
            margin-top: 16px;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea {
            border-radius: 12px !important;
        }

        div[data-testid="stButton"] > button {
            min-height: 48px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header
    if Path(LOGO_PATH).exists():
        c1, c2, c3 = st.columns([1.4, 1, 1.4])
        with c2:
            st.image(LOGO_PATH, width=120)

    badge_left, badge_mid, badge_right = st.columns([1, 1.2, 1])
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
        '<div class="sala-login-subtitle">Approved SALA members and registered external users can access the feasibility calculator after login.</div>',
        unsafe_allow_html=True,
    )

    # Main card
    st.markdown('<div class="sala-login-card">', unsafe_allow_html=True)

    st.markdown('<div class="sala-section-title">Log in</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sala-section-subtitle">Use your approved credentials to enter the tool.</div>',
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

    st.markdown('<div class="sala-divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sala-section-title">Request access</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sala-section-subtitle">If you do not have an account yet, send a request to SALA. Your request will be recorded for review.</div>',
        unsafe_allow_html=True,
    )

    req_name = st.text_input("Full name", key="req_full_name")
    req_email = st.text_input("Work email", key="req_email")
    req_org = st.text_input("Organization", key="req_organization")
    req_message = st.text_area(
        "Short message",
        key="req_message",
        height=110,
        placeholder="Who are you and why do you need access?",
    )

    if st.button("Send access request", use_container_width=True, key="send_access_request"):
        if not req_name.strip():
            st.error("Please enter your full name.")
        elif not req_email.strip():
            st.error("Please enter your email.")
        else:
            create_access_request(
                full_name=req_name.strip(),
                email=req_email.strip(),
                organization=req_org.strip() or None,
                message=req_message.strip() or None,
            )
            st.success("Your request has been sent to SALA for review.")

    st.markdown(
        '<div class="sala-note">Access is controlled by SALA. You will need approval before receiving credentials.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
