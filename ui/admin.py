# ui/admin.py

import json
import secrets
import string
import streamlit as st

from core.i18n import t
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
        return d.get("name") or d.get("code") or str(device_id)
    except Exception:
        return str(device_id)


def _device_labels_from_json(raw_value):
    ids = _safe_json_list(raw_value)
    labels = []
    for item in ids:
        raw = str(item)
        if "||" in raw:
            device_id, variant = raw.split("||", 1)
            try:
                device_id = int(device_id)
            except Exception:
                labels.append(raw)
                continue
            labels.append(f"{_device_label_from_id(device_id)} / {variant}")
        else:
            labels.append(_device_label_from_id(item))
    return labels


def _format_operating_mode(raw_mode, lang):
    value = str(raw_mode or "").strip()
    if not value:
        return "-"
    if value in {"Custom hours per day", t("ui.mode_custom", lang)}:
        return t("ui.mode_custom", lang)
    if value in {"Dusk to dawn", t("ui.mode_dusk", lang)}:
        return t("ui.mode_dusk", lang)
    if value in {"24/7", t("ui.mode_247", lang)}:
        return t("ui.mode_247", lang)
    return value


def _result_filter_options(rows, lang):
    mapping = {
        "ALL_PASS": t("ui.pass", lang),
        "PASS": t("ui.pass", lang),
        "NONE_PASS": t("ui.fail", lang),
        "FAIL": t("ui.fail", lang),
        "MIXED": t("ui.partial_mixed", lang),
        "PARTIAL": t("ui.partial_mixed", lang),
        "PARTIAL / MIXED": t("ui.partial_mixed", lang),
        "NEAR": t("ui.near_threshold", lang),
        "NEAR THRESHOLD": t("ui.near_threshold", lang),
    }
    options = []
    for raw in sorted({row["overall_result"] for row in rows if row["overall_result"]}):
        options.append((mapping.get(str(raw).upper(), str(raw)), raw))
    return options


def _generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _render_access_requests_tab():
    lang = st.session_state.get("language", "en")
    st.markdown(f"### {t('admin.access_requests', lang)}")

    rows = list_access_requests()

    if not rows:
        st.info(t("admin.no_access_requests", lang))
        return

    status_labels = {
        "new": t("admin.status_new", lang),
        "approved": t("admin.status_approved", lang),
        "rejected": t("admin.status_rejected", lang),
    }

    for row in rows:
        with st.container():
            st.markdown("---")

            c1, c2 = st.columns([3, 1])

            with c1:
                st.markdown(f"**{row['full_name']}**")
                st.write(f"{t('ui.email', lang)}: {row['email']}")
                st.write(f"{t('ui.organization', lang)}: {row['organization'] or '-'}")
                st.write(f"{t('ui.status', lang)}: {status_labels.get(row['status'], row['status'])}")

            with c2:
                st.caption(t("admin.created", lang))
                st.write(row["created_at"])

            if row["message"]:
                st.write(f"{t('admin.message', lang)}:")
                st.info(row["message"])

            btn1, btn2 = st.columns(2)

            with btn1:
                if st.button(
                    t("admin.approve_create_user", lang, id=row["id"]),
                    key=f"approve_request_{row['id']}",
                    use_container_width=True,
                    disabled=(row["status"] != "new"),
                ):
                    email = row["email"].strip().lower()

                    if user_exists(email):
                        st.warning(t("admin.user_exists", lang))
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
                            t("admin.user_created_temp_password", lang, email=email, password=temp_password)
                        )
                        st.rerun()

            with btn2:
                if st.button(
                    t("admin.reject_request", lang, id=row["id"]),
                    key=f"reject_request_{row['id']}",
                    use_container_width=True,
                    disabled=(row["status"] != "new"),
                ):
                    update_access_request_status(row["id"], "rejected")
                    st.info(t("admin.request_rejected", lang))
                    st.rerun()


