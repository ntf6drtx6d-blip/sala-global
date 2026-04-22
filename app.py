import os
import json
import time
import hmac
import base64
import hashlib
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from core.i18n import AVAILABLE_LANGUAGES, month_label, month_labels, t
from core.db import init_db, upsert_user, save_study, get_user_by_email
from core.person import normalize_person_name
from core.auth import hash_password, init_auth_state, is_logged_in, is_admin, logout

from ui.setup import render_setup
from ui.cockpit import _run_simulation, reset_study
from ui.result import render_result, render_device_capability_cards
from ui.graph import render_graph
from ui.weather_basis import render_weather_basis
from ui.admin import render_admin_panel
from ui.my_studies import render_my_studies
from ui.result_helpers import annual_empty_battery_stats, overall_state


st.set_page_config(
    page_title="SALA Standardized Feasibility Study for Solar AGL",
    page_icon="sala_favicon.png",
    layout="wide",
)

LOGO_PATH = "sala_logo.png"
LANGUAGE_FLAGS = {
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
}

# ---- Persistent auth via signed URL token ----
# This survives Streamlit restarts because it is stored in the browser URL.
# It is not as strong as HttpOnly cookies, but it works without extra packages.
AUTH_QUERY_PARAM = "auth"
AUTH_TOKEN_TTL_DAYS = 30


def _secret_or_env(name: str, default=None):
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _auth_persist_secret() -> str:
    return (
        _secret_or_env("AUTH_PERSIST_SECRET")
        or _secret_or_env("REMEMBER_ME_SECRET")
        or _secret_or_env("ADMIN_PASSWORD")
        or "change-this-secret-in-streamlit-secrets"
    )


