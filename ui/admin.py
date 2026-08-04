# ui/admin.py

import json
import math
import secrets
import string

import pandas as pd
import streamlit as st

from core.i18n import t
from core.db import (
    create_device_catalog_item,
    device_catalog_code_exists,
    get_device_catalog_item,
    get_study_pdf,
    list_access_requests,
    list_device_catalog,
    list_all_users,
    list_all_studies,
    create_user,
    update_device_catalog_item,
    update_access_request_status,
    user_exists,
    update_user_active,
    update_user_password,
    update_user_profile,
)
from core.auth import hash_password
from core.catalog import get_cached_runtime_catalog, runtime_device_label, invalidate_runtime_catalog_cache
from core.person import normalize_person_name, split_person_name
from core.notify import notify_user_access_approved
from core.stats import LATITUDE_BANDS, compute_admin_stats, compute_device_feasibility
from ui.map_embed import render_folium_map
from psycopg.errors import UniqueViolation


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
    return runtime_device_label(device_id)


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


def _refresh_runtime_catalog_after_admin_save(runtime_id=None):
    invalidate_runtime_catalog_cache()
    if runtime_id is not None:
        runtime_id = int(runtime_id)
        per_device_config = dict(st.session_state.get("per_device_config", {}))
        if per_device_config:
            per_device_config = {
                key: cfg
                for key, cfg in per_device_config.items()
                if int(cfg.get("device_id", -1)) != runtime_id
            }
            st.session_state.per_device_config = per_device_config

        selected_simulation_keys = [
            key
            for key in st.session_state.get("selected_simulation_keys", [])
            if key != str(runtime_id) and not str(key).startswith(f"{runtime_id}||")
        ]
        st.session_state.selected_simulation_keys = selected_simulation_keys

        selected_lamp_types = dict(st.session_state.get("selected_lamp_types", {}))
        selected_lamp_types.pop(runtime_id, None)
        selected_lamp_types.pop(str(runtime_id), None)
        st.session_state.selected_lamp_types = selected_lamp_types

        dynamic_prefixes = [
            "variant_enabled_",
            "intensity_mode_",
            "mixed_share_",
            "mixed_intensity_a_",
            "mixed_rest_",
            "mixed_intensity_b_",
            "intensity_pct_",
            "power_",
            "quantity_",
            "engine_",
            "battery_mode_",
        ]
        stale_keys = []
        for key in list(st.session_state.keys()):
            key_str = str(key)
            if key_str.startswith(f"variant_enabled_{runtime_id}_"):
                stale_keys.append(key)
                continue
            for prefix in dynamic_prefixes:
                if key_str.startswith(prefix):
                    suffix = key_str[len(prefix):]
                    if suffix == str(runtime_id) or suffix.startswith(f"{runtime_id}||"):
                        stale_keys.append(key)
                    break
        for key in stale_keys:
            st.session_state.pop(key, None)

    st.session_state.pop("runtime_devices", None)
    st.session_state.pop("runtime_solar_engines", None)


def _safe_json_value(raw_value, fallback):
    if raw_value is None:
        return fallback
    if isinstance(raw_value, (list, dict)):
        return raw_value
    try:
        return json.loads(raw_value)
    except Exception:
        return fallback


