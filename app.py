import os
import json
import time
import hmac
import base64
import hashlib
from pathlib import Path
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from core.i18n import AVAILABLE_LANGUAGES, month_label, month_labels, t

from core.db import init_db, upsert_user, save_study, update_study, get_study, get_user_by_email, save_running_study_checkpoint, list_user_studies
from core.catalog import get_runtime_devices
from core.person import normalize_person_name
from core.auth import hash_password, init_auth_state, is_logged_in, is_admin, logout

from ui.setup import render_setup
from ui.cockpit import _run_simulation, regenerate_pdf_for_current_results, reset_study
from ui.result import render_result
from ui.admin import render_admin_panel
from ui.my_studies import render_my_studies
from ui.result_helpers import annual_empty_battery_stats, overall_state


APP_DIR = Path(__file__).resolve().parent
FAVICON_PATH = APP_DIR / "sala_favicon.png"
LOGO_FILE_PATH = APP_DIR / "sala_logo.png"

st.set_page_config(
    page_title="SALA Standardized Feasibility Study for Solar AGL",
    page_icon=str(FAVICON_PATH),
    layout="wide",
)

LOGO_PATH = str(LOGO_FILE_PATH)
LANGUAGE_FLAGS = {
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
}
DEFAULT_LAT = 40.416775
DEFAULT_LON = -3.703790
DEFAULT_MANUFACTURER = "S4GA"

# ---- Persistent auth via signed URL token ----
# This survives Streamlit restarts because it is stored in the browser URL.
# It is not as strong as HttpOnly cookies, but it works without extra packages.
AUTH_QUERY_PARAM = "auth"
STUDY_QUERY_PARAM = "study"
AUTH_TOKEN_TTL_DAYS = 30
RUN_STALL_TIMEOUT_SECONDS = 180
STABILITY_ROLLBACK_MODE = os.getenv("SALA_STABILITY_ROLLBACK", "1") not in {"0", "false", "False"}


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


def _query_param_value(name: str):
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _set_auth_query_token(token: str | None):
    qp = st.query_params
    current = _query_param_value(AUTH_QUERY_PARAM)
    target = str(token) if token else None
    if current == target:
        return
    if target:
        qp[AUTH_QUERY_PARAM] = target
    else:
        try:
            del qp[AUTH_QUERY_PARAM]
        except Exception:
            if _query_param_value(AUTH_QUERY_PARAM):
                qp[AUTH_QUERY_PARAM] = ""


def _set_study_query_id(study_id: int | str | None):
    qp = st.query_params
    current = _query_param_value(STUDY_QUERY_PARAM)
    target = str(study_id) if study_id else None
    if current == target:
        return
    if target:
        qp[STUDY_QUERY_PARAM] = target
    else:
        try:
            del qp[STUDY_QUERY_PARAM]
        except Exception:
            if _query_param_value(STUDY_QUERY_PARAM):
                qp[STUDY_QUERY_PARAM] = ""


def restore_login_from_query_token():
    if is_logged_in():
        return

    token = _query_param_value(AUTH_QUERY_PARAM)
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

    current = _query_param_value(AUTH_QUERY_PARAM)
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
    _set_study_query_id(None)
    logout()


