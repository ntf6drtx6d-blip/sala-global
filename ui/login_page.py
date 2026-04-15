# ui/login_page.py

from pathlib import Path

import streamlit as st
from core.auth import login_user
from core.db import create_access_request
from core.i18n import t


LOGO_PATH = "sala_logo.png"


def render_login_page():
    if bool(st.session_state.get("auth_ok", False)):
        return

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 760px;
            padding-top: 2.2rem;
            padding-bottom: 2.5rem;
        }

        .sala-login-head-wrap {
            max-width: 760px;
            margin: 0 auto 18px auto;
        }

        .sala-login-header {
            display: flex;
            align-items: center;
            gap: 18px;
            margin-bottom: 10px;
        }

        .sala-login-title {
            font-size: 2.05rem;
            line-height: 1.08;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }

        .sala-login-lock {
            margin-bottom: 18px;
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

    # Header block aligned to same width as login area
    st.markdown('<div class="sala-login-head-wrap">', unsafe_allow_html=True)

    if Path(LOGO_PATH).exists():
        col_logo, col_title = st.columns([0.16, 0.84], gap="small")
        with col_logo:
            st.image(LOGO_PATH, width=92)
        with col_title:
            st.markdown(
                f'<div class="sala-login-title">{t("app.title", st.session_state.get("language", "en"))}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f'<div class="sala-login-title">{t("app.title", st.session_state.get("language", "en"))}</div>',
            unsafe_allow_html=True,
        )

    lang = st.session_state.get("language", "en")
    st.markdown(
        f'<div class="sala-login-lock"><span class="sala-login-badge">{t("ui.member_access_required", lang)}</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Login card
    st.markdown('<div class="sala-login-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sala-section-title">{t("ui.log_in", lang)}</div>', unsafe_allow_html=True)

    email = st.text_input(t("ui.email", lang), key="login_email_input")
    password = st.text_input(t("ui.password", lang), type="password", key="login_password_input")

    if st.button(t("ui.log_in", lang), type="primary", use_container_width=True, key="login_submit"):
        ok = login_user(email.strip(), password)
        if ok:
            st.success(t("ui.logged_in", lang))
            st.rerun()
        else:
            st.error(t("ui.invalid_credentials", lang))

    st.markdown(
        f'<div class="sala-note">{t("ui.access_granted_by_sala", lang)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Request access collapsed underneath
    with st.expander(t("ui.request_access", lang), expanded=False):
        req_name = st.text_input(t("ui.full_name", lang), key="req_full_name_input")
        req_email = st.text_input(t("ui.work_email", lang), key="req_email_input")
        req_org = st.text_input(t("ui.organization", lang), key="req_organization_input")
        req_message = st.text_area(
            t("ui.short_message", lang),
            key="req_message_input",
            height=120,
            placeholder=t("ui.access_request_placeholder", lang),
        )

        if st.button(t("ui.send_access_request", lang), use_container_width=True, key="send_access_request"):
            if not req_name.strip():
                st.error(t("ui.enter_full_name", lang))
            elif not req_email.strip():
                st.error(t("ui.enter_email", lang))
            else:
                create_access_request(
                    full_name=req_name.strip(),
                    email=req_email.strip(),
                    organization=req_org.strip() or None,
                    message=req_message.strip() or None,
                )
                st.success(t("ui.request_sent", lang))

    st.markdown(
        f'<div class="sala-footer-note">{t("ui.external_users_request_below", lang)}</div>',
        unsafe_allow_html=True,
    )