def _render_users_tab():
    lang = st.session_state.get("language", "en")
    st.markdown(f"### {t('admin.users', lang)}")

    with st.expander(t("admin.create_user_manually", lang), expanded=False):
        new_email = st.text_input(t("ui.email", lang), key="admin_create_email")
        new_full_name = st.text_input(t("ui.full_name", lang), key="admin_create_full_name")
        new_org = st.text_input(t("ui.organization", lang), key="admin_create_org")
        new_role = st.selectbox(t("ui.role", lang), ["user", "admin"], key="admin_create_role")
        new_password = st.text_input(
            t("admin.temporary_password", lang),
            value=_generate_temp_password(),
            key="admin_create_password",
        )

        if st.button(t("admin.create_user", lang), key="admin_create_user_btn", use_container_width=True):
            email = new_email.strip().lower()

            if not email:
                st.error(t("admin.email_required", lang))
            elif user_exists(email):
                st.error(t("admin.user_exists", lang))
            elif not new_password.strip():
                st.error(t("admin.password_required", lang))
            else:
                create_user(
                    email=email,
                    password_hash=hash_password(new_password.strip()),
                    role=new_role,
                    full_name=new_full_name.strip() or None,
                    organization=new_org.strip() or None,
                )
                st.success(t("admin.user_created_for", lang, email=email))
                st.rerun()

    rows = list_all_users()

    if not rows:
        st.info(t("admin.no_users_found", lang))
        return

    current_user_id = st.session_state.get("auth_user_id")

    for row in rows:
        with st.container():
            st.markdown("---")

            c1, c2, c3 = st.columns([2.4, 1.1, 1.7])

            with c1:
                st.markdown(f"**{row['email']}**")
                st.write(f"{t('admin.name', lang)}: {row['full_name'] or '-'}")
                st.write(f"{t('ui.organization', lang)}: {row['organization'] or '-'}")

            with c2:
                st.write(f"{t('ui.role', lang)}: {row['role']}")
                st.write(f"{t('admin.active', lang)}: {t('admin.yes', lang) if row['is_active'] else t('admin.no', lang)}")
                st.write(f"{t('admin.created', lang)}: {row['created_at']}")

            with c3:
                can_manage = row["id"] != current_user_id

                if row["is_active"]:
                    if st.button(
                        t("admin.deactivate", lang),
                        key=f"deactivate_user_{row['id']}",
                        use_container_width=True,
                        disabled=not can_manage,
                    ):
                        update_user_active(row["id"], False)
                        st.warning(t("admin.user_deactivated", lang, email=row["email"]))
                        st.rerun()
                else:
                    if st.button(
                        t("admin.reactivate", lang),
                        key=f"reactivate_user_{row['id']}",
                        use_container_width=True,
                        disabled=not can_manage,
                    ):
                        update_user_active(row["id"], True)
                        st.success(t("admin.user_reactivated", lang, email=row["email"]))
                        st.rerun()

                if st.button(
                    t("admin.reset_password", lang),
                    key=f"reset_password_{row['id']}",
                    use_container_width=True,
                    disabled=not can_manage,
                ):
                    temp_password = _generate_temp_password()
                    update_user_password(row["id"], hash_password(temp_password))
                    st.success(
                        t("admin.password_reset_for", lang, email=row["email"], password=temp_password)
                    )


def _render_studies_tab():
    lang = st.session_state.get("language", "en")
    st.markdown(f"### {t('admin.studies', lang)}")

    rows = list_all_studies()

    if not rows:
        st.info(t("admin.no_studies_recorded", lang))
        return

    # collect filter options
    user_options = sorted({row["email"] for row in rows if row["email"]})
    result_options = _result_filter_options(rows, lang)

    f1, f2 = st.columns(2)

    with f1:
        selected_user = st.selectbox(
            t("admin.filter_by_user", lang),
            options=[t("admin.all_users", lang)] + user_options,
            key="admin_studies_user_filter",
        )

    with f2:
        selected_result = st.selectbox(
            t("admin.filter_by_result", lang),
            options=[t("admin.all_results", lang)] + [label for label, _ in result_options],
            key="admin_studies_result_filter",
        )

    filtered_rows = rows

    if selected_user != t("admin.all_users", lang):
        filtered_rows = [row for row in filtered_rows if row["email"] == selected_user]

    if selected_result != t("admin.all_results", lang):
        selected_result_raw = next((raw for label, raw in result_options if label == selected_result), None)
        filtered_rows = [row for row in filtered_rows if row["overall_result"] == selected_result_raw]

    if not filtered_rows:
        st.info(t("admin.no_studies_match", lang))
        return

    for row in filtered_rows:
        labels = _device_labels_from_json(row["selected_devices_json"])
        devices_text = ", ".join(labels) if labels else "-"

        with st.container():
            st.markdown("---")

            c1, c2, c3 = st.columns([2.2, 1.1, 1.2])

            with c1:
                st.markdown(f"**{row['airport_label'] or t('admin.unnamed_study', lang)}**")
                st.caption(f"{row['created_at']} · {row['email']}")
                st.write(f"{t('admin.mode', lang)}: {_format_operating_mode(row['operating_profile_mode'], lang)}")
                st.write(f"{t('admin.devices', lang)}: {devices_text}")

            with c2:
                st.write(f"**{t('admin.result', lang)}:** {next((label for label, raw in result_options if raw == row['overall_result']), row['overall_result'] or '-')}")
                st.write(f"**{t('admin.hours_per_day', lang)}:** {row['required_hours']}")
                st.write(
                    f"**{t('admin.worst_blackout_days', lang)}:** {row['worst_blackout_days'] if row['worst_blackout_days'] is not None else '-'}"
                )

            with c3:
                pct = row["worst_blackout_pct"]
                pct_text = f"{pct:.2f}%" if pct is not None else "-"
                st.write(f"**{t('admin.worst_blackout_pct', lang)}:** {pct_text}")

                if row["pdf_bytes"]:
                    st.download_button(
                        t("admin.download_pdf", lang),
                        data=row["pdf_bytes"],
                        file_name=row["pdf_name"] or "SALA_report.pdf",
                        mime="application/pdf",
                        key=f"admin_pdf_{row['id']}",
                        use_container_width=True,
                    )


def render_admin_panel():
    lang = st.session_state.get("language", "en")
    st.markdown(f"## {t('admin.panel', lang)}")

    tab1, tab2, tab3 = st.tabs([
        t("admin.access_requests", lang),
        t("admin.users", lang),
        t("admin.studies", lang),
    ])

    with tab1:
        _render_access_requests_tab()

    with tab2:
        _render_users_tab()

    with tab3:
        _render_studies_tab()
