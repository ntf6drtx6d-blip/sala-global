
import os
import time
import tempfile

import streamlit as st

from core.simulate import simulate_for_devices
from core.devices import DEVICES
from core.i18n import t
from core.time_utils import format_clock_timestamp, now_local
from report.report import make_pdf
EU_LOGO_PATH = "logo_en.gif"


def format_seconds(seconds):
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def now_ts():
    return format_clock_timestamp(with_timezone=True)


def short_device_label_from_id(device_id):
    try:
        d = DEVICES[device_id]
        return d.get("code", str(device_id))
    except Exception:
        return str(device_id)


def pvgis_short_card():
    lang = st.session_state.get("language", "en")
    st.markdown(
        f"""
        <div style="
            border:1px solid #d9e2ef;
            border-radius:14px;
            padding:12px 14px;
            background:#f8fbff;
            margin-top:4px;
            margin-bottom:8px;">
            <div style="font-weight:700; color:#12355b; margin-bottom:5px;">
                {t("ui.powered_by_pvgis", lang)}
            </div>
            <div style="font-size:0.90rem; color:#475467; line-height:1.45;">
                <b>{t("ui.pvgis_full_name", lang)}</b><br/>
                {t("ui.pvgis_jrc_line", lang)}<br/>
                {t("ui.pvgis_dataset_line", lang, dataset="<b>PVGIS-SARAH3</b>")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def reset_study():
    lang = st.session_state.get("language", "en")
    auth_keys = {
        "auth_ok": st.session_state.get("auth_ok", False),
        "auth_user_id": st.session_state.get("auth_user_id"),
        "auth_email": st.session_state.get("auth_email"),
        "auth_role": st.session_state.get("auth_role"),
        "auth_full_name": st.session_state.get("auth_full_name"),
    }

    keep = {
        "airport_label": "",
        "airport_query": "",
        "airport_icao": "",
        "language": st.session_state.get("language", "en"),
        "lat": st.session_state.get("lat", 40.416775),
        "lon": st.session_state.get("lon", -3.703790),
        "required_hours": 12.0,
        "operating_profile_mode": t("ui.mode_custom", lang),
        "selected_ids": [],
        "selected_simulation_keys": [],
        "per_device_config": {},
        "search_message": "",
        "map_click_info": "",
        "study_point_confirmed": False,
        "study_ready": False,
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "SALA_report.pdf",
        "elapsed": None,
        "running": False,
        "run_progress": 0,
        "run_stage": t("ui.ready", lang),
        "run_log": [],
        "run_started_at": None,
        "run_elapsed_seconds": None,
        "run_eta_seconds": None,
        "trigger_run": False,
        "study_saved_for_current_result": False,
    }

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    for k, v in auth_keys.items():
        st.session_state[k] = v
    for k, v in keep.items():
        st.session_state[k] = v

    st.rerun()


def _run_simulation(progress_callback=None):
    lang = st.session_state.get("language", "en")
    st.session_state.running = True
    st.session_state.run_stage = t("ui.preparing_simulation", lang)
    st.session_state.run_progress = 0
    st.session_state.run_log = []
    st.session_state.run_started_at = time.time()
    st.session_state.run_elapsed_seconds = 0.0
    st.session_state.run_eta_seconds = None

    def add_log(message):
        logs = st.session_state.get("run_log", [])
        logs.append(f"**{now_ts()}** — {message}")
        st.session_state.run_log = logs[-5:]

    def render_stage(percent):
        if percent < 10:
            return t("ui.stage_validating_inputs", lang)
        elif percent < 25:
            return t("ui.stage_preparing_requests", lang)
        elif percent < 45:
            return t("ui.stage_requesting_data", lang)
        elif percent < 70:
            return t("ui.stage_checking_monthly", lang)
        elif percent < 90:
            return t("ui.stage_calculating_feasibility", lang)
        return t("ui.stage_generating_results", lang)

    def push_progress(percent, stage):
        percent = max(0, min(100, int(percent)))
        percent = max(int(st.session_state.get("run_progress", 0)), percent)
        st.session_state.run_progress = percent
        st.session_state.run_stage = stage
        if progress_callback:
            progress_callback(percent, stage)

    add_log(t("ui.log_checking_airport_inputs", lang))
    push_progress(5, t("ui.stage_validating_inputs", lang))

    add_log(t("ui.log_preparing_request_parameters", lang))
    push_progress(12, t("ui.stage_preparing_requests", lang))

    loc = {
        "lat": st.session_state.lat,
        "lon": st.session_state.lon,
        "label": st.session_state.airport_label or f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
        "country": st.session_state.get("airport_country", ""),
        "icao": st.session_state.get("airport_icao", ""),
    }

    started = time.time()

    def simulation_progress(done, total, pct, elapsed, eta, device_name, month_name):
        percent = int(pct * 100)
        st.session_state.run_elapsed_seconds = max(0.0, float(elapsed or 0.0))
        st.session_state.run_eta_seconds = max(0.0, float(eta or 0.0)) if eta is not None else None
        stage = render_stage(percent)

        push_progress(percent, stage)

        if done == 1:
            add_log(t("ui.log_connecting_pvgis", lang))
            add_log(t("ui.log_using_jrc_engine", lang))

        if month_name == "Jan":
            add_log(t("ui.log_starting_annual_assessment", lang, device_name=device_name))
        if month_name == "Jun":
            add_log(t("ui.log_reviewing_midyear", lang, device_name=device_name))
        if month_name == "Dec":
            add_log(t("ui.log_checking_winter", lang, device_name=device_name))

    results, overall, worst_name, worst_gap, slope = simulate_for_devices(
        loc=loc,
        required_hrs=st.session_state.required_hours,
        selected_ids=st.session_state.get("selected_simulation_keys") or st.session_state.selected_ids,
        per_device_config=st.session_state.per_device_config,
        az_override=None,
        progress_callback=simulation_progress,
    )

    elapsed = time.time() - started

    push_progress(92, t("ui.stage_calculating_feasibility", lang))
    add_log(t("ui.log_pvgis_responses_received", lang))
    add_log(t("ui.log_preparing_conclusion", lang))

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    pdf_name = make_pdf(
        results=results,
        overall=overall,
        language=st.session_state.get("language", "en"),
        airport_label=st.session_state.airport_label,
        airport_icao=st.session_state.get("airport_icao", ""),
        created_at=now_local(),
        author_name=st.session_state.get("auth_full_name") or st.session_state.get("auth_email", ""),
        required_hours=st.session_state.required_hours,
        operating_profile_mode=st.session_state.get("operating_profile_mode", t("ui.mode_custom", lang)),
        output_path=tmp_path,
        lat=st.session_state.lat,
        lon=st.session_state.lon,
        selected_ids=st.session_state.get("selected_simulation_keys") or st.session_state.selected_ids,
    )

    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    push_progress(100, t("ui.stage_generating_results", lang))
    add_log(t("ui.log_simulation_complete", lang))
    add_log(t("ui.log_total_elapsed", lang, elapsed=format_seconds(elapsed)))

    st.session_state.results = results
    st.session_state.overall = overall
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_name = pdf_name or "SALA_report.pdf"
    st.session_state.elapsed = elapsed
    st.session_state.running = False
    st.session_state.trigger_run = False
    st.session_state.run_stage = t("ui.completed", lang)
    st.session_state.run_progress = 100
    st.session_state.run_elapsed_seconds = elapsed
    st.session_state.run_eta_seconds = 0.0
    st.rerun()