def _number_or_none(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _default_cutoff_pct(existing):
    raw = existing.get("cutoff_pct")
    try:
        if raw is not None and float(raw) > 0:
            return float(raw)
    except Exception:
        pass

    code = str(existing.get("code") or "").upper()
    battery_type = str(existing.get("battery_type") or "").upper()
    has_battery = bool(existing.get("battery_wh"))
    if "SP-301" in code or "NIMH" in battery_type or "LIFEPO4" in battery_type or "LFP" in battery_type:
        return 20.0
    if has_battery:
        return 30.0
    return 0.0


def _parse_float_list(raw_text):
    values = []
    for item in str(raw_text or "").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except Exception:
            continue
    return values


def _lamp_variants_to_rows(lamp_variants):
    if not isinstance(lamp_variants, dict):
        return []
    rows = []
    for name, config in lamp_variants.items():
        try:
            power_w = float((config or {}).get("power_w", 0.0))
        except Exception:
            power_w = 0.0
        rows.append({"Lamp type": str(name), "Power (W)": power_w})
    return rows


def _parse_lamp_variants_rows(rows):
    variants = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Lamp type", "")).strip()
        if not name:
            continue
        try:
            power_w = float(row.get("Power (W)", 0.0) or 0.0)
        except Exception:
            continue
        variants[name] = {"power_w": power_w}
    return variants


def _entity_type_options(lang):
    return {
        "built_in_device": t("admin.entity_built_in_device", lang),
        "powered_device": t("admin.entity_powered_device", lang),
        "solar_engine": t("admin.entity_solar_engine", lang),
    }


def _panel_configuration_options(lang):
    return {
        "single_panel": t("admin.panel_single", lang),
        "double_v_shape": t("admin.panel_double_v", lang),
        "quad_90deg": t("admin.panel_quad_90", lang),
    }


def _catalog_form_payload(prefix, lang, existing=None):
    existing = existing or {}
    entity_options = _entity_type_options(lang)
    entity_keys = list(entity_options.keys())
    existing_entity_type = existing.get("entity_type", "built_in_device")
    if existing_entity_type not in entity_keys:
        existing_entity_type = "built_in_device"

    selected_entity_type = st.selectbox(
        t("admin.entity_type", lang),
        options=entity_keys,
        index=entity_keys.index(existing_entity_type),
        format_func=lambda value: entity_options[value],
        key=f"{prefix}_entity_type",
    )

    code = st.text_input(t("admin.device_code", lang), value=existing.get("code", ""), key=f"{prefix}_code")
    manufacturer = st.text_input(
        t("admin.manufacturer", lang),
        value=existing.get("manufacturer", ""),
        key=f"{prefix}_manufacturer",
    )
    name = st.text_input(t("admin.device_name", lang), value=existing.get("name", ""), key=f"{prefix}_name")
    is_active = st.checkbox(
        t("admin.catalog_active", lang),
        value=bool(existing.get("is_active", True)),
        key=f"{prefix}_is_active",
    )

    battery_fields = st.container()
    system_fields = st.container()
    panel_fields = st.container()

    supports_intensity = False
    default_power_w = None
    default_engine_code = None
    compatible_engine_codes = []
    has_external_battery_option = False
    external_battery_wh = None
    panel_configuration = None
    panel_wp = None
    panel_tilt_deg = None
    panel_tilt_options = []
    battery_type = None
    battery_wh = None
    cutoff_pct = None
    standby_power_w = None
    metadata = _safe_json_value(existing.get("metadata"), {})
    lamp_variants = _safe_json_value(metadata.get("lamp_variants"), {})
    default_lamp_variant = metadata.get("default_lamp_variant")

    if selected_entity_type != "solar_engine":
        with system_fields:
            default_power_w = st.number_input(
                t("admin.default_power_w", lang),
                min_value=0.0,
                value=float(existing.get("default_power_w") or 0.0),
                step=0.1,
                key=f"{prefix}_default_power_w",
            )
            supports_intensity = st.checkbox(
                t("admin.supports_intensity_adjustment", lang),
                value=bool(existing.get("supports_intensity_adjustment")),
                key=f"{prefix}_supports_intensity_adjustment",
            )
            standby_power_w = st.number_input(
                t("admin.standby_power_w", lang),
                min_value=0.0,
                value=float(existing.get("standby_power_w") or 0.0),
                step=0.01,
                key=f"{prefix}_standby_power_w",
            )

    with battery_fields:
        battery_type = st.text_input(
            t("admin.battery_type", lang),
            value=existing.get("battery_type") or "",
            key=f"{prefix}_battery_type",
        )
        battery_wh = st.number_input(
            t("admin.battery_size_wh", lang),
            min_value=0.0,
            value=float(existing.get("battery_wh") or 0.0),
            step=1.0,
            key=f"{prefix}_battery_wh",
        )
        cutoff_pct = st.number_input(
            t("admin.cutoff_limit_pct", lang),
            min_value=0.0,
            max_value=100.0,
            value=_default_cutoff_pct(existing),
            step=1.0,
            key=f"{prefix}_cutoff_pct",
        )

    if selected_entity_type in {"built_in_device", "solar_engine"}:
        with panel_fields:
            panel_options = _panel_configuration_options(lang)
            panel_keys = list(panel_options.keys())
            existing_panel_configuration = existing.get("panel_configuration") or "single_panel"
            if existing_panel_configuration not in panel_keys:
                existing_panel_configuration = "single_panel"
            panel_configuration = st.selectbox(
                t("admin.panel_configuration", lang),
                options=panel_keys,
                index=panel_keys.index(existing_panel_configuration),
                format_func=lambda value: panel_options[value],
                key=f"{prefix}_panel_configuration",
            )
            panel_wp = st.number_input(
                t("admin.solar_panel_wp", lang),
                min_value=0.0,
                value=float(existing.get("panel_wp") or 0.0),
                step=0.1,
                key=f"{prefix}_panel_wp",
            )
            panel_tilt_deg = st.number_input(
                t("admin.default_tilt_deg", lang),
                min_value=0.0,
                max_value=90.0,
                value=float(existing.get("panel_tilt_deg") or 0.0),
                step=1.0,
                key=f"{prefix}_panel_tilt_deg",
            )
            tilt_text = st.text_input(
                t("admin.tilt_options_deg", lang),
                value=", ".join(str(x) for x in _safe_json_value(existing.get("panel_tilt_options"), [])),
                key=f"{prefix}_panel_tilt_options",
            )
            panel_tilt_options = _parse_float_list(tilt_text)

    if selected_entity_type == "built_in_device":
        st.caption(t("admin.lamp_variants_help", lang))
        variants_df = pd.DataFrame(
            _lamp_variants_to_rows(lamp_variants),
            columns=["Lamp type", "Power (W)"],
        )
        variants_edited = st.data_editor(
            variants_df,
            key=f"{prefix}_lamp_variants_editor",
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "Lamp type": st.column_config.TextColumn(
                    t("admin.lamp_variants", lang),
                    required=True,
                ),
                "Power (W)": st.column_config.NumberColumn(
                    t("admin.default_power_w", lang),
                    min_value=0.0,
                    step=0.1,
                    format="%.2f",
                    required=True,
                ),
            },
        )
        lamp_variants = _parse_lamp_variants_rows(variants_edited.to_dict("records"))
        variant_names = list(lamp_variants.keys())
        if variant_names:
            if default_lamp_variant not in variant_names:
                default_lamp_variant = variant_names[0]
            default_lamp_variant = st.selectbox(
                t("admin.default_lamp_variant", lang),
                options=variant_names,
                index=variant_names.index(default_lamp_variant),
                key=f"{prefix}_default_lamp_variant",
            )
        else:
            default_lamp_variant = None

    if selected_entity_type == "powered_device":
        _, runtime_engines = get_cached_runtime_catalog()
        engine_codes = sorted(runtime_engines.keys())
        existing_default_engine = existing.get("default_engine_code")
        if existing_default_engine not in engine_codes:
            existing_default_engine = engine_codes[0] if engine_codes else None
        default_engine_code = st.selectbox(
            t("admin.default_solar_engine", lang),
            options=engine_codes,
            index=engine_codes.index(existing_default_engine) if existing_default_engine in engine_codes else 0,
            key=f"{prefix}_default_engine_code",
        ) if engine_codes else None
        compatible_default = _safe_json_value(existing.get("compatible_engine_codes"), [])
        compatible_engine_codes = st.multiselect(
            t("admin.compatible_solar_engines", lang),
            options=engine_codes,
            default=compatible_default or ([default_engine_code] if default_engine_code else []),
            key=f"{prefix}_compatible_engine_codes",
        )

    if selected_entity_type == "solar_engine":
        has_external_battery_option = st.checkbox(
            t("admin.has_external_battery_option", lang),
            value=bool(existing.get("has_external_battery_option")),
            key=f"{prefix}_has_external_battery_option",
        )
        if has_external_battery_option:
            external_battery_wh = st.number_input(
                t("admin.external_battery_size_wh", lang),
                min_value=0.0,
                value=float(metadata.get("battery_wh_external") or 0.0),
                step=1.0,
                key=f"{prefix}_external_battery_wh",
            )

    source_note = st.text_area(
        t("admin.source_note", lang),
        value=str(metadata.get("source_note") or ""),
        key=f"{prefix}_source_note",
        height=80,
    )
    if source_note.strip():
        metadata["source_note"] = source_note.strip()
    else:
        metadata.pop("source_note", None)
    if selected_entity_type == "built_in_device" and lamp_variants:
        metadata["lamp_variants"] = lamp_variants
        metadata["default_lamp_variant"] = default_lamp_variant
    else:
        metadata.pop("lamp_variants", None)
        metadata.pop("default_lamp_variant", None)
    if selected_entity_type == "solar_engine" and has_external_battery_option and external_battery_wh:
        metadata["battery_wh_external"] = float(external_battery_wh)
    else:
        metadata.pop("battery_wh_external", None)

    system_type = {
        "built_in_device": "builtin",
        "powered_device": "external_engine",
        "solar_engine": "solar_engine",
    }[selected_entity_type]

    return {
        "code": code.strip(),
        "entity_type": selected_entity_type,
        "manufacturer": manufacturer.strip(),
        "name": name.strip(),
        "system_type": system_type,
        "default_power_w": _number_or_none(default_power_w),
        "battery_type": battery_type.strip() or None,
        "battery_wh": _number_or_none(battery_wh),
        "cutoff_pct": _number_or_none(cutoff_pct),
        "standby_power_w": _number_or_none(standby_power_w),
        "supports_intensity_adjustment": supports_intensity,
        "panel_configuration": panel_configuration,
        "panel_wp": _number_or_none(panel_wp),
        "panel_tilt_options": panel_tilt_options,
        "panel_tilt_deg": _number_or_none(panel_tilt_deg),
        "default_engine_code": default_engine_code,
        "compatible_engine_codes": compatible_engine_codes,
        "has_external_battery_option": has_external_battery_option,
        "metadata": metadata,
        "is_active": is_active,
    }


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
                        emailed = notify_user_access_approved(
                            email=email,
                            full_name=row["full_name"],
                            temp_password=temp_password,
                        )
                        if not emailed:
                            st.warning(t("admin.approval_email_not_sent", lang))
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

            with st.expander(t("admin.edit_user", lang), expanded=False):
                first_name, last_name = split_person_name(row.get("full_name") or "")
                edit_email = st.text_input(
                    t("ui.email", lang),
                    value=row["email"] or "",
                    key=f"admin_edit_email_{row['id']}",
                )
                edit_first_name = st.text_input(
                    t("ui.first_name", lang),
                    value=first_name,
                    key=f"admin_edit_first_name_{row['id']}",
                )
                edit_last_name = st.text_input(
                    t("ui.last_name", lang),
                    value=last_name,
                    key=f"admin_edit_last_name_{row['id']}",
                )
                edit_org = st.text_input(
                    t("ui.organization", lang),
                    value=row.get("organization") or "",
                    key=f"admin_edit_org_{row['id']}",
                )
                edit_role = st.selectbox(
                    t("ui.role", lang),
                    options=["user", "admin"],
                    index=0 if row.get("role") != "admin" else 1,
                    key=f"admin_edit_role_{row['id']}",
                )

                if st.button(
                    t("admin.save_user_changes", lang),
                    key=f"admin_save_user_{row['id']}",
                    use_container_width=True,
                ):
                    normalized_first = normalize_person_name(edit_first_name)
                    normalized_last = normalize_person_name(edit_last_name)
                    normalized_email = str(edit_email or "").strip().lower()
                    normalized_org = str(edit_org or "").strip() or None

                    if not normalized_first:
                        st.error(t("ui.enter_first_name", lang))
                    elif not normalized_email:
                        st.error(t("ui.enter_email", lang))
                    else:
                        full_name = " ".join(part for part in [normalized_first, normalized_last] if part).strip()
                        try:
                            updated_user = update_user_profile(
                                user_id=row["id"],
                                email=normalized_email,
                                full_name=full_name,
                                organization=normalized_org,
                                role=edit_role,
                                actor_role=st.session_state.get("auth_role"),
                            )
                        except UniqueViolation:
                            st.error(t("ui.email_already_in_use", lang))
                        except PermissionError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(str(exc))
                        else:
                            if updated_user:
                                if row["id"] == current_user_id:
                                    st.session_state.auth_email = updated_user["email"]
                                    st.session_state.auth_full_name = updated_user.get("full_name")
                                    st.session_state.auth_organization = updated_user.get("organization")
                                    st.session_state.auth_role = updated_user.get("role")
                                    st.session_state.auth_token_refresh_required = True
                                st.success(t("admin.user_updated", lang, email=updated_user["email"]))
                                st.rerun()


