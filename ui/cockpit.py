
import os
import time
import tempfile
import json
import hashlib

import streamlit as st

from core.simulate import simulate_for_devices
from core.devices import DEVICES
from core.db import save_running_study_checkpoint
from core.i18n import t
from core.person import normalize_person_name
from core.time_utils import format_clock_timestamp, now_local
from report.report import make_pdf
EU_LOGO_PATH = "logo_en.gif"
DEFAULT_LAT = 40.416775
DEFAULT_LON = -3.703790
DEFAULT_MANUFACTURER = "S4GA"


def format_seconds(seconds):
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _profiling_summary(profile):
    if not profile:
        return []
    total = float(profile.get("total_seconds", 0.0) or 0.0)
    monthly = float(profile.get("monthly_search_total_seconds", 0.0) or 0.0)
    blackout = float(profile.get("blackout_stats_total_seconds", 0.0) or 0.0)
    meta = float(profile.get("meta_total_seconds", 0.0) or 0.0)
    behavior = float(profile.get("behavior_total_seconds", 0.0) or 0.0)
    lines = [
        f"Profiling: simulation core {format_seconds(total)}",
        f"Monthly search: {format_seconds(monthly)}",
        f"Blackout stats: {format_seconds(blackout)}",
        f"PVGIS/report metadata: {format_seconds(meta)}",
        f"Battery behavior/UI metrics: {format_seconds(behavior)}",
    ]
    for item in profile.get("device_breakdown", [])[:3]:
        lines.append(
            f"{item.get('device_name', 'Device')}: search {format_seconds(item.get('monthly_search_seconds', 0.0))}, "
            f"blackout {format_seconds(item.get('blackout_stats_seconds', 0.0))}, "
            f"meta {format_seconds(item.get('meta_seconds', 0.0))}"
        )
    return lines


def _timing_round(value):
    try:
        return round(float(value or 0.0), 3)
    except Exception:
        return 0.0


def _normalize_timing_profile(profile, elapsed_seconds, device_key):
    profile = dict(profile or {})
    device_items = list(profile.get("device_breakdown") or [])
    device_profile = dict(device_items[0]) if device_items else {}
    return {
        "device_key": str(device_key),
        "device_name": device_profile.get("device_name") or str(device_key),
        "source_type": device_profile.get("source_type"),
        "elapsed_seconds": _timing_round(elapsed_seconds),
        "simulation_core_seconds": _timing_round(profile.get("total_seconds", elapsed_seconds)),
        "monthly_search_seconds": _timing_round(profile.get("monthly_search_total_seconds")),
        "blackout_stats_seconds": _timing_round(profile.get("blackout_stats_total_seconds")),
        "pvgis_meta_seconds": _timing_round(profile.get("meta_total_seconds")),
        "battery_behavior_seconds": _timing_round(profile.get("behavior_total_seconds")),
        "device_breakdown": [
            {
                "device_name": item.get("device_name"),
                "source_type": item.get("source_type"),
                "monthly_search_seconds": _timing_round(item.get("monthly_search_seconds")),
                "blackout_stats_seconds": _timing_round(item.get("blackout_stats_seconds")),
                "pvgis_meta_seconds": _timing_round(item.get("meta_seconds")),
                "battery_behavior_seconds": _timing_round(item.get("behavior_seconds")),
            }
            for item in device_items
        ],
    }


def _append_timing_profile(profile, elapsed_seconds, device_key):
    timing = dict(st.session_state.get("simulation_timing") or {})
    chunks = list(timing.get("chunks") or [])
    chunk = _normalize_timing_profile(profile, elapsed_seconds, device_key)
    chunks.append(chunk)
    totals = {
        "elapsed_seconds": sum(_timing_round(item.get("elapsed_seconds")) for item in chunks),
        "simulation_core_seconds": sum(_timing_round(item.get("simulation_core_seconds")) for item in chunks),
        "monthly_search_seconds": sum(_timing_round(item.get("monthly_search_seconds")) for item in chunks),
        "blackout_stats_seconds": sum(_timing_round(item.get("blackout_stats_seconds")) for item in chunks),
        "pvgis_meta_seconds": sum(_timing_round(item.get("pvgis_meta_seconds")) for item in chunks),
        "battery_behavior_seconds": sum(_timing_round(item.get("battery_behavior_seconds")) for item in chunks),
    }
    timing.update(
        {
            "chunks": chunks,
            "totals": {k: _timing_round(v) for k, v in totals.items()},
            "completed_devices": len(chunks),
            "last_device_name": chunk.get("device_name"),
        }
    )
    st.session_state.simulation_timing = timing
    return timing