def restore_study_from_query_id():
    if not is_logged_in():
        return

    raw_study_id = _query_param_value(STUDY_QUERY_PARAM)
    if not raw_study_id:
        return

    try:
        study_id = int(str(raw_study_id))
    except Exception:
        _set_study_query_id(None)
        return

    if (
        st.session_state.get("results") is not None
        and str(st.session_state.get("active_study_id") or "") == str(study_id)
    ):
        return

    row = get_study(study_id, user_id=st.session_state.get("auth_user_id"))
    if not row:
        _set_study_query_id(None)
        return

    result_summary_raw = row.get("result_summary_json")
    try:
        result_summary = json.loads(result_summary_raw) if result_summary_raw else {}
    except Exception:
        result_summary = {}

    results = result_summary.get("results")
    simulation_job = result_summary.get("simulation_job") or None
    try:
        simulation_timing = json.loads(row.get("simulation_timing_json") or "{}")
    except Exception:
        simulation_timing = result_summary.get("simulation_timing") or {}

    selected_devices_raw = row.get("selected_devices_json")
    per_device_config_raw = row.get("per_device_config_json")
    try:
        selected_devices = json.loads(selected_devices_raw) if selected_devices_raw else []
    except Exception:
        selected_devices = []
    try:
        per_device_config = json.loads(per_device_config_raw) if per_device_config_raw else {}
    except Exception:
        per_device_config = {}
    if not selected_devices and isinstance(per_device_config, dict):
        selected_devices = list(per_device_config.keys())

    base_device_ids, lamp_types_by_device, manufacturers = _restore_selection_state_from_saved_devices(selected_devices)
    _clear_setup_widget_state_before_study_restore(selected_devices, base_device_ids)

    st.session_state.airport_label = row.get("airport_label") or ""
    st.session_state.airport_query = row.get("airport_label") or ""
    st.session_state.airport_query_input = row.get("airport_label") or ""
    st.session_state.language = row.get("language") or st.session_state.get("language", "en")
    st.session_state.lat = float(row.get("lat", 0) or 0)
    st.session_state.lon = float(row.get("lon", 0) or 0)
    st.session_state.required_hours = float(row.get("required_hours", 0) or 0)
    st.session_state.required_custom_hours_input = float(row.get("required_hours", 0) or 0)
    st.session_state.operating_profile_mode = row.get("operating_profile_mode") or st.session_state.get("operating_profile_mode")
    st.session_state.operating_profile_mode_radio = st.session_state.operating_profile_mode
    st.session_state.selected_simulation_keys = selected_devices
    st.session_state.selected_ids = base_device_ids
    st.session_state.selected_ids_widget = list(base_device_ids)
    st.session_state.selected_manufacturers = manufacturers
    st.session_state.selected_manufacturers_widget = list(manufacturers)
    st.session_state.selected_lamp_types = lamp_types_by_device
    st.session_state.per_device_config = per_device_config
    st.session_state.active_study_id = study_id
    st.session_state.active_study_name = row.get("study_name")
    st.session_state.active_study_version = row.get("study_version")
    st.session_state.active_study_base_label = row.get("base_airport_label") or row.get("airport_label")
    st.session_state.simulation_timing = simulation_timing if isinstance(simulation_timing, dict) else {}
    st.session_state.study_point_confirmed = True
    st.session_state.study_location = {
        "label": st.session_state.airport_label,
        "query": st.session_state.airport_query,
        "lat": st.session_state.lat,
        "lon": st.session_state.lon,
        "icao": st.session_state.airport_icao,
        "country": st.session_state.get("airport_country", "-"),
    }
    st.session_state.active_simulation_job = simulation_job
    if results:
        overall_value = row.get("overall_result") or result_summary.get("overall_state")
        if str(overall_value or "").upper() in {"RUNNING", "PENDING"}:
            st.session_state.results = None
            st.session_state.overall = None
            st.session_state.partial_results = results
            st.session_state.partial_overall = overall_value
            st.session_state.pdf_name = "SALA_report.pdf"
            st.session_state.pdf_bytes = None
            st.session_state.pdf_error = None
            st.session_state.study_saved_for_current_result = False
            st.session_state.run_error = t("ui.simulation_interrupted_recoverable", st.session_state.get("language", "en"))
            st.session_state.simulation_resume_required = True
            st.session_state.simulation_auto_continue = False
        else:
            st.session_state.results = results
            st.session_state.overall = overall_value
            st.session_state.partial_results = None
            st.session_state.partial_overall = None
            st.session_state.pdf_name = row.get("pdf_name") or "SALA_report.pdf"
            st.session_state.pdf_bytes = row.get("pdf_bytes")
            st.session_state.pdf_error = None
            st.session_state.study_saved_for_current_result = True
            st.session_state.active_simulation_job = None
            st.session_state.simulation_resume_required = False
            st.session_state.simulation_auto_continue = False
    else:
        st.session_state.results = None
        st.session_state.overall = None
        st.session_state.partial_results = None
        st.session_state.partial_overall = None
        st.session_state.pdf_bytes = None
        st.session_state.pdf_name = "SALA_report.pdf"
        st.session_state.pdf_error = None
        st.session_state.study_saved_for_current_result = False
        if str(row.get("overall_result") or "").upper() in {"RUNNING", "PENDING"}:
            st.session_state.run_error = t("ui.simulation_interrupted_recoverable", st.session_state.get("language", "en"))
            st.session_state.simulation_resume_required = True
            st.session_state.simulation_auto_continue = False
        else:
            st.session_state.active_simulation_job = None
            st.session_state.simulation_resume_required = False
            st.session_state.simulation_auto_continue = False
    refresh_study_ready_from_state()