def _sign_auth_payload(payload_json: str) -> str:
    secret = _auth_persist_secret().encode("utf-8")
    sig = hmac.new(secret, payload_json.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(sig)


def _make_auth_token() -> str | None:
    email = st.session_state.get("auth_email")
    user_id = st.session_state.get("auth_user_id")
    role = st.session_state.get("auth_role")
    full_name = st.session_state.get("auth_full_name")

    if not email or not user_id:
        return None

    payload = {
        "uid": int(user_id),
        "email": str(email),
        "role": str(role or ""),
        "full_name": str(full_name or ""),
        "exp": int(time.time()) + AUTH_TOKEN_TTL_DAYS * 24 * 3600,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = _sign_auth_payload(payload_json)
    return f"{_b64url_encode(payload_json.encode('utf-8'))}.{sig}"


def _parse_auth_token(token: str) -> dict | None:
    try:
        payload_b64, sig = token.split(".", 1)
        payload_json = _b64url_decode(payload_b64).decode("utf-8")
        expected_sig = _sign_auth_payload(payload_json)

        if not hmac.compare_digest(sig, expected_sig):
            return None

        payload = json.loads(payload_json)
        if int(payload.get("exp", 0)) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


def _set_auth_query_token(token: str | None):
    qp = st.query_params
    if token:
        qp[AUTH_QUERY_PARAM] = token
    else:
        try:
            del qp[AUTH_QUERY_PARAM]
        except Exception:
            qp[AUTH_QUERY_PARAM] = ""


def restore_login_from_query_token():
    if is_logged_in():
        return

    token = st.query_params.get(AUTH_QUERY_PARAM)
    if not token:
        return

    payload = _parse_auth_token(token)
    if not payload:
        _set_auth_query_token(None)
        return

    email = payload.get("email")
    if not email:
        _set_auth_query_token(None)
        return

    user = get_user_by_email(email)
    if not user or not user["is_active"]:
        _set_auth_query_token(None)
        return

    st.session_state.auth_ok = True
    st.session_state.auth_user_id = user["id"]
    st.session_state.auth_email = user["email"]
    st.session_state.auth_role = user["role"]
    st.session_state.auth_full_name = user["full_name"]
    st.session_state.auth_organization = user.get("organization")


def persist_login_to_query_token():
    if not is_logged_in():
        return

    current = st.query_params.get(AUTH_QUERY_PARAM)
    payload = _parse_auth_token(current) if current else None

    # refresh token if missing, invalid, or belongs to a different user
    if (
        not payload
        or payload.get("email") != st.session_state.get("auth_email")
        or int(payload.get("uid", -1)) != int(st.session_state.get("auth_user_id") or -1)
    ):
        token = _make_auth_token()
        if token:
            _set_auth_query_token(token)


def logout_and_forget():
    _set_auth_query_token(None)
    logout()


def _format_duration(seconds):
    if seconds is None:
        return None
    total = max(0, int(round(float(seconds))))
    mins, secs = divmod(total, 60)
    hrs, mins = divmod(mins, 60)
    if hrs:
        return f"{hrs}h {mins:02d}m"
    if mins:
        return f"{mins}m {secs:02d}s"
    return f"{secs}s"


def init_state():
    defaults = {
        "airport_label": "",
        "airport_query": "",
        "airport_icao": "",
        "language": "en",
        "lat": 40.416775,
        "lon": -3.703790,
        "required_hours": 12.0,
        "operating_profile_mode": "Custom hours per day",
        "selected_ids": [],
        "selected_simulation_keys": [],
        "per_device_config": {},
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "SALA_report.pdf",
        "elapsed": None,
        "search_message": "",
        "map_click_info": "",
        "running": False,
        "run_progress": 0.0,
        "run_stage": "Ready",
        "run_log": [],
        "run_started_at": None,
        "run_elapsed_seconds": None,
        "run_eta_seconds": None,
        "trigger_run": False,
        "study_point_confirmed": False,
        "study_ready": False,
        "study_saved_for_current_result": False,
        "simulation_cache_key": None,
        "simulation_cache_results": None,
        "simulation_cache_overall": None,
        "simulation_cache_pdf_context": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def bootstrap_admin_user():
    init_db()

    admin_email = _secret_or_env("ADMIN_EMAIL")
    admin_password = _secret_or_env("ADMIN_PASSWORD")
    admin_full_name = _secret_or_env("ADMIN_FULL_NAME", "Admin")
    admin_organization = _secret_or_env("ADMIN_ORGANIZATION", "SALA")

    if not admin_email or not admin_password:
        return

    upsert_user(
        email=admin_email,
        password_hash=hash_password(admin_password),
        role="admin",
        full_name=admin_full_name,
        organization=admin_organization,
        is_active=True,
    )


def refresh_study_ready_from_state():
    selected_ids = st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", [])
    study_point_confirmed = bool(st.session_state.get("study_point_confirmed", False))
    mode = st.session_state.get("operating_profile_mode")
    required_hours = st.session_state.get("required_hours")

    mode_ready = False
    if mode == "24/7":
        mode_ready = True
    elif mode == "Dusk to dawn":
        mode_ready = required_hours is not None
    elif mode == "Custom hours per day":
        mode_ready = required_hours is not None and float(required_hours) > 0

    st.session_state.study_ready = bool(
        len(selected_ids) > 0 and study_point_confirmed and mode_ready
    )


def apply_global_styles():
    auth_hide_css = ""
    if is_logged_in():
        auth_hide_css = """
        .sala-login-head-wrap,
        .sala-login-card,
        .sala-footer-note {
            display: none !important;
        }
        """

    st.markdown(
        """
        <style>

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        header[data-testid="stHeader"] {
            background: rgba(255,255,255,0);
        }

        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: 0.2rem;
            color: #1f2937;
        }

        .top-action-wrap {
            border: 1px solid #e8edf4;
            border-radius: 16px;
            padding: 12px 14px;
            background: #ffffff;
            box-shadow: 0 4px 18px rgba(17, 24, 39, 0.05);
            margin-top: 10px;
            margin-bottom: 18px;
        }

        .top-action-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #344054;
            margin-bottom: 10px;
        }

        .secondary-note {
            color: #667085;
            font-size: 0.95rem;
            line-height: 1.45;
            margin-top: 8px;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 12px !important;
            min-height: 48px !important;
            height: 48px !important;
            font-weight: 700 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            margin: 0 !important;
        }

        div[data-testid="stDownloadButton"] > button {
            background: #1f4fbf !important;
            color: white !important;
            border: 1px solid #1f4fbf !important;
        }

        div[data-testid="stDownloadButton"] > button:hover {
            background: #183f98 !important;
            border-color: #183f98 !important;
            color: white !important;
        }

        div[data-testid="stButton"] button[kind="secondary"] {
            background: #fff7db !important;
            border: 1px solid #f5c451 !important;
            color: #7a5a00 !important;
        }

        div[data-testid="stHorizontalBlock"] > div {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }

        div[data-testid="stButton"],
        div[data-testid="stDownloadButton"] {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            height: 100% !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
        }

        div[data-testid="stButton"] > div,
        div[data-testid="stDownloadButton"] > div {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }

        div[data-testid="stPopover"] button {
            border-radius: 999px !important;
            min-height: 44px !important;
            padding: 8px 16px !important;
            font-weight: 700 !important;
            background: #eef4ff !important;
            border: 1px solid #d6e4ff !important;
            color: #1f3a8a !important;
            transition: all 0.2s ease;
        }

        div[data-testid="stPopover"] button:hover {
            background: #e0edff !important;
            border-color: #bcd3ff !important;
        }

        div[data-testid="stPopover"] {
            border-radius: 14px !important;
        }

        .stDataFrame {
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        div[data-testid="stExpander"] {
            border-radius: 12px !important;
            border: 1px solid #e6eaf0 !important;
        }

        input, textarea {
            border-radius: 10px !important;
        }

        hr {
            border: none;
            border-top: 1px solid #e6eaf0;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
    if auth_hide_css:
        st.markdown(f"<style>{auth_hide_css}</style>", unsafe_allow_html=True)


def _display_name_from_email(email: str) -> str:
    if not email:
        return t("ui.account", st.session_state.get("language"))

    local = email.split("@")[0]
    parts = local.replace(".", " ").replace("_", " ").split()

    if not parts:
        return email

    if len(parts) == 1:
        return parts[0].capitalize()

    first = parts[0][:1].upper()
    last = parts[-1].capitalize()

    return f"{first}. {last}"


def _display_name() -> str:
    full_name = str(st.session_state.get("auth_full_name") or "").strip()
    if full_name:
        return normalize_person_name(full_name)
    return _display_name_from_email(st.session_state.get("auth_email", ""))


def render_header():
    c1, c2, c3 = st.columns([1, 6, 2])

    with c1:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=90)

    with c2:
        st.markdown(
            f'<div class="main-title">{t("app.title", st.session_state.get("language"))}</div>',
            unsafe_allow_html=True,
        )

    with c3:
        current_lang = st.session_state.get("language", "en")
        selected_lang = st.selectbox(
            t("ui.language", current_lang),
            options=list(AVAILABLE_LANGUAGES.keys()),
            index=list(AVAILABLE_LANGUAGES.keys()).index(current_lang) if current_lang in AVAILABLE_LANGUAGES else 0,
            format_func=lambda code: f"{LANGUAGE_FLAGS.get(code, code.upper())}  {AVAILABLE_LANGUAGES[code]}",
            key="ui_language_selector",
            label_visibility="collapsed",
        )
        st.session_state.language = selected_lang
        email = st.session_state.get("auth_email", "")
        role = st.session_state.get("auth_role", "")
        display_name = _display_name()
        user_label = f"{display_name}"

        with st.popover(user_label, use_container_width=True):
            lang = st.session_state.get("language", "en")
            st.markdown(f"**{t('ui.my_profile', lang)}**")
            st.write(f"{t('ui.email', lang)}: {email}")
            st.write(f"{t('ui.role', lang)}: {role}")

            if st.button(t("ui.log_out", lang), key="logout_from_popover", use_container_width=True):
                logout_and_forget()


def _trigger_simulation():
    st.session_state.running = True
    st.session_state.run_stage = "Connecting to PVGIS"
    st.session_state.run_progress = 0.0
    st.session_state.run_started_at = time.time()
    st.session_state.run_elapsed_seconds = 0.0
    st.session_state.run_eta_seconds = None
    st.session_state.trigger_run = True
    st.session_state.study_saved_for_current_result = False
    st.rerun()


def render_top_action_bar():
    lang = st.session_state.get("language", "en")
    st.markdown('<div class="top-action-wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="top-action-title">{t("ui.actions", lang)}</div>', unsafe_allow_html=True)

    ready = bool(st.session_state.get("study_ready", False))
    has_results = st.session_state.get("results") is not None
    is_running = bool(st.session_state.get("running", False))

    action_state = {
        "progress_bar": None,
        "progress_text": None,
        "stage_text": None,
        "timing_text": None,
        "status_box": None,
        "trust_note": None,
    }

    if is_running:
        st.markdown(f"**{t('ui.simulation_in_progress', lang)}**")
        st.markdown(
            f"<div class='secondary-note' style='margin-top:0;'>{t('ui.pvgis_basis_note', lang)}</div>",
            unsafe_allow_html=True,
        )

        progress_cols = st.columns([6, 1])
        with progress_cols[0]:
            action_state["progress_bar"] = st.progress(0)
        with progress_cols[1]:
            action_state["progress_text"] = st.empty()

        action_state["stage_text"] = st.empty()
        action_state["timing_text"] = st.empty()
        action_state["status_box"] = st.empty()
        action_state["trust_note"] = st.empty()

        pct = int(st.session_state.get("run_progress", 0))
        stage = st.session_state.get("run_stage", t("ui.initializing_simulation", lang))

        action_state["progress_bar"].progress(pct)
        action_state["progress_text"].markdown(
            f"<div style='text-align:right;font-weight:700;color:#667085;'>{pct}%</div>",
            unsafe_allow_html=True,
        )
        action_state["stage_text"].markdown(
            f"<div class='secondary-note'><b>{t('ui.current_step', lang)}</b> {stage}</div>",
            unsafe_allow_html=True,
        )
        elapsed_seconds = st.session_state.get("run_elapsed_seconds")
        eta_seconds = st.session_state.get("run_eta_seconds")
        if elapsed_seconds is not None:
            timing_parts = [t("ui.elapsed_time", lang, value=_format_duration(elapsed_seconds))]
            if eta_seconds is not None:
                timing_parts.append(t("ui.estimated_remaining", lang, value=_format_duration(eta_seconds)))
            action_state["timing_text"].markdown(
                f"<div class='secondary-note' style='margin-top:4px;'>{' · '.join(timing_parts)}</div>",
                unsafe_allow_html=True,
            )

        logs = st.session_state.get("run_log", [])
        if logs:
            log_html = "".join(
                [
                    f"<div style='padding:6px 0;border-bottom:1px solid #eef2f6;color:#344054;'>{line}</div>"
                    for line in logs[-6:]
                ]
            )
        else:
            log_html = f"<div style='color:#667085;'>{t('ui.initializing_simulation', lang)}</div>"

        action_state["status_box"].markdown(
            f"""
            <div style="
                border:1px solid #e6eaf0;
                border-radius:14px;
                background:#ffffff;
                padding:12px 14px;
                margin-top:10px;
                box-shadow:0 2px 10px rgba(16,24,40,0.04);
            ">
                <div style="font-size:0.88rem;font-weight:700;color:#344054;margin-bottom:8px;">
                    {t('ui.live_calculation_status', lang)}
                </div>
                {log_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        action_state["trust_note"].markdown(
            f"""
            <div style="
                margin-top:10px;
                border:1px solid #d6e4ff;
                border-radius:12px;
                background:#eef4ff;
                padding:10px 12px;
                color:#344054;
                font-size:0.93rem;
                line-height:1.45;
            ">
                <b>{t('ui.transparent_method_title', lang)}</b> {t('ui.transparent_method_body', lang)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif not has_results:
        c1, c2 = st.columns([1.4, 4])

        with c1:
            if st.button(
                t("ui.run_simulation", lang),
                type="primary",
                use_container_width=True,
                disabled=not ready,
                key="top_run_simulation",
            ):
                _trigger_simulation()

        with c2:
            if ready:
                st.markdown(
                    f'<div class="secondary-note">{t("ui.setup_complete_ready", lang)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="secondary-note">{t("ui.select_location_to_enable", lang)}</div>',
                    unsafe_allow_html=True,
                )

    else:
        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            if st.session_state.get("pdf_bytes") is not None:
                st.download_button(
                    f"📄 {t('ui.download_pdf_report', lang)}",
                    data=st.session_state.get("pdf_bytes"),
                    file_name=st.session_state.get(
                        "pdf_name", "SALA_report.pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True,
                    key="top_download_pdf_report",
                )

        with c2:
            if st.button(
                t("ui.run_updated_simulation", lang),
                type="primary",
                use_container_width=True,
                disabled=not ready,
                key="top_run_updated_simulation",
            ):
                _trigger_simulation()

        with c3:
            if st.button(
                t("ui.start_new_study", lang),
                use_container_width=True,
                key="top_start_new_study",
            ):
                reset_study()

        st.markdown(
            f'<div class="secondary-note">{t("ui.keep_location_note", lang)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return action_state


def maybe_save_current_study():
    results = st.session_state.get("results")
    if not results:
        return

    if st.session_state.get("study_saved_for_current_result", False):
        return

    user_id = st.session_state.get("auth_user_id")
    if not user_id:
        return

    days, pct, _ = annual_empty_battery_stats(results)
    state_value = overall_state(results)
    overall_result = state_value.upper() if state_value else "UNKNOWN"

    result_summary = {
        "overall_state": state_value,
        "worst_blackout_days": days,
        "worst_blackout_pct": pct,
        "results": results,
    }

    save_study(
        user_id=user_id,
        airport_label=st.session_state.get("airport_label", ""),
        lat=float(st.session_state.get("lat", 0)),
        lon=float(st.session_state.get("lon", 0)),
        required_hours=float(st.session_state.get("required_hours", 0)),
        operating_profile_mode=st.session_state.get("operating_profile_mode", ""),
        selected_devices=st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []),
        per_device_config=st.session_state.get("per_device_config", {}),
        overall_result=overall_result,
        worst_blackout_days=days,
        worst_blackout_pct=pct,
        result_summary=result_summary,
        pdf_name=st.session_state.get("pdf_name", "SALA_report.pdf"),
        pdf_bytes=st.session_state.get("pdf_bytes"),
    )

    st.session_state.study_saved_for_current_result = True


def _extract_energy_flow_payload(results, required_hours, overall, selected_ids):
    raw_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    lang = st.session_state.get("language", "en")
    months = month_labels(lang)

    selected_device_name = "Selected configuration"
    if selected_ids:
        first_id = selected_ids[0]
        if isinstance(first_id, str) and "||" in first_id:
            try:
                device_id_str, lamp_variant = first_id.split("||", 1)
                device_id = int(device_id_str)
                from core.devices import DEVICES
                selected_device_name = f"{DEVICES[device_id]['name']} / {lamp_variant}"
            except Exception:
                selected_device_name = str(first_id)
        else:
            selected_device_name = ", ".join(str(x) for x in selected_ids)

    worst_blackout_risk = "N/A"
    lowest_reserve_pct = 0
    worst_month = "N/A"

    reserve_pct = [48, 44, 58, 73, 86, 91, 94, 88, 71, 49, 24, 12]
    generated_monthly_wh = [280, 300, 410, 520, 610, 690, 720, 670, 520, 390, 260, 210]
    demand_monthly_wh = [420, 380, 420, 410, 420, 410, 420, 420, 410, 420, 410, 420]

    if not results:
        return {
            "selected_device_name": selected_device_name,
            "required_hours": float(required_hours or 12),
            "overall_result": overall or "N/A",
            "worst_blackout_risk": worst_blackout_risk,
            "lowest_reserve_pct": lowest_reserve_pct,
            "months": months,
            "reserve_pct": reserve_pct,
            "generated_monthly_wh": generated_monthly_wh,
            "demand_monthly_wh": demand_monthly_wh,
            "worst_month": worst_month,
        }

    first_key = next(iter(results.keys()))
    first_result = results[first_key] or {}

    worst_pct = None
    for _, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is not None:
            try:
                pct = float(pct)
                if worst_pct is None or pct > worst_pct:
                    worst_pct = pct
            except Exception:
                pass

    if worst_pct is not None:
        worst_days = round(365 * worst_pct / 100.0)
        worst_blackout_risk = f"{worst_days} {t('ui.days_per_year_unit', lang)}"

    monthly_reserve_candidates = [
        first_result.get("monthly_reserve_pct"),
        first_result.get("reserve_pct_by_month"),
        first_result.get("battery_reserve_pct_by_month"),
        first_result.get("monthly_battery_reserve_pct"),
    ]

    for candidate in monthly_reserve_candidates:
        if isinstance(candidate, (list, tuple)) and len(candidate) == 12:
            try:
                reserve_pct = [float(x) for x in candidate]
                break
            except Exception:
                pass

    monthly_generation_candidates = [
        first_result.get("monthly_generated_wh"),
        first_result.get("generated_wh_by_month"),
        first_result.get("monthly_generation_wh"),
        first_result.get("pv_output_wh_by_month"),
    ]

    for candidate in monthly_generation_candidates:
        if isinstance(candidate, (list, tuple)) and len(candidate) == 12:
            try:
                generated_monthly_wh = [float(x) for x in candidate]
                break
            except Exception:
                pass

    monthly_demand_candidates = [
        first_result.get("monthly_required_wh"),
        first_result.get("required_wh_by_month"),
        first_result.get("monthly_load_wh"),
        first_result.get("load_wh_by_month"),
    ]

    demand_found = False
    for candidate in monthly_demand_candidates:
        if isinstance(candidate, (list, tuple)) and len(candidate) == 12:
            try:
                demand_monthly_wh = [float(x) for x in candidate]
                demand_found = True
                break
            except Exception:
                pass

    if not demand_found:
        daily_wh = first_result.get("daily_consumption_wh")
        if daily_wh is None:
            hourly_wh = first_result.get("hourly_consumption_wh")
            if hourly_wh is not None:
                try:
                    daily_wh = float(hourly_wh) * float(required_hours or 12)
                except Exception:
                    daily_wh = None

        if daily_wh is not None:
            month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            try:
                demand_monthly_wh = [float(daily_wh) * d for d in month_days]
            except Exception:
                pass

    if reserve_pct:
        lowest_reserve_pct = min(reserve_pct)
        worst_idx = reserve_pct.index(lowest_reserve_pct)
        worst_month = month_label(raw_months[worst_idx], lang)

    device_name_candidates = [
        first_result.get("device_name"),
        first_result.get("label"),
        first_result.get("code"),
    ]
    for c in device_name_candidates:
        if c:
            selected_device_name = str(c)
            break

    return {
        "selected_device_name": selected_device_name,
        "required_hours": float(required_hours or 12),
        "overall_result": overall or "N/A",
        "worst_blackout_risk": worst_blackout_risk,
        "lowest_reserve_pct": lowest_reserve_pct,
        "months": months,
        "reserve_pct": reserve_pct,
        "generated_monthly_wh": generated_monthly_wh,
        "demand_monthly_wh": demand_monthly_wh,
        "worst_month": worst_month,
    }


def render_calculator_app():
    lang = st.session_state.get("language", "en")
    if st.session_state.get("running", False):
        with st.expander(t("ui.show_study_setup", lang), expanded=False):
            st.caption(t("ui.inputs_locked", lang))
    elif not st.session_state.get("results"):
        render_setup(disabled=False)
    else:
        with st.expander(t("ui.show_study_setup", lang), expanded=False):
            render_setup(disabled=False)

    refresh_study_ready_from_state()
    action_state = render_top_action_bar()

    if st.session_state.get("trigger_run"):
        st.session_state.trigger_run = False

        def progress_callback(percent: int, stage: str):
            percent = max(0, min(100, int(percent)))
            percent = max(int(st.session_state.get("run_progress", 0)), percent)
            st.session_state.run_progress = percent
            st.session_state.run_stage = stage
            started_at = st.session_state.get("run_started_at")
            if started_at:
                st.session_state.run_elapsed_seconds = max(0.0, time.time() - float(started_at))

            if action_state["progress_bar"] is not None:
                action_state["progress_bar"].progress(percent)

            if action_state["progress_text"] is not None:
                action_state["progress_text"].markdown(
                    f"<div style='text-align:right;font-weight:700;color:#667085;'>{percent}%</div>",
                    unsafe_allow_html=True,
                )

            if action_state["stage_text"] is not None:
                action_state["stage_text"].markdown(
                    f"<div class='secondary-note'><b>{t('ui.current_step', lang)}</b> {stage}</div>",
                    unsafe_allow_html=True,
                )

            if action_state["timing_text"] is not None:
                elapsed_seconds = st.session_state.get("run_elapsed_seconds")
                eta_seconds = st.session_state.get("run_eta_seconds")
                if elapsed_seconds is not None:
                    timing_parts = [t("ui.elapsed_time", lang, value=_format_duration(elapsed_seconds))]
                    if eta_seconds is not None:
                        timing_parts.append(t("ui.estimated_remaining", lang, value=_format_duration(eta_seconds)))
                    action_state["timing_text"].markdown(
                        f"<div class='secondary-note' style='margin-top:4px;'>{' · '.join(timing_parts)}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    action_state["timing_text"].empty()

            if action_state["status_box"] is not None:
                logs = st.session_state.get("run_log", [])
                if logs:
                    log_html = "".join(
                        [
                            f"<div style='padding:6px 0;border-bottom:1px solid #eef2f6;color:#344054;'>{line}</div>"
                            for line in logs[-6:]
                        ]
                    )
                else:
                    log_html = f"<div style='color:#667085;'>{t('ui.initializing_simulation', lang)}</div>"

                action_state["status_box"].markdown(
                    f"""
                    <div style="
                        border:1px solid #e6eaf0;
                        border-radius:14px;
                        background:#ffffff;
                        padding:12px 14px;
                        margin-top:10px;
                        box-shadow:0 2px 10px rgba(16,24,40,0.04);
                    ">
                        <div style="font-size:0.88rem;font-weight:700;color:#344054;margin-bottom:8px;">
                            {t('ui.live_calculation_status', lang)}
                        </div>
                        {log_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        _run_simulation(progress_callback=progress_callback)

    if st.session_state.get("results") is not None:
        maybe_save_current_study()

        results = st.session_state.get("results")
        render_result()
        render_graph()
        render_device_capability_cards(results)
        render_weather_basis()


init_state()
init_auth_state()
bootstrap_admin_user()
restore_login_from_query_token()
apply_global_styles()

if not is_logged_in():
    from ui.login_page import render_login_page
    render_login_page()
    st.stop()

persist_login_to_query_token()
render_header()

user_id = st.session_state.get("auth_user_id")

if is_admin():
    lang = st.session_state.get("language", "en")
    tab_calc, tab_my, tab_admin = st.tabs([t("tabs.feasibility", lang), t("tabs.my_studies", lang), t("tabs.admin", lang)])

    with tab_calc:
        render_calculator_app()

    with tab_my:
        render_my_studies(user_id)

    with tab_admin:
        render_admin_panel()
else:
    lang = st.session_state.get("language", "en")
    tab_calc, tab_my = st.tabs([t("tabs.feasibility", lang), t("tabs.my_studies", lang)])

    with tab_calc:
        render_calculator_app()

    with tab_my:
        render_my_studies(user_id)