def now_ts():
    return format_clock_timestamp(with_timezone=True)


def _simulation_signature(lang):
    payload = {
        "airport_label": st.session_state.get("airport_label", ""),
        "airport_icao": st.session_state.get("airport_icao", ""),
        "lat": st.session_state.get("lat"),
        "lon": st.session_state.get("lon"),
        "required_hours": float(st.session_state.get("required_hours", 0) or 0),
        "operating_profile_mode": st.session_state.get("operating_profile_mode", t("ui.mode_custom", lang)),
        "selected_ids": st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []),
        "per_device_config": st.session_state.get("per_device_config", {}),
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_pdf(results, overall, lang):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    pdf_name = make_pdf(
        results=results,
        overall=overall,
        language=lang,
        airport_label=st.session_state.airport_label,
        airport_icao=st.session_state.get("airport_icao", ""),
        created_at=now_local(),
        author_name=normalize_person_name(
            st.session_state.get("auth_full_name") or st.session_state.get("auth_email", "")
        ),
        author_organization=st.session_state.get("auth_organization", ""),
        required_hours=st.session_state.required_hours,
        operating_profile_mode=st.session_state.get("operating_profile_mode", t("ui.mode_custom", lang)),
        output_path=tmp_path,
        lat=st.session_state.lat,
        lon=st.session_state.lon,
        selected_ids=st.session_state.get("selected_simulation_keys") or st.session_state.selected_ids,
        include_aging=True,
    )

    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    return pdf_name or "SALA_report.pdf", pdf_bytes


