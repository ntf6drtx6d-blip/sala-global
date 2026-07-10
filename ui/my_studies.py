# ui/my_studies.py

import json
import html
from urllib.parse import urlencode
from collections import OrderedDict

import streamlit as st

from core.db import list_user_studies
from core.catalog import runtime_device_label, runtime_device_variant_label
from core.i18n import AVAILABLE_LANGUAGES, t
from core.time_utils import format_timestamp


def _row_value(row, key, default=None):
    try:
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            return default
    except Exception:
        return default


def _safe_json_list(raw_value):
    if raw_value is None or raw_value == "":
        return []
    if isinstance(raw_value, list):
        return raw_value
    try:
        value = json.loads(raw_value)
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _safe_json_dict(raw_value):
    if raw_value is None or raw_value == "":
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    try:
        value = json.loads(raw_value)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _format_seconds(seconds):
    try:
        seconds = max(0, int(round(float(seconds or 0))))
    except Exception:
        seconds = 0
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs:
        return f"{hrs}h {mins}m {secs}s"
    if mins:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _timing_value(totals, key):
    try:
        return float((totals or {}).get(key, 0.0) or 0.0)
    except Exception:
        return 0.0


def _normalize_result(result):
    value = (result or "").strip().upper()
    if value in {"ALL_PASS", "PASS"}:
        return "PASS"
    if value in {"NONE_PASS", "FAIL"}:
        return "FAIL"
    if value in {"MIXED", "PARTIAL", "PARTIAL / MIXED", "NEAR", "NEAR THRESHOLD"}:
        return "MIXED"
    return value or "UNKNOWN"


def _result_badge_config(result):
    normalized = _normalize_result(result)
    lang = st.session_state.get("language", "en")
    if normalized == "PASS":
        return t("ui.pass", lang), "#16a34a", "#ecfdf3", "#bbf7d0"
    if normalized == "FAIL":
        return t("ui.fail", lang), "#dc2626", "#fef2f2", "#fecaca"
    if normalized == "MIXED":
        return t("ui.partial_mixed", lang), "#d97706", "#fff7ed", "#fed7aa"
    return normalized, "#475467", "#f8fafc", "#e4e7ec"


def _device_variant_label(device_id, variant):
    return runtime_device_variant_label(device_id, variant)


def _format_operating_mode(raw_mode, lang):
    value = str(raw_mode or "").strip()
    if not value:
        return "—"
    if value in {"Custom hours per day", t("ui.mode_custom", lang)}:
        return t("ui.mode_custom", lang)
    if value in {"Dusk to dawn", t("ui.mode_dusk", lang)}:
        return t("ui.mode_dusk", lang)
    if value in {"24/7", t("ui.mode_247", lang)}:
        return t("ui.mode_247", lang)
    return value


def _device_labels_from_json(raw_value):
    ids = _safe_json_list(raw_value)
    grouped = OrderedDict()
    for item in ids:
        raw = str(item)
        if "||" in raw:
            device_id, variant = raw.split("||", 1)
            label = _device_variant_label(device_id, variant)
        else:
            label = runtime_device_label(raw)
        grouped[label] = grouped.get(label, 0) + 1
    return [f"{count} × {label}" for label, count in grouped.items()]


def _format_created_at(value):
    return format_timestamp(value, include_seconds=True)


def _format_language(value):
    code = str(value or "en").strip().lower()
    return AVAILABLE_LANGUAGES.get(code, code.upper() if code else "—")


def _study_open_url(row_id):
    params = {"study": str(row_id)}
    auth_token = st.query_params.get("auth")
    if isinstance(auth_token, list):
        auth_token = auth_token[0] if auth_token else None
    if auth_token:
        params["auth"] = str(auth_token)
    return f"?{urlencode(params)}"