def _render_studies_tab():
    lang = st.session_state.get("language", "en")
    st.markdown(f"### {t('admin.studies', lang)}")

    studies_limit = 300
    rows = list_all_studies(limit=studies_limit)

    if not rows:
        st.info(t("admin.no_studies_recorded", lang))
        return

    if len(rows) >= studies_limit:
        st.caption(f"Showing the {studies_limit} most recent studies.")

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

                # PDF bytes are intentionally not part of the listing query (see
                # list_all_studies) — fetch a single study's PDF only once the
                # admin actually asks for it, and only for that one row.
                reveal_key = f"admin_pdf_reveal_{row['id']}"
                if not st.session_state.get(reveal_key):
                    if st.button(
                        t("admin.download_pdf", lang),
                        key=f"admin_pdf_prepare_{row['id']}",
                        use_container_width=True,
                    ):
                        st.session_state[reveal_key] = True
                        st.rerun()
                else:
                    pdf_name, pdf_bytes = get_study_pdf(row["id"])
                    if pdf_bytes:
                        st.download_button(
                            t("admin.download_pdf", lang),
                            data=pdf_bytes,
                            file_name=pdf_name or "SALA_report.pdf",
                            mime="application/pdf",
                            key=f"admin_pdf_{row['id']}",
                            use_container_width=True,
                        )


