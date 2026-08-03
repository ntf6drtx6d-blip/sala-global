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
#
# Emails are sent as branded HTML (with a plain-text fallback part) using a
# shared "shell" template so the three automated emails - new-request alert
# to the admin, receipt confirmation to the requester, and the approval
# email to the new user - look like they come from the same product,
# matching the login page's palette (navy text, SALA blue accents).

from __future__ import annotations

import html
import io
import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

_logger = logging.getLogger(__name__)

DEFAULT_APP_URL = "https://app.sala-global.com"
DEFAULT_SUPPORT_SALES_EMAIL = "supportsales@solutions4ga.com"
INTERNAL_EMAIL_DOMAINS = {"sala-global.com", "solutions4ga.com"}
_LOGO_PATH = Path(__file__).resolve().parent.parent / "sala_logo.png"
_LOGO_CID = "sala_logo"

_NAVY = "#0f172a"
_BLUE = "#1d4ed8"
_MUTED = "#667085"
_BORDER = "#e6eaf0"
_PANEL_BG = "#f8fafc"
_PAGE_BG = "#f4f6fa"
_GREEN = "#067647"
_GREEN_BG = "#ecfdf3"
_RED = "#b42318"
_RED_BG = "#fef3f2"
_AMBER = "#b54708"
_AMBER_BG = "#fffaeb"


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


def get_support_sales_email() -> str:
    return _secret_or_env("SUPPORT_SALES_EMAIL") or DEFAULT_SUPPORT_SALES_EMAIL


def get_app_url() -> str:
    return _app_url()


def is_internal_email(email: str) -> bool:
    domain = str(email or "").rsplit("@", 1)[-1].strip().lower()
    return domain in INTERNAL_EMAIL_DOMAINS


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


def _app_url() -> str:
    return _secret_or_env("APP_URL") or DEFAULT_APP_URL


def _logo_png_bytes() -> bytes | None:
    """sala_logo.png on disk is actually WebP; converted in-memory to a
    real PNG since Outlook and several other mail clients don't render
    WebP inline images."""
    try:
        from PIL import Image

        with Image.open(_LOGO_PATH) as im:
            buf = io.BytesIO()
            im.convert("RGB").save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        _logger.exception("Could not prepare SALA logo for email embedding.")
        return None


# --- shared HTML shell -----------------------------------------------------


def _info_table(rows: list[tuple[str, str]]) -> str:
    trs = "".join(
        f'<tr>'
        f'<td style="padding:7px 0;color:{_MUTED};font-size:13px;vertical-align:top;white-space:nowrap;">{html.escape(label)}</td>'
        f'<td style="padding:7px 0 7px 14px;color:{_NAVY};font-size:13px;font-weight:700;text-align:right;">{value}</td>'
        f"</tr>"
        for label, value in rows
    )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-top:1px solid {_BORDER};margin-top:14px;">{trs}</table>'
    )


def _button(label: str, url: str) -> str:
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:20px;">'
        f'<tr><td style="border-radius:10px;background:{_BLUE};">'
        f'<a href="{html.escape(url)}" style="display:inline-block;padding:11px 22px;font-size:14px;'
        f'font-weight:700;color:#ffffff;text-decoration:none;border-radius:10px;">{html.escape(label)}</a>'
        f"</td></tr></table>"
    )


