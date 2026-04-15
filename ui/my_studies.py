# ui/my_studies.py

import json
from collections import OrderedDict

import streamlit as st

from core.db import list_user_studies
from core.devices import DEVICES
from core.i18n import t


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
    try:
        did = int(device_id)
        device = DEVICES.get(did)
        base = device.get("name") or device.get("code") or str(did) if device else str(did)
    except Exception:
        base = str(device_id)
    if variant:
        return f"{base} / {variant}"
    return base


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
            try:
                did = int(raw)
                device = DEVICES.get(did)
                label = device.get("name") or device.get("code") or str(did) if device else str(did)
            except Exception:
                label = raw
        grouped[label] = grouped.get(label, 0) + 1
    return [f"{count} × {label}" for label, count in grouped.items()]


def _format_created_at(value):
    text = str(value or "—")
    return text.replace("T", " ")


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
        study_name = _row_value(row, "airport_label", t("ui.unnamed_study", lang))
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

            if pdf_bytes:
                st.download_button(
                    t("ui.download_pdf", lang),
                    data=pdf_bytes,
                    file_name=pdf_name or "SALA_report.pdf",
                    mime="application/pdf",
                    key=f"user_pdf_{row_id}",
                    use_container_width=True,
                )