def _render_device_database_tab():
    lang = st.session_state.get("language", "en")
    st.markdown(f"### {t('admin.device_database', lang)}")

    rows = list_device_catalog()
    entity_options = _entity_type_options(lang)
    entity_filter_options = [t("admin.all_device_types", lang)] + list(entity_options.values())
    selected_filter = st.selectbox(
        t("admin.filter_by_device_type", lang),
        options=entity_filter_options,
        key="admin_device_catalog_filter",
    )

    filtered_rows = rows
    if selected_filter != t("admin.all_device_types", lang):
        selected_entity_type = next(
            (key for key, label in entity_options.items() if label == selected_filter),
            None,
        )
        if selected_entity_type:
            filtered_rows = [row for row in rows if row["entity_type"] == selected_entity_type]

    with st.expander(t("admin.add_catalog_item", lang), expanded=False):
        with st.form("admin_catalog_create_form", border=False):
            payload = _catalog_form_payload("admin_catalog_create", lang)
            create_submitted = st.form_submit_button(
                t("admin.save_new_catalog_item", lang),
                width="stretch",
            )
        if create_submitted:
            if not payload["code"]:
                st.error(t("admin.catalog_code_required", lang))
            elif device_catalog_code_exists(payload["code"]):
                st.error(t("admin.catalog_code_exists", lang, code=payload["code"]))
            elif not payload["manufacturer"]:
                st.error(t("admin.catalog_manufacturer_required", lang))
            elif not payload["name"]:
                st.error(t("admin.catalog_name_required", lang))
            else:
                created_id = create_device_catalog_item(payload)
                created = get_device_catalog_item(created_id) if created_id else None
                _refresh_runtime_catalog_after_admin_save(created.get("runtime_id") if created else None)
                st.success(t("admin.catalog_item_created", lang, code=payload["code"]))
                st.rerun()

    if not filtered_rows:
        st.info(t("admin.no_catalog_items", lang))
        return

    for row in filtered_rows:
        title = f"{row['manufacturer']} · {row['name']} ({row['code']})"
        with st.expander(title, expanded=False):
            st.caption(
                f"{entity_options.get(row['entity_type'], row['entity_type'])} · "
                f"{t('admin.active', lang)}: {t('admin.yes', lang) if row['is_active'] else t('admin.no', lang)}"
            )
            with st.form(f"admin_catalog_edit_form_{row['id']}", border=False):
                payload = _catalog_form_payload(f"admin_catalog_edit_{row['id']}", lang, existing=row)
                edit_submitted = st.form_submit_button(
                    t("admin.save_catalog_changes", lang),
                    width="stretch",
                )
            if edit_submitted:
                if not payload["code"]:
                    st.error(t("admin.catalog_code_required", lang))
                elif device_catalog_code_exists(payload["code"], exclude_id=row["id"]):
                    st.error(t("admin.catalog_code_exists", lang, code=payload["code"]))
                elif not payload["manufacturer"]:
                    st.error(t("admin.catalog_manufacturer_required", lang))
                elif not payload["name"]:
                    st.error(t("admin.catalog_name_required", lang))
                else:
                    update_device_catalog_item(row["id"], payload)
                    _refresh_runtime_catalog_after_admin_save(row.get("runtime_id"))
                    st.success(t("admin.catalog_item_updated", lang, code=payload["code"]))
                    st.rerun()


