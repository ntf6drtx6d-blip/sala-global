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
            padding-bottom: 2.5rem;
        }

        .sala-login-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 18px;
            margin-bottom: 12px;
        }

        .sala-login-title {
            font-size: 2rem;
            line-height: 1.08;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }

        .sala-login-lock {
            text-align: center;
            margin-bottom: 22px;
        }

        .sala-login-badge {
            display: inline-block;
            padding: 7px 14px;
            border-radius: 999px;
            background: #eef4ff;
            color: #1f4fbf;
            font-size: 0.83rem;
            font-weight: 700;
        }

        .sala-login-card {
            background: #ffffff;
            border: 1px solid #e6eaf0;
            border-radius: 20px;
            padding: 28px 28px 22px 28px;
            box-shadow: 0 12px 34px rgba(16,24,40,0.07);
            margin-bottom: 18px;
        }

        .sala-section-title {
            font-size: 1.08rem;
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 14px;
        }

        .sala-note {
            color: #667085;
            font-size: 0.92rem;
            line-height: 1.5;
            margin-top: 14px;
        }

        .sala-footer-note {
            color: #667085;
            font-size: 0.9rem;
            line-height: 1.5;
            text-align: center;
            margin-top: 18px;
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

        div[data-testid="stExpander"] details {
            border: 1px solid #e6eaf0 !important;
            border-radius: 16px !important;
            background: #ffffff !important;
            overflow: hidden;
        }

        div[data-testid="stExpander"] summary {
            font-weight: 700 !important;
            color: #1f2937 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header: logo left, title right
    if Path(LOGO_PATH).exists():
        st.markdown('<div class="sala-login-header">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.2, 0.34, 4.0])
        with c2:
            st.image(LOGO_PATH, width=82)
        with c3:
            st.markdown(
                '<div class="sala-login-title">SALA Standardized Feasibility Study for Solar AGL</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="sala-login-title" style="text-align:center;">SALA Standardized Feasibility Study for Solar AGL</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="sala-login-lock"><span class="sala-login-badge">Member access required</span></div>',
        unsafe_allow_html=True,
    )

    # Login card
    st.markdown('<div class="sala-login-card">', unsafe_allow_html=True)
    st.markdown('<div class="sala-section-title">Log in</div>', unsafe_allow_html=True)

    email = st.text_input("Email", key="login_email_input")
    password = st.text_input("Password", type="password", key="login_password_input")

    if st.button("Log in", type="primary", use_container_width=True, key="login_submit"):
        ok = login_user(email.strip(), password)
        if ok:
            st.success("Logged in.")
            st.rerun()
        else:
            st.error("Invalid credentials or inactive account.")

    st.markdown(
        '<div class="sala-note">Access is granted by SALA.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Request access collapsed underneath
    with st.expander("Request access", expanded=False):
        req_name = st.text_input("Full name", key="req_full_name_input")
        req_email = st.text_input("Work email", key="req_email_input")
        req_org = st.text_input("Organization", key="req_organization_input")
        req_message = st.text_area(
            "Short message",
            key="req_message_input",
            height=120,
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
        '<div class="sala-footer-note">External users can request access below.</div>',
        unsafe_allow_html=True,
    )