def _email_shell(preheader: str, heading: str, body_html: str, has_logo: bool) -> str:
    logo_block = (
        f'<img src="cid:{_LOGO_CID}" alt="SALA" width="96" style="display:block;border:0;outline:none;">'
        if has_logo
        else f'<div style="font-weight:800;font-size:20px;color:{_NAVY};letter-spacing:0.02em;">SALA</div>'
    )
    return f"""<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{_PAGE_BG};font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <span style="display:none;font-size:1px;color:{_PAGE_BG};">{html.escape(preheader)}</span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_PAGE_BG};padding:32px 12px;">
      <tr><td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0"
               style="max-width:560px;width:100%;background:#ffffff;border:1px solid {_BORDER};border-radius:18px;overflow:hidden;">
          <tr><td style="padding:22px 30px;border-bottom:1px solid {_BORDER};">{logo_block}</td></tr>
          <tr><td style="padding:28px 30px 8px 30px;">
            <div style="font-size:19px;font-weight:800;color:{_NAVY};margin-bottom:6px;">{html.escape(heading)}</div>
            {body_html}
          </td></tr>
          <tr><td style="padding:18px 30px;background:{_PANEL_BG};color:{_MUTED};font-size:11.5px;text-align:center;">
            SALA Standardized Feasibility Study for Solar AGL &middot; Automated notification, please do not reply
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""


def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
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
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")
        logo_bytes = _logo_png_bytes()
        if logo_bytes:
            html_part = msg.get_payload()[1]
            html_part.add_related(logo_bytes, maintype="image", subtype="png", cid=f"<{_LOGO_CID}>")

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


# --- concrete emails ---------------------------------------------------


def notify_admin_new_access_request(
    admin_email: str,
    full_name: str,
    email: str,
    organization: str | None = None,
    message: str | None = None,
) -> bool:
    if not admin_email:
        return False

    rows = [
        ("Name", html.escape(full_name)),
        ("Email", html.escape(email)),
        ("Organization", html.escape(organization or "-")),
    ]
    body_html = (
        f'<p style="font-size:14px;color:{_NAVY};line-height:1.5;margin:0;">'
        f"A new access request was submitted for the SALA app.</p>"
        f"{_info_table(rows)}"
    )
    if message:
        body_html += (
            f'<div style="margin-top:16px;padding:12px 14px;background:{_PANEL_BG};border-radius:10px;'
            f'font-size:13px;color:{_NAVY};line-height:1.5;">{html.escape(message)}</div>'
        )
    body_html += _button("Review in Admin panel", f"{_app_url()}")

    html_out = _email_shell(
        preheader=f"New access request from {full_name}",
        heading="New access request",
        body_html=body_html,
        has_logo=True,
    )

    text_lines = [
        "A new access request was submitted for the SALA Standardized Feasibility Study app.",
        "",
        f"Name: {full_name}",
        f"Email: {email}",
        f"Organization: {organization or '-'}",
    ]
    if message:
        text_lines += ["", "Message:", message]
    text_lines += ["", "Review it in the app: Admin panel > Access Requests."]

    return send_email(admin_email, "SALA app: new access request", "\n".join(text_lines), html_out)


def notify_requester_received(full_name: str, email: str, organization: str | None = None) -> bool:
    """Confirms receipt to the person who just submitted a request - so
    they know it actually reached SALA, before an admin has done anything
    with it yet."""
    if not email:
        return False

    rows = [
        ("Name", html.escape(full_name)),
        ("Email", html.escape(email)),
        ("Organization", html.escape(organization or "-")),
    ]
    body_html = (
        f'<p style="font-size:14px;color:{_NAVY};line-height:1.5;margin:0;">'
        f"Hi {html.escape(full_name)},</p>"
        f'<p style="font-size:14px;color:{_NAVY};line-height:1.5;">'
        f"Thanks for your interest in the SALA Standardized Feasibility Study app. Your access request has "
        f"been received and forwarded to the SALA team for review. We'll be in touch as soon as it's approved."
        f"</p>"
        f"{_info_table(rows)}"
    )

    html_out = _email_shell(
        preheader="Your SALA app access request has been received",
        heading="Request received",
        body_html=body_html,
        has_logo=True,
    )

    text_lines = [
        f"Hi {full_name},",
        "",
        "Thanks for your interest in the SALA Standardized Feasibility Study app. Your access request has "
        "been received and forwarded to the SALA team for review. We'll be in touch as soon as it's approved.",
        "",
        f"Name: {full_name}",
        f"Email: {email}",
        f"Organization: {organization or '-'}",
    ]

    return send_email(email, "We've received your SALA app access request", "\n".join(text_lines), html_out)


def notify_user_access_approved(email: str, full_name: str, temp_password: str) -> bool:
    if not email:
        return False

    login_url = _app_url()
    rows = [
        ("Email", html.escape(email)),
        ("Temporary password", f'<span style="font-family:monospace;">{html.escape(temp_password)}</span>'),
    ]
    body_html = (
        f'<p style="font-size:14px;color:{_NAVY};line-height:1.5;margin:0;">'
        f"Hi {html.escape(full_name)},</p>"
        f'<p style="font-size:14px;color:{_NAVY};line-height:1.5;">'
        f"Your access request for the SALA Standardized Feasibility Study app has been approved. "
        f"Use the credentials below to log in, and please keep this password secure."
        f"</p>"
        f"{_info_table(rows)}"
        f"{_button('Log in to SALA', login_url)}"
    )

    html_out = _email_shell(
        preheader="Your SALA app access has been approved",
        heading="Access approved",
        body_html=body_html,
        has_logo=True,
    )

    text_lines = [
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

    return send_email(email, "Your SALA app access has been approved", "\n".join(text_lines), html_out)


def _equipment_list_html(equipment: list[dict]) -> str:
    rows = "".join(
        f'<tr>'
        f'<td style="padding:5px 0;color:{_NAVY};font-size:13px;">{html.escape(str(item.get("name") or ""))}</td>'
        f'<td style="padding:5px 0;text-align:right;">'
        f'<span style="font-size:11px;font-weight:800;color:{_GREEN if item.get("status") == "PASS" else _RED};">'
        f'{"PASS" if item.get("status") == "PASS" else "FAIL"}</span></td>'
        f"</tr>"
        for item in equipment
    )
    return (
        f'<div style="margin-top:14px;">'
        f'<div style="font-size:12px;font-weight:700;color:{_MUTED};text-transform:uppercase;letter-spacing:0.03em;'
        f'margin-bottom:2px;">Equipment tested</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        f"</div>"
    )


def notify_fs_completed(
    study_id,
    share_token: str | None,
    author_name: str,
    author_email: str,
    author_organization: str | None,
    airport_label: str,
    airport_icao: str | None,
    overall_status: str,
    status_detail: str | None,
    equipment: list[dict] | None,
    study_version: int | None,
    language_label: str,
) -> bool:
    """Alerts SALA sales/support whenever someone outside the internal
    domains completes a Feasibility Study, so the team knows a prospect
    or partner just ran one - who, which airport, whether it passed, and
    which specific equipment passed/failed. The link carries share_token
    so whoever gets this email can open/download that exact study without
    needing an admin account - see core/db.get_study's token match."""
    to_email = get_support_sales_email()
    if not to_email or not study_id:
        return False

    status_colors = {
        "PASS": (_GREEN, _GREEN_BG),
        "FAIL": (_RED, _RED_BG),
        "MIXED": (_AMBER, _AMBER_BG),
    }
    color, bg = status_colors.get(overall_status, (_MUTED, _PANEL_BG))

    is_recalculation = bool(study_version and study_version > 1)
    version_suffix = f" (v{study_version})" if is_recalculation else ""
    subject = f"SALA FS: {author_name} — {airport_label} — {overall_status}{version_suffix}"
    download_url = f"{_app_url()}/?study={study_id}"
    if share_token:
        download_url += f"&token={share_token}"

    status_pill = (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:999px;background:{bg};'
        f'color:{color};font-size:12px;font-weight:800;letter-spacing:0.02em;">{html.escape(overall_status)}</span>'
    )

    airport_display = airport_label + (f" ({airport_icao})" if airport_icao else "")
    rows = [
        ("Made by", html.escape(f"{author_name} ({author_email})")),
        ("Organization", html.escape(author_organization or "-")),
        ("Airport", html.escape(airport_display)),
        ("Result", status_pill),
        ("Version", f"v{study_version}" if study_version else "-"),
        ("Report language", html.escape(language_label)),
    ]

    intro = f"{html.escape(author_name)} completed a Feasibility Study"
    intro += " (recalculation)" if is_recalculation else ""
    intro += "."
    body_html = (
        f'<p style="font-size:14px;color:{_NAVY};line-height:1.5;margin:0;">{intro}</p>'
        f"{_info_table(rows)}"
    )
    if status_detail:
        body_html += f'<div style="margin-top:14px;font-size:13px;color:{_MUTED};">{html.escape(status_detail)}</div>'
    if equipment:
        body_html += _equipment_list_html(equipment)
    body_html += _button("View / download study", download_url)

    html_out = _email_shell(
        preheader=subject,
        heading="Feasibility Study completed",
        body_html=body_html,
        has_logo=True,
    )

    text_lines = [
        f"{author_name} ({author_email}) completed a Feasibility Study.",
        "",
        f"Organization: {author_organization or '-'}",
        f"Airport: {airport_display}",
        f"Result: {overall_status}" + (f" - {status_detail}" if status_detail else ""),
        f"Version: v{study_version}" if study_version else "Version: -",
        f"Report language: {language_label}",
    ]
    if equipment:
        text_lines += ["", "Equipment tested:"]
        text_lines += [f"  - {item.get('name')}: {item.get('status')}" for item in equipment]
    text_lines += ["", f"View / download: {download_url}"]

    return send_email(to_email, subject, "\n".join(text_lines), html_out)