def _format_seconds_stat(seconds):
    if seconds is None:
        return "—"
    seconds = int(round(seconds))
    minutes, secs = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _weekly_fs_chart(weekly_counts, lang):
    import altair as alt

    internal_label = t("admin.stat_series_internal", lang)
    external_label = t("admin.stat_series_external", lang)
    df_long = pd.DataFrame(
        [
            {"week_start": row["week_start"], "series": internal_label, "count": row["internal"]}
            for row in weekly_counts
        ]
        + [
            {"week_start": row["week_start"], "series": external_label, "count": row["external"]}
            for row in weekly_counts
        ]
    )
    color = alt.Color(
        "series:N",
        title=None,
        sort=[internal_label, external_label],
        scale=alt.Scale(
            domain=[internal_label, external_label],
            range=["#1d4ed8", "#f59e0b"],
        ),
        legend=alt.Legend(orient="top"),
    )
    base = alt.Chart(df_long).encode(
        x=alt.X("week_start:O", title=None, axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("count:Q", title=None, scale=alt.Scale(nice=True)),
        color=color,
    )
    lines = base.mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=70, filled=True)).encode(
        tooltip=[alt.Tooltip("week_start:O", title="Week"), "series:N", "count:Q"],
    )
    # Value labels on every point, so the counts are readable directly
    # instead of having to be estimated against the y-axis. The two series
    # are labelled in opposite directions so their labels can't overlap
    # where the lines cross or share a value.
    labels_internal = (
        base.transform_filter(alt.datum.series == internal_label)
        .mark_text(dy=-13, fontSize=12, fontWeight="bold")
        .encode(text="count:Q")
    )
    labels_external = (
        base.transform_filter(alt.datum.series == external_label)
        .mark_text(dy=15, fontSize=12, fontWeight="bold")
        .encode(text="count:Q")
    )
    return (lines + labels_internal + labels_external).properties(height=340)


