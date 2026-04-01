# ui/my_studies.py

import json
import streamlit as st

from core.db import list_user_studies
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


def _safe_json_list(raw_value):
    if raw_value is None or raw_value == "":
        return []

    if isinstance(raw_value, list):
        return raw_value

    try:
        value = json.loads(raw_value)
        if isinstance(value, list):
            return value
        return []
    except Exception:
        return []


def _device_label_from_id(device_id):
    try:
        did = int(device_id)
        d = DEVICES.get(did)
        if d:
            return d.get("code") or d.get("name") or str(did)
        return str(did)
    except Exception:
        return str(device_id)


def _device_labels_from_json(raw_value):
    ids = _safe_json_list(raw_value)
    return [_device_label_from_id(x) for x in ids]


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

    rows = list_user_studies(user_id)

    if not rows:
        st.info("No studies recorded yet.")
        return

    for idx, row in enumerate(rows):
        airport_label = _row_value(row, "airport_label", "Unnamed study")
        created_at = _row_value(row, "created_at", "—")
        operating_profile_mode = _row_value(row, "operating_profile_mode", "—")
        overall_result = _row_value(row, "overall_result", "UNKNOWN")
        required_hours = _row_value(row, "required_hours", "—")
        worst_blackout_days = _row_value(row, "worst_blackout_days", None)
        worst_blackout_pct = _row_value(row, "worst_blackout_pct", None)
        pdf_bytes = _row_value(row, "pdf_bytes", None)
        pdf_name = _row_value(row, "pdf_name", "study_report.pdf")
        row_id = _row_value(row, "id", idx)

        device_labels = _device_labels_from_json(_row_value(row, "selected_devices_json"))
        devices_text = ", ".join(device_labels) if device_labels else "—"

        if worst_blackout_days is None:
            blackout_days_text = "—"
        else:
            try:
                blackout_days_text = str(int(worst_blackout_days))
            except Exception:
                blackout_days_text = str(worst_blackout_days)

        if worst_blackout_pct is None:
            blackout_pct_text = "—"
        else:
            try:
                blackout_pct_text = f"{float(worst_blackout_pct):.2f}%"
            except Exception:
                blackout_pct_text = str(worst_blackout_pct)

        try:
            required_hours_text = f"{float(required_hours):.1f}"
        except Exception:
            required_hours_text = str(required_hours)

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

            c1, c2, c3 = st.columns([2.1, 1.1, 1.2])

            with c1:
                st.markdown("**Mode**")
                st.write(operating_profile_mode)

                st.markdown("**Devices**")
                st.write(devices_text)

            with c2:
                st.markdown("**Hours/day**")
                st.write(required_hours_text)

                st.markdown("**Worst blackout days**")
                st.write(blackout_days_text)

            with c3:
                st.markdown("**Worst blackout %**")
                st.write(blackout_pct_text)

                if pdf_bytes:
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name=pdf_name or "study_report.pdf",
                        mime="application/pdf",
                        key=f"user_pdf_{row_id}",
                        use_container_width=True,
                    )

            st.markdown("---")
