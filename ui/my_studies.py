# ui/my_studies.py

import json
import streamlit as st
from core.db import list_user_studies
from core.devices import DEVICES


def _safe_json_list(raw_value):
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
        if isinstance(value, list):
            return value
        return []
    except Exception:
        return []


def _device_label_from_id(device_id):
    try:
        d = DEVICES[int(device_id)]
        return d.get("code") or d.get("name") or str(device_id)
    except Exception:
        return str(device_id)


def _safe_json_dict(raw_value):
    if not raw_value:
        return {}
    try:
        value = json.loads(raw_value)
        if isinstance(value, dict):
            return value
        return {}
    except Exception:
        return {}


def _device_labels(row):
    ids = _safe_json_list(row.get("selected_devices_json"))
    cfg = _safe_json_dict(row.get("per_device_config_json"))
    labels = []
    for x in ids:
        key = str(x)
        item_cfg = cfg.get(key) or cfg.get(x) or {}
        display = item_cfg.get("display_label")
        if display:
            labels.append(display)
            continue
        if isinstance(x, str) and "||" in x:
            try:
                did, lamp_variant = x.split("||", 1)
                labels.append(f"{_device_label_from_id(did)} / {lamp_variant}")
                continue
            except Exception:
                pass
        labels.append(_device_label_from_id(x))
    return labels


def render_my_studies(user_id):
    st.markdown("## My studies")

    rows = list_user_studies(user_id)

    if not rows:
        st.info("No studies recorded yet.")
        return

    for row in rows:
        labels = _device_labels(row)
        devices_text = ", ".join(labels) if labels else "-"

        with st.container():
            st.markdown("---")

            c1, c2, c3 = st.columns([2.1, 1.1, 1.2])

            with c1:
                st.markdown(f"**{row['airport_label'] or 'Unnamed study'}**")
                st.caption(row["created_at"])
                st.write(f"Mode: {row['operating_profile_mode'] or '-'}")
                st.write(f"Devices: {devices_text}")

            with c2:
                st.write(f"**Result:** {row['overall_result'] or '-'}")
                st.write(f"**Hours/day:** {row['required_hours']}")
                st.write(f"**Worst blackout days:** {row['worst_blackout_days'] if row['worst_blackout_days'] is not None else '-'}")

            with c3:
                pct = row["worst_blackout_pct"]
                pct_text = f"{pct:.2f}%" if pct is not None else "-"
                st.write(f"**Worst blackout %:** {pct_text}")

                if row["pdf_bytes"]:
                    st.download_button(
                        "Download PDF",
                        data=row["pdf_bytes"],
                        file_name=row["pdf_name"] or "study_report.pdf",
                        mime="application/pdf",
                        key=f"user_pdf_{row['id']}",
                        use_container_width=True,
                    )