_MAP_STATUS_COLOURS = {
    "PASS": "#16a34a",
    "FAIL": "#dc2626",
    "MIXED": "#f59e0b",
    "UNKNOWN": "#94a3b8",
}


def _zoom_for_span(lat_span: float, lon_span: float) -> int:
    # Deterministic zoom from the data's bounding box, computed server-side
    # rather than via Leaflet's fitBounds() - fitBounds() needs the map
    # container's actual pixel size to compute a zoom, and calling it
    # before the container has been laid out (as happens inside
    # Streamlit's iframe on first render) produces a garbage result
    # (observed: zoom 20 centered on the wrong continent for a
    # near-global bounding box). A world at zoom Z is ~360/2^Z degrees
    # wide, so picking Z so that width covers the span (with padding)
    # gives a reasonable "fit" without needing the container size at all.
    # The lower bound is 2, not 1: tiles don't repeat (no_wrap), so at
    # zoom 1 the whole world is only 512px wide and a wide dashboard panel
    # is left with large empty margins either side. Zoom 2 doubles that to
    # 1024px, which fills the panel while still showing +/-74 degrees of
    # latitude at the map height used below - i.e. every location a study
    # is realistically run at. Zoom 3 would fill an even wider panel but
    # starts clipping northern Europe and New Zealand, so 2 is the ceiling
    # for a global spread.
    span = max(lat_span, lon_span, 0.01) * 1.4
    zoom = math.log2(360.0 / span)
    return max(2, min(9, int(zoom)))


def _build_stats_folium_map(map_points):
    import folium

    lats = [p["lat"] for p in map_points]
    lons = [p["lon"] for p in map_points]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    zoom_start = _zoom_for_span(max(lats) - min(lats), max(lons) - min(lons)) if len(map_points) > 1 else 8

    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        control_scale=True,
        tiles=None,
        max_bounds=True,
        min_zoom=2,
    )
    folium.TileLayer("CartoDB positron", no_wrap=True).add_to(fmap)

    # Tiles don't repeat (no_wrap), and a whole-world view can't fill a very
    # wide panel without zooming in far enough to clip northern Europe, so
    # some horizontal margin is unavoidable. Paint that margin the same
    # colour as the basemap's water instead of leaving it browser-grey, so
    # it reads as ocean continuing past the map rather than as a partially
    # rendered map.
    fmap.get_root().header.add_child(
        folium.Element("<style>.folium-map, .leaflet-container { background: #d4dadc !important; }</style>")
    )

    # How large the map can be drawn depends on the panel's real pixel
    # width, which isn't knowable server-side: a globally-spread dataset
    # spans ~295 degrees of longitude, which fits at zoom 3 on a ~1800px+
    # panel (filling it) but would cut off the outermost points on a
    # narrower one. So let Leaflet pick: fitBounds chooses the largest
    # zoom at which every point still fits the actual container, which
    # fills the width whenever the screen allows and falls back to a
    # smaller zoom rather than dropping data when it doesn't.
    #
    # Deferred behind a timeout on purpose - called inline it runs before
    # the container has been laid out, and Leaflet then computes the zoom
    # from a zero-sized box (observed: zoom 20 on the wrong continent).
    # zoom_start above remains the fallback if this never runs.
    if len(map_points) > 1:
        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        fmap.get_root().script.add_child(
            folium.Element(
                f"""
                setTimeout(function () {{
                    try {{
                        var m = {fmap.get_name()};
                        if (m && m.getSize().x > 0) {{
                            m.invalidateSize({{animate: false}});
                            m.fitBounds({bounds}, {{padding: [18, 18], animate: false}});
                        }}
                    }} catch (e) {{}}
                }}, 250);
                """
            )
        )

    for p in map_points:
        colour = _MAP_STATUS_COLOURS.get(p.get("status"), _MAP_STATUS_COLOURS["UNKNOWN"])
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=4,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.85,
            weight=1,
            tooltip=f"{p['label']} — {p['count']} FS — {p.get('status', '—')}",
        ).add_to(fmap)

    return fmap


