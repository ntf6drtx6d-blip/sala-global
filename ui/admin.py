# ui/admin.py

import json
import secrets
import string
import streamlit as st

from core.db import (
    list_access_requests,
    list_all_users,
    list_all_studies,
    create_user,
    update_access_request_status,
    user_exists,
    update_user_active,
    update_user_password,
)
from core.auth import hash_password
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
        d = DEVICES[device_id]
        return d.get("code") or d.get("name") or str(device_id)
    except Exception:
        return str(device_id)


def _device_labels_from_json(raw_value):
    ids = _safe_json_list(raw_value)
    labels = [_device_label_from_id(x) for x in ids]
    return labels


def _generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
                st.caption("Created")
                st.write(row["created_at"])

            if row["message"]:
                st.write("Message:")
                st.info(row["message"])

            btn1, btn2 = st.columns(2)

            with btn1:
                if st.button(
                    f"Approve & create user #{row['id']}",
                    key=f"approve_request_{row['id']}",
                    use_container_width=True,
                    disabled=(row["status"] != "new"),
                ):
                    email = row["email"].strip().lower()

                    if user_exists(email):
                        st.warning("User with this email already exists.")
                    else:
                        temp_password = _generate_temp_password()
                        create_user(
                            email=email,
                            password_hash=hash_password(temp_password),
                            role="user",
                            full_name=row["full_name"],
                            organization=row["organization"],
                        )
                        update_access_request_status(row["id"], "approved")
                        st.success(
                            f"User created. Temporary password for {email}: {temp_password}"
                        )
                        st.rerun()

            with btn2:
                if st.button(
                    f"Mark rejected #{row['id']}",
                    key=f"reject_request_{row['id']}",
                    use_container_width=True,
                    disabled=(row["status"] != "new"),
                ):
                    update_access_request_status(row["id"], "rejected")
                    st.info("Request marked as rejected.")
                    st.rerun()


def _render_users_tab():
    st.markdown("### Users")

    with st.expander("Create user manually", expanded=False):
        new_email = st.text_input("Email", key="admin_create_email")
        new_full_name = st.text_input("Full name", key="admin_create_full_name")
        new_org = st.text_input("Organization", key="admin_create_org")
        new_role = st.selectbox("Role", ["user", "admin"], key="admin_create_role")
        new_password = st.text_input(
            "Temporary password",
            value=_generate_temp_password(),
            key="admin_create_password",
        )

        if st.button("Create user", key="admin_create_user_btn", use_container_width=True):
            email = new_email.strip().lower()

            if not email:
                st.error("Email is required.")
            elif user_exists(email):
                st.error("User with this email already exists.")
            elif not new_password.strip():
                st.error("Password is required.")
            else:
                create_user(
                    email=email,
                    password_hash=hash_password(new_password.strip()),
                    role=new_role,
                    full_name=new_full_name.strip() or None,
                    organization=new_org.strip() or None,
                )
                st.success(f"User created for {email}")
                st.rerun()

    rows = list_all_users()

    if not rows:
        st.info("No users found.")
        return

    current_user_id = st.session_state.get("auth_user_id")

    for row in rows:
        with st.container():
            st.markdown("---")

            c1, c2, c3 = st.columns([2.4, 1.1, 1.7])

            with c1:
                st.markdown(f"**{row['email']}**")
                st.write(f"Name: {row['full_name'] or '-'}")
                st.write(f"Organization: {row['organization'] or '-'}")

            with c2:
                st.write(f"Role: {row['role']}")
                st.write(f"Active: {'Yes' if row['is_active'] else 'No'}")
                st.write(f"Created: {row['created_at']}")

            with c3:
                can_manage = row["id"] != current_user_id

                if row["is_active"]:
                    if st.button(
                        "Deactivate",
                        key=f"deactivate_user_{row['id']}",
                        use_container_width=True,
                        disabled=not can_manage,
                    ):
                        update_user_active(row["id"], False)
                        st.warning(f"User {row['email']} deactivated.")
                        st.rerun()
                else:
                    if st.button(
                        "Reactivate",
                        key=f"reactivate_user_{row['id']}",
                        use_container_width=True,
                        disabled=not can_manage,
                    ):
                        update_user_active(row["id"], True)
                        st.success(f"User {row['email']} reactivated.")
                        st.rerun()

                if st.button(
                    "Reset password",
                    key=f"reset_password_{row['id']}",
                    use_container_width=True,
                    disabled=not can_manage,
                ):
                    temp_password = _generate_temp_password()
                    update_user_password(row["id"], hash_password(temp_password))
                    st.success(
                        f"Password reset for {row['email']}. New temporary password: {temp_password}"
                    )


def _render_studies_tab():
    st.markdown("### Studies")

    rows = list_all_studies()

    if not rows:
        st.info("No studies recorded yet.")
        return

    # collect filter options
    user_options = sorted({row["email"] for row in rows if row["email"]})
    result_options = sorted({row["overall_result"] for row in rows if row["overall_result"]})

    f1, f2 = st.columns(2)

    with f1:
        selected_user = st.selectbox(
            "Filter by user",
            options=["All users"] + user_options,
            key="admin_studies_user_filter",
        )

    with f2:
        selected_result = st.selectbox(
            "Filter by result",
            options=["All results"] + result_options,
            key="admin_studies_result_filter",
        )

    filtered_rows = rows

    if selected_user != "All users":
        filtered_rows = [row for row in filtered_rows if row["email"] == selected_user]

    if selected_result != "All results":
        filtered_rows = [row for row in filtered_rows if row["overall_result"] == selected_result]

    if not filtered_rows:
        st.info("No studies match the selected filters.")
        return

    for row in filtered_rows:
        labels = _device_labels_from_json(row["selected_devices_json"])
        devices_text = ", ".join(labels) if labels else "-"

        with st.container():
            st.markdown("---")

            c1, c2, c3 = st.columns([2.2, 1.1, 1.2])

            with c1:
                st.markdown(f"**{row['airport_label'] or 'Unnamed study'}**")
                st.caption(f"{row['created_at']} · {row['email']}")
                st.write(f"Mode: {row['operating_profile_mode'] or '-'}")
                st.write(f"Devices: {devices_text}")

            with c2:
                st.write(f"**Result:** {row['overall_result'] or '-'}")
                st.write(f"**Hours/day:** {row['required_hours']}")
                st.write(
                    f"**Worst blackout days:** {row['worst_blackout_days'] if row['worst_blackout_days'] is not None else '-'}"
                )

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
                        key=f"admin_pdf_{row['id']}",
                        use_container_width=True,
                    )


def render_admin_panel():
    st.markdown("## Admin panel")

    tab1, tab2, tab3 = st.tabs(["Access requests", "Users", "Studies"])

    with tab1:
        _render_access_requests_tab()

    with tab2:
        _render_users_tab()

    with tab3:
        _render_studies_tab()