def _restore_selection_state_from_saved_devices(selected_devices):
    device_ids = []
    lamp_types_by_device = {}
    manufacturers = set()
    runtime_devices = {}
    try:
        runtime_devices = get_runtime_devices()
    except Exception:
        runtime_devices = {}

    for item in selected_devices or []:
        raw = str(item)
        variant = None
        device_raw = raw
        if "||" in raw:
            device_raw, variant = raw.split("||", 1)

        try:
            device_id = int(device_raw)
        except Exception:
            continue

        if device_id not in device_ids:
            device_ids.append(device_id)

        if variant:
            lamp_types_by_device.setdefault(device_id, [])
            if variant not in lamp_types_by_device[device_id]:
                lamp_types_by_device[device_id].append(variant)

        device_spec = runtime_devices.get(device_id) if runtime_devices else None
        if device_spec:
            manufacturers.add(device_spec.get("manufacturer", "Unknown"))

    return device_ids, lamp_types_by_device, sorted(manufacturers)


def _clear_setup_widget_state_before_study_restore(selected_devices, base_device_ids):
    keys_to_pop = {
        "airport_query_input",
        "airport_icao_input",
        "required_custom_hours_input",
        "operating_profile_mode_radio",
        "ui_language_selector",
        "selected_ids_widget",
        "selected_manufacturers_widget",
        "device_search_filter",
    }
    dynamic_prefixes = (
        "variant_enabled_",
        "intensity_mode_",
        "mixed_share_",
        "mixed_intensity_a_",
        "mixed_rest_",
        "mixed_intensity_b_",
        "intensity_pct_",
        "power_",
        "quantity_",
        "engine_",
        "battery_mode_",
    )
    saved_keys = {str(item) for item in (selected_devices or [])}
    saved_keys.update(str(item) for item in (base_device_ids or []))

    for key in list(st.session_state.keys()):
        key_str = str(key)
        if key_str in keys_to_pop:
            st.session_state.pop(key, None)
            continue
        if key_str.startswith(dynamic_prefixes):
            for saved_key in saved_keys:
                if key_str.endswith(saved_key) or f"_{saved_key}_" in key_str or f"_{saved_key}" in key_str:
                    st.session_state.pop(key, None)
                    break


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


def _base_study_label() -> str:
    return (st.session_state.get("airport_label") or st.session_state.get("airport_query") or "Unnamed study").strip()


def _next_study_version(user_id, base_label: str) -> tuple[int, str]:
    normalized = " ".join(str(base_label or "Unnamed study").lower().split())
    max_version = 0
    try:
        rows = list_user_studies(user_id)
    except Exception:
        rows = []
    for row in rows:
        row_base = row.get("base_airport_label") or row.get("airport_label") or row.get("study_name") or ""
        if " ".join(str(row_base).lower().split()) != normalized:
            continue
        try:
            max_version = max(max_version, int(row.get("study_version") or 0))
        except Exception:
            max_version += 1
    version = max_version + 1
    return version, f"{base_label or 'Unnamed study'} v{version:02d}"


def _mark_run_failed(message: str):
    lang = st.session_state.get("language", "en")
    logs = st.session_state.get("run_log", [])
    logs.append(f"**{time.strftime('%H:%M:%S')}** — {message}")
    st.session_state.run_log = logs[-6:]
    st.session_state.running = False
    st.session_state.trigger_run = False
    st.session_state.run_stage = t("ui.failed", lang)
    st.session_state.run_eta_seconds = None
    st.session_state.run_last_update_at = time.time()
    st.session_state.run_error = message
    if st.session_state.get("active_simulation_job"):
        st.session_state.simulation_resume_required = True
        st.session_state.simulation_auto_continue = False