def render_admin_dashboard():
    lang = st.session_state.get("language", "en")
    st.markdown(f"### {t('admin.dashboard_title', lang)}")

    if st.button(f"▶ {t('admin.dashboard_run_fs_cta', lang)}", type="primary", key="dashboard_run_fs_cta"):
        st.session_state.admin_active_page = "feasibility"
        st.rerun()

    with st.spinner(t("admin.statistics_loading", lang)):
        stats = compute_admin_stats(weeks=8)

    pending_requests = sum(1 for r in list_access_requests() if r.get("status") == "new")
    if pending_requests or stats["dormant_users"]:
        st.markdown(f"#### {t('admin.dashboard_needs_attention_title', lang)}")
        att1, att2 = st.columns(2)
        with att1:
            if pending_requests:
                st.warning(t("admin.dashboard_pending_requests", lang, count=pending_requests))
            else:
                st.success(t("admin.dashboard_no_pending_requests", lang))
        with att2:
            if stats["dormant_users"]:
                st.info(
                    t(
                        "admin.dashboard_dormant_users",
                        lang,
                        count=stats["dormant_users"],
                        days=stats["active_window_days"],
                    )
                )

    if stats["fs_listing"]:
        st.markdown(f"#### {t('admin.dashboard_recent_activity_title', lang)}")
        recent_df = pd.DataFrame(
            [
                {
                    t("admin.stat_col_airport", lang): row["airport"],
                    t("admin.stat_col_name", lang): row["full_name"],
                    t("admin.stat_col_organization", lang): row["organization"],
                    t("admin.stat_col_status", lang): row["status"],
                    t("admin.stat_col_days_since", lang): row["days_since"],
                }
                for row in stats["fs_listing"][:8]
            ]
        )
        st.dataframe(recent_df, hide_index=True, use_container_width=True)

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("admin.stat_total_fs", lang), stats["total_fs"])
    c2.metric(t("admin.stat_internal_vs_external", lang), f"{stats['internal_fs']} / {stats['external_fs']}")
    c3.metric(t("admin.stat_total_users", lang), stats["total_users"])
    c4.metric(
        t("admin.stat_active_dormant_users", lang, days=stats["active_window_days"]),
        f"{stats['active_users']} / {stats['dormant_users']}",
    )

    st.caption(t("admin.stat_headline_caption", lang))

    st.markdown(f"#### {t('admin.stat_weekly_chart_title', lang)}")
    st.caption(t("admin.stat_weekly_chart_caption", lang))
    if not stats["weekly_counts"] or sum(r["total"] for r in stats["weekly_counts"]) == 0:
        st.info(t("admin.stat_no_data", lang))
    else:
        st.altair_chart(_weekly_fs_chart(stats["weekly_counts"], lang), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"#### {t('admin.stat_pass_fail_title', lang)}")
        status_counts = stats["status_counts"]
        if not status_counts:
            st.info(t("admin.stat_no_data", lang))
        else:
            status_df = pd.DataFrame(
                {"status": list(status_counts.keys()), "count": list(status_counts.values())}
            ).set_index("status")
            st.bar_chart(status_df)

        st.metric(
            t("admin.stat_recalculation_rate", lang),
            f"{stats['recalculation_rate_pct']:.0f}%",
            help=t("admin.stat_recalculation_rate_help", lang, count=stats["recalculated_count"], total=stats["total_fs"]),
        )

    with col_b:
        st.markdown(f"#### {t('admin.stat_generation_time_title', lang)}")
        if stats["generation_time_sample_size"] == 0:
            st.info(t("admin.stat_no_data", lang))
        else:
            g1, g2 = st.columns(2)
            g1.metric(t("admin.stat_avg_time", lang), _format_seconds_stat(stats["avg_generation_seconds"]))
            g2.metric(t("admin.stat_median_time", lang), _format_seconds_stat(stats["median_generation_seconds"]))
            st.caption(t("admin.stat_generation_time_caption", lang, count=stats["generation_time_sample_size"]))

    alltime_caption = t("admin.stat_alltime_caption", lang, total=stats["total_fs"])

    st.markdown(f"#### {t('admin.stat_top_devices_title', lang)}")
    st.caption(alltime_caption)
    if not stats["top_devices"]:
        st.info(t("admin.stat_no_data", lang))
    else:
        for name, count in stats["top_devices"]:
            st.write(f"**{name}** — {count}")

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown(f"#### {t('admin.stat_top_organizations_title', lang)}")
        st.caption(alltime_caption)
        if not stats["top_organizations"]:
            st.info(t("admin.stat_no_data", lang))
        else:
            org_df = pd.DataFrame(stats["top_organizations"], columns=["organization", "count"])
            st.dataframe(org_df, hide_index=True, use_container_width=True)

    with col_d:
        st.markdown(f"#### {t('admin.stat_top_users_title', lang)}")
        st.caption(alltime_caption)
        if not stats["top_users"]:
            st.info(t("admin.stat_no_data", lang))
        else:
            users_df = pd.DataFrame(stats["top_users"], columns=["user", "count"])
            st.dataframe(users_df, hide_index=True, use_container_width=True)

    st.markdown(f"#### {t('admin.stat_map_title', lang)}")
    st.caption(t("admin.stat_map_caption", lang))
    st.caption(t("admin.stat_map_legend", lang))
    map_points = stats["map_points"]
    if not map_points:
        st.info(t("admin.stat_no_data", lang))
    else:
        render_folium_map(_build_stats_folium_map(map_points), height=720, key="admin_stats_map")
        top_points = sorted(map_points, key=lambda p: -p["count"])[:10]
        table_df = pd.DataFrame(
            [
                {
                    t("admin.stat_col_airport", lang): p["label"],
                    t("admin.stat_col_status", lang): p.get("status", "—"),
                    "FS": p["count"],
                }
                for p in top_points
            ]
        )
        st.dataframe(table_df, hide_index=True, use_container_width=True)

    st.markdown(f"#### {t('admin.stat_fs_listing_title', lang)}")
    st.caption(t("admin.stat_fs_listing_caption", lang))
    fs_listing = stats["fs_listing"]
    if not fs_listing:
        st.info(t("admin.stat_no_data", lang))
    else:
        listing_df = pd.DataFrame(
            [
                {
                    t("admin.stat_col_airport", lang): row["airport"],
                    t("admin.stat_col_country", lang): row["country"],
                    t("admin.stat_col_name", lang): row["full_name"],
                    t("admin.stat_col_organization", lang): row["organization"],
                    t("admin.stat_col_status", lang): row["status"],
                    t("admin.stat_col_date", lang): row["date"].strftime("%Y-%m-%d") if row["date"] else "-",
                    t("admin.stat_col_days_since", lang): row["days_since"],
                }
                for row in fs_listing
            ]
        )
        st.dataframe(listing_df, hide_index=True, use_container_width=True)
        st.download_button(
            f"📥 {t('admin.stat_download_csv', lang)}",
            data=listing_df.to_csv(index=False).encode("utf-8"),
            file_name="sala_fs_listing.csv",
            mime="text/csv",
        )

    _render_device_feasibility_section(lang)


