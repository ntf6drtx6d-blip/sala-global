# ui/admin.py

import json
import streamlit as st

from core.db import list_access_requests, list_all_users, list_all_studies


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


def _render_access_requests_tab():
    st.markdown("### Access requests")

    rows = list_access_requests()

    if not rows:
        st.info("No access requests yet.")
        return

    for row in rows:
        with st.container():
            st.markdown("---")
            c1, c2 = st.columns([3, 1])

            with c1:
                st.markdown(f"**{row['full_name']}**")
                st.write(f"Email: {row['email']}")
                st.write(f"Organization: {row['organization'] or '-'}")
                st.write(f"Status: {row['status']}")

            with c2:
                st.caption(f"Created")
                st.write(row["created_at"])

            if row["message"]:
                st.write("Message:")
                st.info(row["message"])


def _render_users_tab():
    st.markdown("### Users")

    rows = list_all_users()

    if not rows:
        st.info("No users found.")
        return

    data = []
    for row in rows:
        data.append(
            {
                "Email": row["email"],
                "Full name": row["full_name"] or "",
                "Organization": row["organization"] or "",
                "Role": row["role"],
                "Active": "Yes" if row["is_active"] else "No",
                "Created": row["created_at"],
                "Last login": row["last_login_at"] or "",
            }
        )

    st.dataframe(data, use_container_width=True, hide_index=True)


def _render_studies_tab():
    st.markdown("### Studies")

    rows = list_all_studies()

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
                "User": row["email"],
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


def render_admin_panel():
    st.markdown("## Admin panel")

    tab1, tab2, tab3 = st.tabs(["Access requests", "Users", "Studies"])

    with tab1:
        _render_access_requests_tab()

    with tab2:
        _render_users_tab()

    with tab3:
        _render_studies_tab()