def _recover_stalled_run_if_needed():
    if not st.session_state.get("running"):
        return
    if st.session_state.get("results") is not None:
        return
    if st.session_state.get("trigger_run"):
        return

    last_update = st.session_state.get("run_last_update_at") or st.session_state.get("run_started_at")
    if not last_update:
        return

    stalled_for = time.time() - float(last_update)
    if stalled_for < RUN_STALL_TIMEOUT_SECONDS:
        return

    lang = st.session_state.get("language", "en")
    message = t("ui.simulation_interrupted", lang, seconds=_format_duration(stalled_for))
    _mark_run_failed(message)


def init_state():
    defaults = {
        "airport_label": "",
        "airport_query": "",
        "airport_icao": "",
        "language": "en",
        "lat": DEFAULT_LAT,
        "lon": DEFAULT_LON,
        "required_hours": 12.0,
        "operating_profile_mode": "Custom hours per day",
        "selected_ids": [],
        "selected_ids_widget": [],
        "selected_manufacturers": [DEFAULT_MANUFACTURER],
        "selected_manufacturers_widget": [DEFAULT_MANUFACTURER],
        "selected_simulation_keys": [],
        "per_device_config": {},
        "selected_lamp_types": {},
        "airport_query_input": "",
        "airport_icao_input": "",
        "study_location": None,
        "last_airport_query": "",
        "last_map_click": None,
        "map_click_pending_rerender": False,
        "show_map_picker": False,
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "SALA_report.pdf",
        "pdf_error": None,
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
        "run_last_update_at": None,
        "run_error": None,
        "trigger_run": False,
        "study_point_confirmed": False,
        "study_ready": False,
        "study_saved_for_current_result": False,
        "simulation_cache_key": None,
        "simulation_cache_results": None,
        "simulation_cache_overall": None,
        "simulation_cache_pdf_context": None,
        "simulation_timing": {},
        "active_study_id": None,
        "active_study_name": None,
        "active_study_version": None,
        "active_study_base_label": None,
        "partial_results": None,
        "partial_overall": None,
        "active_simulation_job": None,
        "simulation_resume_required": False,
        "simulation_auto_continue": False,
        "include_aging_analysis": False,
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
            full_name = str(st.session_state.get("auth_full_name") or "").strip()
            organization = str(st.session_state.get("auth_organization") or "").strip()
            if full_name:
                st.write(f"{t('ui.full_name', lang)}: {full_name}")
            if organization:
                st.write(f"{t('ui.organization', lang)}: {organization}")

            if st.button(t("ui.log_out", lang), key="logout_from_popover", use_container_width=True):
                logout_and_forget()


def _trigger_simulation():
    now = time.time()
    st.session_state.active_study_id = None
    st.session_state.results = None
    st.session_state.overall = None
    st.session_state.pdf_bytes = None
    st.session_state.pdf_name = "SALA_report.pdf"
    st.session_state.running = True
    st.session_state.run_stage = "Connecting to PVGIS"
    st.session_state.run_progress = 0.0
    st.session_state.run_started_at = now
    st.session_state.run_elapsed_seconds = 0.0
    st.session_state.run_eta_seconds = None
    st.session_state.run_last_update_at = now
    st.session_state.run_error = None
    st.session_state.trigger_run = True
    st.session_state.study_saved_for_current_result = False
    st.session_state.pdf_error = None
    st.session_state.simulation_timing = {}
    st.session_state.partial_results = {}
    st.session_state.partial_overall = "RUNNING"
    selected_devices = list(st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []))
    st.session_state.active_simulation_job = {
        "status": "RUNNING",
        "selected_devices": selected_devices,
        "current_device_index": 0,
        "total_devices": len(selected_devices),
        "completed_device_keys": [],
    }
    st.session_state.simulation_resume_required = False
    st.session_state.simulation_auto_continue = True
    st.session_state.simulation_cache_key = None
    st.session_state.simulation_cache_results = None
    st.session_state.simulation_cache_overall = None
    st.session_state.simulation_cache_pdf_context = None
    ensure_active_study_record()
    save_running_checkpoint({}, st.session_state.active_simulation_job)
    st.rerun()


