import json
import streamlit as st

from core.db import get_user_studies
from core.devices import DEVICES


def _row_value(row, key, default=None):
    try:
        if row is None:
            return default

        if isinstance(row, dict):
            return row.get(key, default)

        try:
            return row[key]
        except Exception:
            pass

        return default
    except Exception:
        return default


def _safe_json_list(value):
    if value is None or value == "":
        return []

    if isinstance(value, list):
        return value

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception:
        return []


def _safe_json_dict(value):
    if value is None or value == "":
        return {}

    if isinstance(value, dict):
        return value

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except Exception:
        return {}


def _device_labels(row):
    ids = _safe_json_list(_row_value(row, "selected_devices_json"))
    if not ids:
        return []

    labels = []
    for device_id in ids:
        try:
            did = int(device_id)
            spec = DEVICES.get(did)
            if spec:
                labels.append(spec.get("code") or spec.get("name") or str(did))
            else:
                labels.append(str(did))
        except Exception:
            labels.append(str(device_id))

    return labels


def _format_devices(labels):
    if not labels:
        return "—"
    return ", ".join(labels)


def _format_blackout_days(row):
    value = _row_value(row, "worst_blackout_days")
    if value is None or value == "":
        return "—"
    try:
        return f"{int(value)}"
    except Exception:
        return str(value)


def _format_required_hours(row):
    value = _row_value(row, "required_hours")
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.1f}"
    except Exception:
        return str(value)


def _result_badge(result):
    result = (result or "").upper()

    if result == "PASS":
        color = "#16a34a"
        bg = "#ecfdf3"
        border = "#bbf7d0"
    elif result in ["NEAR", "NEAR THRESHOLD", "MIXED"]:
        color = "#d97706"
        bg = "#fff7ed"
        border = "#fed7aa"
    elif result == "FAIL":
        color = "#dc2626"
        bg = "#fef2f2"
        border = "#fecaca"
    else:
        color = "#475467"
        bg = "#f8fafc"
        border = "#e4e7ec"

    return f"""
    <span style="
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        font-size:0.82rem;
        font-weight:700;
        color:{color};
        background:{bg};
        border:1px solid {border};
    ">
        {result or "UNKNOWN"}
    </span>
    """


def render_my_studies(user_id):
    st.markdown("## My studies")

    if not user_id:
        st.info("User is not logged in.")
        return

    rows = get_user_studies(user_id)

    if not rows:
        st.info("No saved studies yet.")
        return

    for idx, row in enumerate(rows):
        airport_label = _row_value(row, "airport_label", "Study point")
        overall_result = _row_value(row, "overall_result", "UNKNOWN")
        required_hours = _format_required_hours(row)
        worst_blackout_days = _format_blackout_days(row)
        created_at = _row_value(row, "created_at", "—")
        pdf_name = _row_value(row, "pdf_name", "study_report.pdf")
        pdf_bytes = _row_value(row, "pdf_bytes")
        operating_profile_mode = _row_value(row, "operating_profile_mode", "—")
        lat = _row_value(row, "lat", "—")
        lon = _row_value(row, "lon", "—")

        device_labels = _device_labels(row)
        result_summary = _safe_json_dict(_row_value(row, "result_summary_json"))

        with st.container():
            st.markdown(
                f"""
                <div style="
                    border:1px solid #e4e7ec;
                    border-radius:16px;
                    background:#ffffff;
                    padding:16px 18px;
                    margin-bottom:14px;
                    box-shadow:0 2px 8px rgba(16,24,40,0.04);
                ">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;">
                        <div>
                            <div style="font-size:1.05rem;font-weight:800;color:#1f2937;">
                                {airport_label}
                            </div>
                            <div style="margin-top:4px;color:#667085;font-size:0.92rem;">
                                Created: {created_at}
                            </div>
                        </div>
                        <div>
                            {_result_badge(overall_result)}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns([1.4, 1.2, 1.2], gap="large")

            with c1:
                st.markdown("**Devices**")
                st.write(_format_devices(device_labels))

                st.markdown("**Operating profile**")
                st.write(operating_profile_mode)

            with c2:
                st.markdown("**Required hours/day**")
                st.write(required_hours)

                st.markdown("**Worst blackout days**")
                st.write(worst_blackout_days)

            with c3:
                st.markdown("**Study point**")
                st.write(f"{lat}, {lon}")

                pass_state = result_summary.get("overall_state") or "—"
                st.markdown("**Overall state**")
                st.write(pass_state)

            if pdf_bytes:
                st.download_button(
                    "📄 Download PDF",
                    data=pdf_bytes,
                    file_name=pdf_name,
                    mime="application/pdf",
                    key=f"download_pdf_{idx}",
                    use_container_width=False,
                )

            st.markdown("<hr style='margin:18px 0 8px 0;'>", unsafe_allow_html=True)