def _render_device_feasibility_section(lang):
    st.divider()
    st.markdown(f"#### {t('admin.stat_device_feasibility_title', lang)}")
    st.caption(t("admin.stat_device_feasibility_caption", lang))

    with st.spinner(t("admin.statistics_loading", lang)):
        feasibility = compute_device_feasibility()

    if not feasibility:
        st.info(t("admin.stat_no_data", lang))
        return

    device_codes = list(feasibility.keys())
    selected = st.selectbox(
        t("admin.stat_device_picker", lang),
        device_codes,
        format_func=lambda code: f"{code} ({feasibility[code]['tested']})",
        key="admin_device_feasibility_picker",
    )
    data = feasibility[selected]

    m1, m2, m3 = st.columns(3)
    m1.metric(t("admin.stat_device_tested", lang), data["tested"])
    m2.metric(t("admin.stat_device_passed", lang), data["passed"])
    pass_rate = (data["passed"] / data["tested"] * 100.0) if data["tested"] else 0.0
    m3.metric(t("admin.stat_device_pass_rate", lang), f"{pass_rate:.0f}%")

    band_labels = {
        "tropical": t("admin.stat_band_tropical", lang),
        "subtropical": t("admin.stat_band_subtropical", lang),
        "high": t("admin.stat_band_high", lang),
    }
    band_rows = []
    for band_key, _low, _high in LATITUDE_BANDS:
        values = data["bands"].get(band_key)
        if not values or not values["tested"]:
            continue
        band_rows.append(
            {
                t("admin.stat_col_band", lang): band_labels[band_key],
                t("admin.stat_col_tested", lang): values["tested"],
                t("admin.stat_col_passed", lang): values["passed"],
                t("admin.stat_col_max_pass_hours", lang): (
                    f"{values['max_pass_hours']:.1f}" if values["max_pass_hours"] is not None else "—"
                ),
                t("admin.stat_col_min_fail_hours", lang): (
                    f"{values['min_fail_hours']:.1f}" if values["min_fail_hours"] is not None else "—"
                ),
            }
        )

    if band_rows:
        st.dataframe(pd.DataFrame(band_rows), hide_index=True, use_container_width=True)
        st.caption(t("admin.stat_band_table_caption", lang))
    else:
        st.info(t("admin.stat_no_data", lang))

    points = [p for p in data["points"] if p.get("lat") is not None and p.get("lon") is not None]
    if points:
        st.caption(t("admin.stat_map_legend_pass_fail", lang))
        render_folium_map(
            _build_stats_folium_map(points),
            height=720,
            key=f"admin_device_map_{selected}",
        )


def render_admin_panel():
    lang = st.session_state.get("language", "en")
    st.markdown(f"## {t('admin.panel', lang)}")

    tab1, tab2, tab3, tab4 = st.tabs([
        t("admin.access_requests", lang),
        t("admin.users", lang),
        t("admin.studies", lang),
        t("admin.device_database", lang),
    ])

    with tab1:
        _render_access_requests_tab()

    with tab2:
        _render_users_tab()

    with tab3:
        _render_studies_tab()

    with tab4:
        _render_device_database_tab()