def render_my_studies(user_id):
    lang = st.session_state.get("language", "en")
    st.markdown(f"## {t('ui.my_studies_heading', lang)}")

    if not user_id:
        st.info(t("ui.user_not_logged_in", lang))
        return

    rows = list_user_studies(user_id)
    if not rows:
        st.info(t("ui.no_studies_recorded", lang))
        return

    for idx, row in enumerate(rows):
        study_name = _row_value(row, "study_name", None) or _row_value(row, "airport_label", t("ui.unnamed_study", lang))
        airport_name = _row_value(row, "airport_label", None) or "—"
        study_language = _format_language(_row_value(row, "language", "en"))
        created_at = _format_created_at(_row_value(row, "created_at", "—"))
        operating_profile_mode = _format_operating_mode(_row_value(row, "operating_profile_mode", "—"), lang)
        overall_result = _row_value(row, "overall_result", "UNKNOWN")
        required_hours = _row_value(row, "required_hours", "—")
        worst_blackout_days = _row_value(row, "worst_blackout_days", None)
        worst_blackout_pct = _row_value(row, "worst_blackout_pct", None)
        pdf_bytes = _row_value(row, "pdf_bytes", None)
        pdf_name = _row_value(row, "pdf_name", "SALA_report.pdf")
        row_id = _row_value(row, "id", idx)

        device_labels = _device_labels_from_json(_row_value(row, "selected_devices_json"))
        devices_text = ", ".join(device_labels) if device_labels else "—"

        try:
            required_hours_text = f"{float(required_hours):.1f}"
        except Exception:
            required_hours_text = str(required_hours)

        try:
            blackout_days_text = str(int(worst_blackout_days)) if worst_blackout_days is not None else "—"
        except Exception:
            blackout_days_text = str(worst_blackout_days)

        try:
            blackout_pct_text = f"{float(worst_blackout_pct):.2f}%" if worst_blackout_pct is not None else "—"
        except Exception:
            blackout_pct_text = str(worst_blackout_pct)

        simulation_timing = _safe_json_dict(_row_value(row, "simulation_timing_json"))
        timing_totals = simulation_timing.get("totals") or {}
        timing_chunks = list(simulation_timing.get("chunks") or [])

        badge_text, badge_fg, badge_bg, badge_border = _result_badge_config(overall_result)

        with st.container(border=True):
            top_left, top_right = st.columns([4, 1.2], vertical_alignment="top")
            with top_left:
                st.markdown(f"### {study_name}")
                st.caption(f"{t('ui.created', lang)}: {created_at}")
            with top_right:
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:flex-end;">
                        <span style="
                            display:inline-block;
                            padding:4px 10px;
                            border-radius:999px;
                            font-size:0.82rem;
                            font-weight:700;
                            color:{badge_fg};
                            background:{badge_bg};
                            border:1px solid {badge_border};
                            white-space:nowrap;
                        ">
                            {badge_text}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            left, right = st.columns(2)
            with left:
                st.markdown(f"**{t('ui.airport_name', lang)}**")
                st.write(airport_name)
                st.markdown(f"**{t('ui.language', lang)}**")
                st.write(study_language)
                st.markdown(f"**{t('ui.mode', lang)}**")
                st.write(operating_profile_mode or "—")
                st.markdown(f"**{t('ui.devices', lang)}**")
                st.write(devices_text)
            with right:
                st.markdown(f"**{t('ui.hours_per_day_unit', lang)}**")
                st.write(required_hours_text)
                st.markdown(f"**{t('ui.worst_blackout_days', lang)}**")
                st.write(blackout_days_text)
                st.markdown(f"**{t('ui.worst_blackout_pct', lang)}**")
                st.write(blackout_pct_text)

            if timing_totals or timing_chunks:
                with st.expander("Simulation timing log", expanded=False):
                    total_seconds = _timing_value(timing_totals, "total_elapsed_seconds") or _timing_value(timing_totals, "elapsed_seconds")
                    st.markdown(f"**Total elapsed:** {_format_seconds(total_seconds)}")
                    timing_cols = st.columns(5)
                    timing_metrics = [
                        ("Monthly PVGIS search", "monthly_search_seconds"),
                        ("Blackout stats", "blackout_stats_seconds"),
                        ("PVGIS/report metadata", "pvgis_meta_seconds"),
                        ("Battery behavior/UI", "battery_behavior_seconds"),
                        ("PDF generation", "pdf_generation_seconds"),
                    ]
                    for col, (label, key) in zip(timing_cols, timing_metrics):
                        col.metric(label, _format_seconds(_timing_value(timing_totals, key)))

                    if timing_chunks:
                        rows = []
                        for idx_chunk, chunk in enumerate(timing_chunks, start=1):
                            rows.append(
                                {
                                    "Device": chunk.get("device_name") or chunk.get("device_key") or f"Device {idx_chunk}",
                                    "Elapsed": _format_seconds(chunk.get("elapsed_seconds")),
                                    "Monthly search": _format_seconds(chunk.get("monthly_search_seconds")),
                                    "Blackout stats": _format_seconds(chunk.get("blackout_stats_seconds")),
                                    "Metadata": _format_seconds(chunk.get("pvgis_meta_seconds")),
                                    "Battery/UI": _format_seconds(chunk.get("battery_behavior_seconds")),
                                }
                            )
                        st.dataframe(rows, hide_index=True, use_container_width=True)

            action_cols = st.columns(2)
            with action_cols[0]:
                open_url = _study_open_url(row_id)
                open_label = html.escape(t("ui.open_study", lang))
                st.markdown(
                    f"""
                    <a href="{html.escape(open_url)}" target="_blank" rel="noopener noreferrer"
                       style="
                         display:block;
                         width:100%;
                         box-sizing:border-box;
                         text-align:center;
                         text-decoration:none;
                         border:1px solid #f5c451;
                         border-radius:14px;
                         padding:0.72rem 1rem;
                         font-weight:700;
                         color:#7a5a00;
                         background:#fff7dc;
                       ">
                        {open_label}
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
            with action_cols[1]:
                if pdf_bytes:
                    st.download_button(
                        t("ui.download_pdf", lang),
                        data=pdf_bytes,
                        file_name=pdf_name or "SALA_report.pdf",
                        mime="application/pdf",
                        key=f"user_pdf_{row_id}",
                        use_container_width=True,
                    )