def _resume_simulation_job():
    if not st.session_state.get("active_simulation_job"):
        return
    now = time.time()
    st.session_state.results = None
    st.session_state.overall = None
    st.session_state.pdf_bytes = None
    st.session_state.pdf_name = "SALA_report.pdf"
    st.session_state.running = True
    st.session_state.run_stage = t("ui.preparing_simulation", st.session_state.get("language", "en"))
    st.session_state.run_progress = 0.0
    st.session_state.run_started_at = now
    st.session_state.run_elapsed_seconds = 0.0
    st.session_state.run_eta_seconds = None
    st.session_state.run_last_update_at = now
    st.session_state.run_error = None
    st.session_state.trigger_run = True
    st.session_state.simulation_resume_required = False
    st.session_state.simulation_auto_continue = True
    st.rerun()


def render_top_action_bar():
    lang = st.session_state.get("language", "en")
    st.markdown('<div class="top-action-wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="top-action-title">{t("ui.actions", lang)}</div>', unsafe_allow_html=True)

    ready = bool(st.session_state.get("study_ready", False))
    has_results = st.session_state.get("results") is not None
    is_running = bool(st.session_state.get("running", False))
    active_job = st.session_state.get("active_simulation_job") or {}
    resume_required = bool(st.session_state.get("simulation_resume_required", False) and active_job)
    if has_results and is_running and not st.session_state.get("trigger_run"):
        st.session_state.running = False
        st.session_state.trigger_run = False
        is_running = False

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
        if active_job:
            current_index = int(active_job.get("current_device_index", 0))
            total_devices = max(1, int(active_job.get("total_devices", 0) or len(active_job.get("selected_devices", [])) or 1))
            completed_devices = list(active_job.get("completed_device_keys", []))
            selected_devices = list(active_job.get("selected_devices", []))
            current_device_name = (
                str(selected_devices[current_index])
                if 0 <= current_index < len(selected_devices)
                else t("ui.finalizing_results", lang)
            )
            action_state["stage_text"].markdown(
                f"""
                <div class='secondary-note'><b>{t('ui.current_step', lang)}</b> {stage}</div>
                <div class='secondary-note' style='margin-top:4px;'><b>{t('ui.processing_device_progress', lang, current=min(current_index + 1, total_devices), total=total_devices)}</b></div>
                <div class='secondary-note' style='margin-top:4px;'>{t('ui.current_device_name', lang, name=current_device_name)}</div>
                <div class='secondary-note' style='margin-top:4px;'>{t('ui.completed_devices_list', lang, names=', '.join(completed_devices) if completed_devices else t('ui.none', lang))}</div>
                """,
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
            <div style="
                margin-top:10px;
                border:1px solid #fde68a;
                border-radius:12px;
                background:#fffbeb;
                padding:10px 12px;
                color:#92400e;
                font-size:0.93rem;
                line-height:1.45;
            ">
                {t('ui.do_not_close_page', lang)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif not has_results:
        run_error = st.session_state.get("run_error")
        if run_error:
            st.error(run_error)

        c1, c2 = st.columns([1.4, 4])

        with c1:
            if resume_required:
                if st.button(
                    t("ui.resume_simulation", lang),
                    type="primary",
                    use_container_width=True,
                    key="top_resume_simulation",
                ):
                    _resume_simulation_job()
            else:
                if st.button(
                    t("ui.run_simulation", lang),
                    type="primary",
                    use_container_width=True,
                    disabled=not ready,
                    key="top_run_simulation",
                ):
                    _trigger_simulation()

        with c2:
            if resume_required:
                completed = len(active_job.get("completed_device_keys", []))
                total = max(1, int(active_job.get("total_devices", 0) or len(active_job.get("selected_devices", [])) or 1))
                st.markdown(
                    f'<div class="secondary-note">{t("ui.resume_simulation_note", lang, completed=completed, total=total)}</div>',
                    unsafe_allow_html=True,
                )
            elif ready:
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
            else:
                pdf_error = st.session_state.get("pdf_error")
                if pdf_error:
                    st.warning(t("ui.pdf_generation_failed", lang, error=pdf_error))
                else:
                    st.warning(t("ui.pdf_not_ready", lang))

                if st.button(
                    t("ui.generate_pdf_report", lang),
                    use_container_width=True,
                    key="top_generate_pdf_report",
                ):
                    try:
                        regenerate_pdf_for_current_results()
                    except Exception as exc:
                        st.session_state.pdf_error = str(exc)
                    st.rerun()

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
                _set_study_query_id(None)
                st.session_state.active_study_id = None
                reset_study()

        st.markdown(
            f'<div class="secondary-note">{t("ui.keep_location_note", lang)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return action_state


def render_top_new_study_control():
    if st.session_state.get("running") or st.session_state.get("trigger_run"):
        return
    lang = st.session_state.get("language", "en")
    has_any_study_state = any([
        st.session_state.get("airport_label"),
        st.session_state.get("airport_query"),
        st.session_state.get("selected_ids"),
        st.session_state.get("selected_simulation_keys"),
        st.session_state.get("results") is not None,
        st.session_state.get("active_study_id"),
    ])
    if not has_any_study_state:
        return
    cols = st.columns([1, 2.8])
    with cols[0]:
        if st.button(t("ui.start_new_study", lang), key="quick_start_new_study", use_container_width=True):
            _set_study_query_id(None)
            reset_study()


def ensure_active_study_record():
    if st.session_state.get("active_study_id"):
        return st.session_state.get("active_study_id")

    user_id = st.session_state.get("auth_user_id")
    if not user_id:
        return None

    base_label = _base_study_label()
    study_version, study_name = _next_study_version(user_id, base_label)

    study_id = save_study(
        user_id=user_id,
        airport_label=base_label,
        lat=float(st.session_state.get("lat", 0)),
        lon=float(st.session_state.get("lon", 0)),
        required_hours=float(st.session_state.get("required_hours", 0)),
        operating_profile_mode=st.session_state.get("operating_profile_mode", ""),
        selected_devices=st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []),
        per_device_config=st.session_state.get("per_device_config", {}),
        overall_result="RUNNING",
        worst_blackout_days=None,
        worst_blackout_pct=None,
        result_summary={"overall_state": "running", "results": None},
        pdf_name=None,
        pdf_bytes=None,
        study_name=study_name,
        study_version=study_version,
        base_airport_label=base_label,
        language=st.session_state.get("language", "en"),
        simulation_timing=st.session_state.get("simulation_timing") or {},
    )
    if study_id:
        st.session_state.active_study_id = study_id
        st.session_state.active_study_name = study_name
        st.session_state.active_study_version = study_version
        st.session_state.active_study_base_label = base_label
        _set_study_query_id(study_id)
    return study_id


def _save_running_checkpoint_impl(partial_results=None):
    active_study_id = st.session_state.get("active_study_id")
    user_id = st.session_state.get("auth_user_id")
    if not active_study_id or not user_id:
        return None

    return save_running_study_checkpoint(
        study_id=active_study_id,
        user_id=user_id,
        airport_label=st.session_state.get("airport_label", ""),
        lat=float(st.session_state.get("lat", 0)),
        lon=float(st.session_state.get("lon", 0)),
        required_hours=float(st.session_state.get("required_hours", 0)),
        operating_profile_mode=st.session_state.get("operating_profile_mode", ""),
        selected_devices=st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []),
        per_device_config=st.session_state.get("per_device_config", {}),
        partial_results=partial_results if partial_results is not None else st.session_state.get("partial_results"),
        simulation_job=st.session_state.get("active_simulation_job"),
        study_name=st.session_state.get("active_study_name"),
        study_version=st.session_state.get("active_study_version"),
        base_airport_label=st.session_state.get("active_study_base_label") or _base_study_label(),
        language=st.session_state.get("language", "en"),
        simulation_timing=st.session_state.get("simulation_timing") or {},
    )


def save_running_checkpoint(partial_results=None, simulation_job=None):
    if simulation_job is not None:
        st.session_state.active_simulation_job = simulation_job
    return _save_running_checkpoint_impl(partial_results)


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
        "simulation_job": None,
        "simulation_timing": st.session_state.get("simulation_timing") or {},
    }

    active_study_id = st.session_state.get("active_study_id")
    save_fn = update_study if active_study_id else save_study
    save_kwargs = dict(
        user_id=user_id,
        airport_label=_base_study_label(),
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
        language=st.session_state.get("language", "en"),
        simulation_timing=st.session_state.get("simulation_timing") or {},
    )
    if active_study_id:
        save_kwargs["study_id"] = active_study_id
        save_kwargs["study_name"] = st.session_state.get("active_study_name")
        save_kwargs["study_version"] = st.session_state.get("active_study_version")
        save_kwargs["base_airport_label"] = st.session_state.get("active_study_base_label") or _base_study_label()
    study_id = save_fn(**save_kwargs)

    st.session_state.study_saved_for_current_result = True
    if study_id:
        _set_study_query_id(study_id)


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

    # No fake placeholder data: until a real result row is available, the
    # charts show a flat/empty state rather than fabricated-looking curves.
    reserve_pct = [0.0] * 12
    generated_monthly_wh = [0.0] * 12
    demand_monthly_wh = [0.0] * 12

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

    # Battery reserve (%) by month — actual simulation output from
    # core/simulate.py's _battery_behavior_metrics(), not a guessed key name.
    reserve_candidate = first_result.get("soc_monthly_avg")
    if isinstance(reserve_candidate, (list, tuple)) and len(reserve_candidate) == 12:
        try:
            reserve_pct = [float(x) for x in reserve_candidate]
        except Exception:
            pass

    # Generation (Wh/day) by month — same monthly generation basis used to
    # drive the feasibility calculation itself.
    generation_candidate = first_result.get("monthly_generation_wh_day")
    if isinstance(generation_candidate, (list, tuple)) and len(generation_candidate) == 12:
        try:
            generated_monthly_wh = [float(x) for x in generation_candidate]
        except Exception:
            pass

    # Demand (Wh/day) is constant across months — the operating profile's
    # required hours don't vary seasonally — so use the precomputed daily
    # discharge, falling back to power * required_hours if it's missing.
    daily_demand_wh = first_result.get("avg_daily_energy_out_wh")
    if daily_demand_wh is None:
        try:
            daily_demand_wh = float(first_result.get("power", 0) or 0) * float(required_hours or 0)
        except Exception:
            daily_demand_wh = None
    if daily_demand_wh is not None:
        try:
            demand_monthly_wh = [float(daily_demand_wh)] * 12
        except Exception:
            pass

    if reserve_pct:
        lowest_reserve_pct = min(reserve_pct)
        worst_idx = reserve_pct.index(lowest_reserve_pct)
        worst_month = month_label(raw_months[worst_idx], lang)

    device_name_candidates = [
        first_result.get("name"),
        first_result.get("device_code"),
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
    if st.session_state.get("auth_token_refresh_required"):
        persist_login_to_query_token()
        st.session_state.auth_token_refresh_required = False
    _recover_stalled_run_if_needed()
    active_job = st.session_state.get("active_simulation_job") or {}
    resume_required = bool(st.session_state.get("simulation_resume_required") and active_job)
    if (
        active_job
        and str(active_job.get("status", "")).upper() == "RUNNING"
        and st.session_state.get("simulation_auto_continue")
        and not st.session_state.get("trigger_run")
        and st.session_state.get("results") is None
    ):
        st.session_state.running = True
        st.session_state.trigger_run = True
    render_top_new_study_control()
    if st.session_state.get("running", False):
        with st.expander(t("ui.show_study_setup", lang), expanded=False):
            st.caption(t("ui.inputs_locked", lang))
    elif resume_required:
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
            st.session_state.run_last_update_at = time.time()

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

        try:
            _run_simulation(progress_callback=progress_callback)
        except Exception as exc:
            _mark_run_failed(t("ui.simulation_failed", lang, error=str(exc)))
            st.rerun()

    if st.session_state.get("results") is not None:
        st.session_state.running = False
        st.session_state.trigger_run = False
        st.session_state.run_error = None
        maybe_save_current_study()

        results = st.session_state.get("results")
        render_result()

        if STABILITY_ROLLBACK_MODE:
            st.info("Advanced result sections are temporarily disabled in stability mode.")
        else:
            from ui.result import render_device_capability_cards
            from ui.weather_basis import render_weather_basis
            from ui.graph import render_graph

            try:
                render_device_capability_cards(results)
            except Exception as exc:
                st.error(f"Per-device result render failed: {exc}")

            st.divider()

            try:
                render_weather_basis()
            except Exception as exc:
                st.error(f"Methodology render failed: {exc}")

            st.divider()

            try:
                render_graph()
            except Exception as exc:
                st.error(f"Annual graph render failed: {exc}")


init_state()
init_auth_state()
bootstrap_admin_user()
restore_login_from_query_token()
restore_study_from_query_id()
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
