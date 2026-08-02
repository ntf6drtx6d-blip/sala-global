# core/notify.py
#
# Best-effort email notifications for the access-request workflow. Plain
# SMTP is used deliberately instead of a specific provider's API, so any
# SMTP-capable mailbox (Office365, Gmail, a transactional-email provider's
# SMTP endpoint, etc.) works without adding a new dependency.
#
# All sends are best-effort: an unconfigured or unreachable SMTP server
# must never block the underlying access-request or approval action, since
# the database record (and, for approvals, the created user account) is
# what actually matters. Callers get a bool back so they can tell the admin
# in the UI when a notification didn't go out.

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

_logger = logging.getLogger(__name__)

DEFAULT_APP_URL = "https://app.sala-global.com"


def _secret_or_env(name: str, default=None):
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default


def get_admin_email() -> str | None:
    return _secret_or_env("ADMIN_EMAIL")


def _smtp_config():
    host = _secret_or_env("SMTP_HOST")
    if not host:
        return None
    user = _secret_or_env("SMTP_USER")
    return {
        "host": host,
        "port": int(_secret_or_env("SMTP_PORT", 587)),
        "user": user,
        "password": _secret_or_env("SMTP_PASSWORD"),
        "from_email": _secret_or_env("SMTP_FROM_EMAIL") or user,
        "use_tls": str(_secret_or_env("SMTP_USE_TLS", "true")).strip().lower() not in ("0", "false", "no"),
    }


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Returns True on success, False if unconfigured or sending failed.
    Never raises - a broken mail server should not break the caller."""
    if not to_email:
        return False

    config = _smtp_config()
    if not config:
        _logger.warning("SMTP not configured (SMTP_HOST missing); skipping email to %s.", to_email)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["from_email"] or "no-reply@sala-global.com"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=15) as server:
            if config["use_tls"]:
                server.starttls()
            if config["user"] and config["password"]:
                server.login(config["user"], config["password"])
            server.send_message(msg)
        return True
    except Exception:
        _logger.exception("Failed to send email to %s.", to_email)
        return False


def notify_admin_new_access_request(
    admin_email: str,
    full_name: str,
    email: str,
    organization: str | None = None,
    message: str | None = None,
) -> bool:
    if not admin_email:
        return False

    lines = [
        "A new access request was submitted for the SALA Standardized Feasibility Study app.",
        "",
        f"Name: {full_name}",
        f"Email: {email}",
        f"Organization: {organization or '-'}",
    ]
    if message:
        lines += ["", "Message:", message]
    lines += ["", "Review it in the app: Admin panel > Access Requests."]

    return send_email(admin_email, "SALA app: new access request", "\n".join(lines))


def notify_user_access_approved(email: str, full_name: str, temp_password: str) -> bool:
    if not email:
        return False

    login_url = _secret_or_env("APP_URL") or DEFAULT_APP_URL
    lines = [
        f"Hi {full_name},",
        "",
        "Your access request for the SALA Standardized Feasibility Study app has been approved.",
        "",
        f"Log in here: {login_url}",
        f"Email: {email}",
        f"Temporary password: {temp_password}",
        "",
        "Please keep this password secure.",
    ]

    return send_email(email, "Your SALA app access has been approved", "\n".join(lines))