def regenerate_pdf_for_current_results():
    lang = st.session_state.get("language", "en")
    results = st.session_state.get("results")
    overall = st.session_state.get("overall")
    if results is None or overall is None:
        return False
    pdf_name, pdf_bytes = _build_pdf(results, overall, lang)
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_name = pdf_name or "SALA_report.pdf"
    st.session_state.pdf_error = None
    return True


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
        "auth_organization": st.session_state.get("auth_organization"),
    }

    keep = {
        "airport_label": "",
        "airport_query": "",
        "airport_icao": "",
        "airport_query_input": "",
        "airport_icao_input": "",
        "study_location": None,
        "language": st.session_state.get("language", "en"),
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
        "device_search_filter": "",
        "search_message": "",
        "map_click_info": "",
        "last_airport_query": "",
        "last_map_click": None,
        "map_click_pending_rerender": False,
        "show_map_picker": False,
        "study_point_confirmed": False,
        "study_ready": False,
        "results": None,
        "overall": None,
        "pdf_bytes": None,
        "pdf_name": "SALA_report.pdf",
        "pdf_error": None,
        "elapsed": None,
        "running": False,
        "run_progress": 0,
        "run_stage": t("ui.ready", lang),
        "run_log": [],
        "run_started_at": None,
        "run_elapsed_seconds": None,
        "run_eta_seconds": None,
        "run_last_update_at": None,
        "run_error": None,
        "trigger_run": False,
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
    active_job = dict(st.session_state.get("active_simulation_job") or {})
    if not active_job:
        raise RuntimeError("No active simulation job found.")

    selected_devices = list(active_job.get("selected_devices") or st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []))
    total_devices = len(selected_devices)
    current_index = int(active_job.get("current_device_index", 0) or 0)
    if total_devices <= 0:
        raise RuntimeError("No devices selected for simulation.")
    if current_index >= total_devices:
        current_index = total_devices - 1

    current_device_key = selected_devices[current_index]
    current_device_label = str(current_device_key)
    partial_results = dict(st.session_state.get("partial_results") or {})
    st.session_state.running = True
    st.session_state.run_stage = t("ui.preparing_simulation", lang)
    st.session_state.run_progress = max(0, int((current_index / max(total_devices, 1)) * 100))
    st.session_state.run_log = []
    st.session_state.run_started_at = time.time()
    st.session_state.run_elapsed_seconds = 0.0
    st.session_state.run_eta_seconds = None
    st.session_state.run_last_update_at = st.session_state.run_started_at
    st.session_state.run_error = None

    def add_log(message):
        logs = st.session_state.get("run_log", [])
        logs.append(f"**{now_ts()}** — {message}")
        st.session_state.run_log = logs[-6:]
        st.session_state.run_last_update_at = time.time()

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
    push_progress(max(1, int((current_index / total_devices) * 100)), t("ui.stage_validating_inputs", lang))

    add_log(t("ui.log_preparing_request_parameters", lang))
    push_progress(max(5, int((current_index / total_devices) * 100)), t("ui.stage_preparing_requests", lang))

    if partial_results:
        add_log(t("ui.simulation_resuming_from_checkpoint", lang, count=len(partial_results)))
    add_log(t("ui.processing_device_progress", lang, current=current_index + 1, total=total_devices))
    add_log(t("ui.current_device_name", lang, name=current_device_label))

    loc = {
        "lat": st.session_state.lat,
        "lon": st.session_state.lon,
        "label": st.session_state.airport_label or f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
        "country": st.session_state.get("airport_country", ""),
        "icao": st.session_state.get("airport_icao", ""),
    }

    started = time.time()

    def simulation_progress(done, total, pct, elapsed, eta, device_name, month_name):
        overall_done = (current_index * 12.0) + float(done or 0.0)
        overall_total = max(1.0, float(total_devices * 12))
        percent = int((overall_done / overall_total) * 100)
        st.session_state.run_elapsed_seconds = max(0.0, float(elapsed or 0.0))
        remaining_devices = max(total_devices - current_index - 1, 0)
        chunk_eta = max(0.0, float(eta or 0.0)) if eta is not None else None
        if chunk_eta is not None:
            st.session_state.run_eta_seconds = chunk_eta + (remaining_devices * max(st.session_state.run_elapsed_seconds, 1.0))
        else:
            st.session_state.run_eta_seconds = None

        month_parts = str(month_name or '').split('|')
        month_base = month_parts[0] if month_parts else ''
        month_phase = month_parts[1] if len(month_parts) > 1 else ''
        search_step = int(month_parts[2]) if len(month_parts) > 2 and str(month_parts[2]).isdigit() else None
        search_total = int(month_parts[3]) if len(month_parts) > 3 and str(month_parts[3]).isdigit() else None

        stage = render_stage(percent)
        if month_base:
            stage = f"{stage} — {device_name} / {month_base}"
            if month_phase == 'search' and search_step and search_total:
                stage = f"{stage} ({search_step}/{search_total})"

        push_progress(percent, stage)

        if float(done or 0) <= 1.0:
            add_log(t("ui.log_connecting_pvgis", lang))
            add_log(t("ui.log_using_jrc_engine", lang))

        if month_phase == 'start':
            add_log({
                'en': f'Evaluating {month_base} for {device_name}.',
                'es': f'Evaluando {month_base} para {device_name}.',
                'fr': f'Évaluation de {month_base} pour {device_name}.',
            }.get(lang, f'Evaluating {month_base} for {device_name}.'))

        if month_phase == 'search' and search_step in {4, 8, 12, 16} and search_total:
            add_log({
                'en': f'Running PVGIS monthly search {month_base} {search_step}/{search_total} for {device_name}.',
                'es': f'Ejecutando búsqueda mensual PVGIS {month_base} {search_step}/{search_total} para {device_name}.',
                'fr': f'Recherche mensuelle PVGIS {month_base} {search_step}/{search_total} pour {device_name}.',
            }.get(lang, f'Running PVGIS monthly search {month_base} {search_step}/{search_total} for {device_name}.'))

    simulation_profile = {}
    chunk_results, chunk_overall, worst_name, worst_gap, slope = simulate_for_devices(
        loc=loc,
        required_hrs=st.session_state.required_hours,
        selected_ids=[current_device_key],
        per_device_config=st.session_state.per_device_config,
        az_override=None,
        progress_callback=simulation_progress,
        profiling=simulation_profile,
    )
    elapsed = time.time() - started
    simulation_timing = _append_timing_profile(simulation_profile, elapsed, current_device_key)
    for line in _profiling_summary(simulation_profile):
        add_log(line)

    partial_results.update(chunk_results)
    completed_key = next(iter(chunk_results.keys())) if chunk_results else current_device_label
    completed_devices = list(active_job.get("completed_device_keys", []))
    if completed_key not in completed_devices:
        completed_devices.append(completed_key)

    next_index = current_index + 1
    st.session_state.partial_results = partial_results
    st.session_state.partial_overall = "RUNNING"

    if next_index < total_devices:
        active_job.update({
            "status": "RUNNING",
            "selected_devices": selected_devices,
            "current_device_index": next_index,
            "total_devices": total_devices,
            "completed_device_keys": completed_devices,
        })
        st.session_state.active_simulation_job = active_job
        save_running_study_checkpoint(
            study_id=st.session_state.get("active_study_id"),
            user_id=st.session_state.get("auth_user_id"),
            airport_label=st.session_state.get("airport_label", ""),
            lat=float(st.session_state.get("lat", 0)),
            lon=float(st.session_state.get("lon", 0)),
            required_hours=float(st.session_state.get("required_hours", 0)),
            operating_profile_mode=st.session_state.get("operating_profile_mode", ""),
            selected_devices=st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", []),
            per_device_config=st.session_state.get("per_device_config", {}),
            partial_results=partial_results,
            simulation_job=active_job,
            study_name=st.session_state.get("active_study_name"),
            study_version=st.session_state.get("active_study_version"),
            base_airport_label=st.session_state.get("active_study_base_label") or st.session_state.get("airport_label", ""),
            language=st.session_state.get("language", "en"),
            simulation_timing=simulation_timing,
        )
        push_progress(int((next_index / total_devices) * 100), t("ui.stage_calculating_feasibility", lang))
        add_log({
            "en": f"Checkpoint saved after {completed_key}.",
            "es": f"Punto de control guardado tras {completed_key}.",
            "fr": f"Point de reprise enregistre apres {completed_key}.",
        }.get(lang, f"Checkpoint saved after {completed_key}."))
        st.session_state.elapsed = elapsed
        st.session_state.running = True
        st.session_state.trigger_run = True
        st.session_state.run_last_update_at = time.time()
        st.session_state.simulation_auto_continue = True
        st.session_state.simulation_resume_required = False
        st.rerun()

    from core.simulate import summarize_simulation_results

    results = partial_results
    overall, worst_name, worst_gap = summarize_simulation_results(results)
    add_log(t("ui.log_pvgis_responses_received", lang))
    add_log(t("ui.log_preparing_conclusion", lang))
    pdf_name = "SALA_report.pdf"
    pdf_bytes = None
    pdf_error = None
    pdf_started = time.time()
    try:
        pdf_name, pdf_bytes = _build_pdf(results, overall, lang)
    except Exception as exc:
        pdf_error = str(exc)
        add_log(t("ui.pdf_generation_failed", lang, error=str(exc)))
    pdf_seconds = time.time() - pdf_started
    timing = dict(st.session_state.get("simulation_timing") or {})
    totals = dict(timing.get("totals") or {})
    totals["pdf_generation_seconds"] = _timing_round(pdf_seconds)
    totals["total_elapsed_seconds"] = _timing_round(sum(_timing_round(item.get("elapsed_seconds")) for item in timing.get("chunks", [])) + pdf_seconds)
    timing["totals"] = totals
    timing["pdf_generation_seconds"] = _timing_round(pdf_seconds)
    st.session_state.simulation_timing = timing

    push_progress(100, t("ui.stage_generating_results", lang))
    add_log(t("ui.log_simulation_complete", lang))
    add_log(f"PDF generation: {format_seconds(pdf_seconds)}")
    add_log(t("ui.log_total_elapsed", lang, elapsed=format_seconds(totals.get("total_elapsed_seconds", elapsed))))

    st.session_state.results = results
    st.session_state.overall = overall
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_name = pdf_name or "SALA_report.pdf"
    st.session_state.pdf_error = pdf_error
    st.session_state.partial_results = None
    st.session_state.partial_overall = None
    st.session_state.active_simulation_job = None
    st.session_state.simulation_auto_continue = False
    st.session_state.simulation_resume_required = False
    st.session_state.elapsed = elapsed
    st.session_state.running = False
    st.session_state.trigger_run = False
    st.session_state.run_stage = t("ui.completed", lang)
    st.session_state.run_progress = 100
    st.session_state.run_elapsed_seconds = elapsed
    st.session_state.run_eta_seconds = 0.0
    st.session_state.run_last_update_at = time.time()
    st.rerun()
