# ui/my_studies.py

import json
import streamlit as st
from core.db import list_user_studies


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


def render_my_studies(user_id):
    st.markdown("## My studies")

    rows = list_user_studies(user_id)

    if not rows:
        st.info("No studies recorded yet.")
        return

    data = []
    for row in rows:
        devices = _safe_json_list(row["selected_devices_json"])
        devices_text = ", ".join(str(x) for x in devices) if devices else ""

        data.append(
            {
                "Created": row["created_at"],
                "Airport": row["airport_label"] or "",
                "Hours/day": row["required_hours"],
                "Mode": row["operating_profile_mode"] or "",
                "Devices": devices_text,
                "Result": row["overall_result"] or "",
                "Worst blackout days": row["worst_blackout_days"],
                "Worst blackout %": row["worst_blackout_pct"],
            }
        )

    st.dataframe(data, use_container_width=True, hide_index=True)
