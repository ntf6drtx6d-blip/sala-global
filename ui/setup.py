import math
import streamlit as st
import folium
from streamlit_folium import st_folium

from core.devices import DEVICES, SOLAR_ENGINES
from core.geocoding import search_airport
from core.i18n import t


def _init_setup_defaults():
    if "setup_initialized" not in st.session_state:
        st.session_state.setup_initialized = True

        if "airport_label" not in st.session_state:
            st.session_state.airport_label = ""
        if "airport_query" not in st.session_state:
            st.session_state.airport_query = ""
        if "selected_ids" not in st.session_state:
            st.session_state.selected_ids = []
        if "selected_manufacturers" not in st.session_state:
            st.session_state.selected_manufacturers = ["S4GA", "Avlite"]
        if "selected_simulation_keys" not in st.session_state:
            st.session_state.selected_simulation_keys = []
        if "per_device_config" not in st.session_state:
            st.session_state.per_device_config = {}
        if "selected_lamp_types" not in st.session_state:
            st.session_state.selected_lamp_types = {}

        if "required_hours" not in st.session_state:
            st.session_state.required_hours = 12.0
        if "operating_profile_mode" not in st.session_state:
            st.session_state.operating_profile_mode = "Custom hours per day"

        if "study_point_confirmed" not in st.session_state:
            st.session_state.study_point_confirmed = False

        if "lat" not in st.session_state:
            st.session_state.lat = 40.416775
        if "lon" not in st.session_state:
            st.session_state.lon = -3.703790

        if "search_message" not in st.session_state:
            st.session_state.search_message = ""
        if "map_click_info" not in st.session_state:
            st.session_state.map_click_info = ""
        if "last_airport_query" not in st.session_state:
            st.session_state.last_airport_query = ""
        if "airport_country" not in st.session_state:
            st.session_state.airport_country = "-"
        if "airport_icao" not in st.session_state:
            st.session_state.airport_icao = ""

    _refresh_study_ready()


def _refresh_study_ready():
    selected_ids = st.session_state.get("selected_simulation_keys") or st.session_state.get("selected_ids", [])
    study_point_confirmed = bool(st.session_state.get("study_point_confirmed", False))
    mode = st.session_state.get("operating_profile_mode")
    required_hours = st.session_state.get("required_hours")

    mode_ready = False
    if mode == "24/7":
        mode_ready = True
    elif mode == "Dusk to dawn":
        mode_ready = required_hours is not None
    elif mode == "Custom hours per day":
        mode_ready = required_hours is not None and float(required_hours) > 0

    st.session_state.study_ready = bool(
        len(selected_ids) > 0 and study_point_confirmed and mode_ready
    )


def create_map(lat, lon, label):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=13,
        control_scale=True,
        tiles="CartoDB positron",
    )

    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color="#c0392b",
        fill=True,
        fill_color="#c0392b",
        fill_opacity=0.9,
        weight=2,
        tooltip=label if label else "Selected point",
    ).add_to(fmap)

    folium.Circle(
        location=[lat, lon],
        radius=100,
        color="#c0392b",
        weight=1.2,
        fill=True,
        fill_color="#c0392b",
        fill_opacity=0.07,
    ).add_to(fmap)

    return fmap


def _day_length_hours(lat_deg: float, decl_deg: float) -> float:
    lat = math.radians(lat_deg)
    decl = math.radians(decl_deg)
    zenith = math.radians(90.833)

    cos_h = (math.cos(zenith) - math.sin(lat) * math.sin(decl)) / (
        math.cos(lat) * math.cos(decl)
    )

    if cos_h <= -1:
        return 24.0
    if cos_h >= 1:
        return 0.0

    hour_angle = math.acos(cos_h)
    return 24.0 * hour_angle / math.pi


def longest_night_hours(lat_deg: float) -> float:
    clamped_lat = max(min(float(lat_deg), 89.0), -89.0)
    decl = -23.44 if clamped_lat >= 0 else 23.44
    day = _day_length_hours(clamped_lat, decl)
    night = 24.0 - day
    return max(0.0, min(24.0, night))


def _device_label(device_id):
    d = DEVICES[device_id]
    return d["name"]


def _device_manufacturer(device_id):
    d = DEVICES[device_id]
    return d.get("manufacturer", "S4GA")


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _engine_summary(device_id, engine_key, battery_mode):
    dspec = DEVICES[device_id]
    system_type = dspec.get("system_type", "builtin")

    if system_type in ["builtin", "avlite_fixture"]:
        source_label = "Built-in solar system" if system_type == "builtin" else "Avlite built-in solar system"
        return {
            "source_label": source_label,
            "pv": _safe_float(dspec.get("pv", 0.0), 0.0),
            "batt": _safe_float(dspec.get("batt", 0.0), 0.0),
            "battery_mode": "Built-in",
        }

    if system_type == "external_engine":
        if not engine_key or engine_key not in SOLAR_ENGINES:
            return {
                "source_label": "Unknown solar engine",
                "pv": 0.0,
                "batt": 0.0,
                "battery_mode": battery_mode if battery_mode else "Std",
            }

        eng = SOLAR_ENGINES[engine_key]
        batt = eng["batt_ext"] if (battery_mode == "Ext" and eng.get("batt_ext")) else eng["batt"]

        return {
            "source_label": eng["short_name"],
            "pv": _safe_float(eng.get("pv", 0.0), 0.0),
            "batt": _safe_float(batt, 0.0),
            "battery_mode": battery_mode if battery_mode else "Std",
        }

    return {
        "source_label": "Built-in solar system",
        "pv": _safe_float(dspec.get("pv", 0.0), 0.0),
        "batt": _safe_float(dspec.get("batt", 0.0), 0.0),
        "battery_mode": "Built-in",
    }


def _default_multiselect_labels():

    labels = []
    for did in st.session_state.get("selected_ids", []):
        if did in DEVICES:
            labels.append(_device_label(did))
    return labels


def _variant_short_label(lamp_type: str) -> str:
    mapping = {
        "Runway edge light": "RWY edge",
        "Runway threshold/end light": "THR/END",
        "Taxiway edge light": "TWY edge",
        "Approach light": "APP",
        "Obstruction Type A LI light": "OBS LI",
        "TLOF light": "TLOF",
        "FATO light": "FATO",
    }
    return mapping.get(lamp_type, lamp_type)


def _simulation_key(device_id, lamp_variant=None):
    return f"{device_id}||{lamp_variant}" if lamp_variant else str(device_id)


def _simulation_label(device_id, lamp_variant=None):
    base = _device_label(device_id)
    return f"{base} / {_variant_short_label(lamp_variant)}" if lamp_variant else base


def _default_lamp_selection(device_id):
    dspec = DEVICES[device_id]
    variants = list(dspec.get("lamp_variants", {}).keys())
    if not variants:
        return []
    preferred = {
        1: ["Runway edge light", "Runway threshold/end light", "Approach light"],
        2: ["Runway edge light", "Runway threshold/end light", "Approach light"],
        3: ["Taxiway edge light", "Runway edge light"],
    }.get(device_id, [])
    selected = [x for x in preferred if x in variants]
    return selected or variants[:1]


def _apply_operating_profile():
    mode = st.session_state.get("operating_profile_mode")

    if mode == "24/7":
        st.session_state.required_hours = 24.0
    elif mode == "Dusk to dawn":
        if st.session_state.get("study_point_confirmed", False):
            st.session_state.required_hours = round(longest_night_hours(st.session_state.lat), 1)
        else:
            st.session_state.required_hours = None
    elif mode == "Custom hours per day":
        if st.session_state.get("required_hours") is None:
            st.session_state.required_hours = 12.0

    _refresh_study_ready()


def render_setup(disabled=False):
    _init_setup_defaults()
    lang = st.session_state.get("language", "en")

    st.markdown(f"## {t('ui.study_setup', lang)}")

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown(f"### 1. {t('ui.location', lang)}")

        airport_row_1, airport_row_2 = st.columns([3.2, 1.1])

        with airport_row_1:
            airport_query = st.text_input(
                t("ui.airport_name", lang),
                value=st.session_state.get("airport_query", ""),
                placeholder=t("ui.airport_placeholder", lang),
                key="airport_query_input",
                disabled=disabled,
            )

        with airport_row_2:
            st.write("")
            st.write("")
            if st.button(t("ui.find_airport", lang), use_container_width=True, disabled=disabled):
                query = airport_query.strip()

                if not query:
                    st.session_state.search_message = t("ui.please_enter_airport", lang)
                    st.rerun()

                normalized_query = " ".join(query.lower().split())
                last_query = st.session_state.get("last_airport_query")

                if last_query == normalized_query and st.session_state.get("study_point_confirmed"):
                    st.session_state.search_message = t("ui.airport_already_loaded", lang)
                    st.rerun()

                try:
                    result = search_airport(query)

                    if not result:
                        st.session_state.search_message = t("ui.no_airport_result", lang, query=query)
                        st.rerun()

                    if result.get("error") == "RATE_LIMIT":
                        st.session_state.search_message = (
                            t("ui.search_rate_limited", lang)
                        )
                        st.rerun()

                    st.session_state.airport_label = query or result["label"]
                    st.session_state.airport_query = query or result["label"]
                    st.session_state.lat = result["lat"]
                    st.session_state.lon = result["lon"]
                    st.session_state.airport_country = result.get("country", "-")
                    st.session_state.airport_icao = result.get("icao", "") or ""
                    st.session_state.study_point_confirmed = True
                    st.session_state.last_airport_query = normalized_query
                    st.session_state.search_message = t("ui.search_found", lang, display_name=result["display_name"])
                    st.session_state.map_click_info = (
                        t("ui.study_point_set_to", lang, label=st.session_state.airport_label, lat=result["lat"], lon=result["lon"])
                    )

                    if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
                        _apply_operating_profile()

                    _refresh_study_ready()
                    st.rerun()

                except Exception as e:
                    if "RATE_LIMIT_429" in str(e) or "429" in str(e):
                        st.session_state.search_message = (
                            t("ui.search_rate_limited_advanced", lang)
                        )
                    else:
                        st.session_state.search_message = t("ui.search_error", lang, error=e)
                    st.rerun()

        if st.session_state.search_message:
            if st.session_state.search_message.startswith(t("ui.search_found", lang, display_name="")):
                st.success(st.session_state.search_message)
            else:
                st.warning(st.session_state.search_message)

        airport_icao_value = st.text_input(
            t("ui.icao_optional", lang),
            value=st.session_state.get("airport_icao", ""),
            placeholder=t("ui.icao_placeholder", lang),
            max_chars=4,
            disabled=disabled,
            key="airport_icao_input",
        )
        st.session_state.airport_icao = "".join(ch for ch in airport_icao_value.upper() if ch.isalnum())[:4]

        with st.expander(t("ui.advanced_coordinates", lang), expanded=False):
            c1, c2 = st.columns(2)

            with c1:
                new_lat = st.number_input(
                    t("ui.latitude", lang),
                    min_value=-90.0,
                    max_value=90.0,
                    value=float(st.session_state.lat),
                    format="%.6f",
                    disabled=disabled,
                )

            with c2:
                new_lon = st.number_input(
                    t("ui.longitude", lang),
                    min_value=-180.0,
                    max_value=180.0,
                    value=float(st.session_state.lon),
                    format="%.6f",
                    disabled=disabled,
                )

            coords_changed = (
                abs(new_lat - st.session_state.lat) > 1e-9
                or abs(new_lon - st.session_state.lon) > 1e-9
            )

            st.session_state.lat = new_lat
            st.session_state.lon = new_lon

            if coords_changed:
                st.session_state.study_point_confirmed = True
                st.session_state.map_click_info = t("ui.point_selected", lang, lat=new_lat, lon=new_lon)
                st.session_state.search_message = ""
                if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
                    _apply_operating_profile()
                _refresh_study_ready()

        st.markdown(f"### 2. {t('ui.operating_profile_section', lang)}")
        st.caption(t("ui.operating_profile_desc", lang))

        mode_options = ["Custom hours per day", "24/7", "Dusk to dawn"]
        mode_labels = {
            "Custom hours per day": t("ui.mode_custom", lang),
            "24/7": t("ui.mode_247", lang),
            "Dusk to dawn": t("ui.mode_dusk", lang),
        }
        current_mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
        if current_mode not in mode_options:
            current_mode = "Custom hours per day"

        mode = st.radio(
            t("ui.operating_profile", lang),
            mode_options,
            horizontal=True,
            index=mode_options.index(current_mode),
            key="operating_profile_mode_radio",
            disabled=disabled,
            format_func=lambda item: mode_labels[item],
        )

        if st.session_state.get("operating_profile_mode") != mode:
            st.session_state.operating_profile_mode = mode
            _apply_operating_profile()

        if mode == "Custom hours per day":
            current_custom = st.session_state.get("required_hours")
            if current_custom is None:
                current_custom = 12.0

            required_custom = st.number_input(
                t("ui.planned_daily_hours", lang),
                min_value=0.1,
                max_value=24.0,
                value=float(current_custom),
                step=0.5,
                help=t("ui.planned_daily_hours_help", lang),
                key="required_custom_hours_input",
                disabled=disabled,
            )
            st.session_state.required_hours = required_custom
            st.caption(t("ui.planned_daily_hours_help", lang))

        elif mode == "24/7":
            st.session_state.required_hours = 24.0
            st.info(f"{t('ui.applied_profile', lang)} 24.0 {t('ui.hours_per_day_unit', lang)}")

        elif mode == "Dusk to dawn":
            if st.session_state.get("study_point_confirmed", False):
                applied = round(longest_night_hours(st.session_state.lat), 1)
                st.session_state.required_hours = applied
                st.info(
                    f"{t('ui.applied_profile', lang)} {applied:.1f} {t('ui.hours_per_day_unit', lang)} "
                    f"(based on the longest night at the selected study point)"
                )
            else:
                st.session_state.required_hours = None
                st.warning(t("ui.select_location_first", lang))

        _refresh_study_ready()

        st.markdown(f"### 3. {t('ui.manufacturer', lang)}")

        manufacturer_options = ["S4GA", "Avlite"]
        current_manufacturers = st.session_state.get("selected_manufacturers", ["S4GA", "Avlite"])
        selected_manufacturers = st.multiselect(
            t("ui.manufacturers_included", lang),
            manufacturer_options,
            default=current_manufacturers,
            key="selected_manufacturers_multiselect",
            disabled=disabled,
            help=t("ui.manufacturers_included", lang),
        )
        st.session_state.selected_manufacturers = selected_manufacturers

        st.markdown(f"### 4. {t('ui.select_devices', lang)}")

        filtered_device_ids = [
            k for k in DEVICES.keys()
            if _device_manufacturer(k) in selected_manufacturers
        ]

        device_options = {_device_label(k): k for k in filtered_device_ids}

        default_labels = [
            _device_label(did)
            for did in st.session_state.get("selected_ids", [])
            if did in filtered_device_ids
        ]

        selected_labels = st.multiselect(
            t("ui.devices_included", lang),
            list(device_options.keys()),
            default=default_labels,
            key="selected_devices_multiselect",
            disabled=disabled,
        )

        selected_ids = [device_options[label] for label in selected_labels]
        st.session_state.selected_ids = selected_ids

    with right:
        st.markdown(f"### {t('ui.study_point', lang)}")

        fmap = create_map(
            st.session_state.lat,
            st.session_state.lon,
            st.session_state.airport_label or "Selected study point",
        )

        map_data = st_folium(
            fmap,
            width=None,
            height=360,
            returned_objects=["last_clicked"],
            key="study_map_modular",
        )

        clicked = map_data.get("last_clicked") if isinstance(map_data, dict) else None
        if clicked and not disabled:
            clicked_lat = float(clicked["lat"])
            clicked_lon = float(clicked["lng"])

            if (
                abs(clicked_lat - st.session_state.lat) > 1e-7
                or abs(clicked_lon - st.session_state.lon) > 1e-7
            ):
                st.session_state.lat = clicked_lat
                st.session_state.lon = clicked_lon
                st.session_state.study_point_confirmed = True
                st.session_state.map_click_info = t("ui.point_selected", lang, lat=clicked_lat, lon=clicked_lon)
                st.session_state.search_message = ""
                if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
                    _apply_operating_profile()
                _refresh_study_ready()
                st.rerun()

        if st.session_state.map_click_info:
            st.success(st.session_state.map_click_info)

        if st.session_state.study_point_confirmed:
            st.caption(
                f"{t('ui.study_point_sent', lang)} {st.session_state.lat:.6f}, {st.session_state.lon:.6f}"
            )
        else:
            st.caption(t("ui.select_airport_or_click", lang))


    st.markdown(f"### 5. {t('ui.configure_devices', lang)}")

    per_device_config = {}
    selected_simulation_keys = []

    if not selected_ids:
        st.caption(t("ui.select_device_to_configure", lang))
        st.session_state.per_device_config = {}
        st.session_state.selected_simulation_keys = []
        st.session_state.selected_lamp_types = {}
        _refresh_study_ready()
    else:
        current_lamp_map = st.session_state.get("selected_lamp_types", {})
        current_lamp_map = {k: v for k, v in current_lamp_map.items() if k in selected_ids}
        st.session_state.selected_lamp_types = current_lamp_map

        for did in selected_ids:
            dspec = DEVICES[did]
            system_type = dspec["system_type"]
            variants = list(dspec.get("lamp_variants", {}).keys())

            if variants and did not in st.session_state["selected_lamp_types"]:
                st.session_state["selected_lamp_types"][did] = _default_lamp_selection(did)

            if variants:
                with st.expander(f"{_device_label(did)} — {t('ui.lamp_types', lang)}", expanded=False):
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button(t("ui.select_all", lang), key=f"select_all_variants_{did}", disabled=disabled):
                            st.session_state["selected_lamp_types"][did] = variants
                    with c2:
                        if st.button(t("ui.clear", lang), key=f"clear_variants_{did}", disabled=disabled):
                            st.session_state["selected_lamp_types"][did] = []

                    chosen = []
                    for lamp_variant in variants:
                        checked = lamp_variant in st.session_state["selected_lamp_types"].get(did, [])
                        is_on = st.checkbox(
                            f"{lamp_variant} — {float(dspec['lamp_variants'][lamp_variant]['power_w']):.2f} W",
                            value=checked,
                            key=f"variant_enabled_{did}_{lamp_variant}",
                            disabled=disabled,
                        )
                        if is_on:
                            chosen.append(lamp_variant)
                    st.session_state["selected_lamp_types"][did] = chosen
                    if chosen:
                        st.caption(t("ui.each_selected_lamp_type", lang))
                    else:
                        st.caption(t("ui.no_lamp_type_selected", lang))
                    active_variants = chosen
            else:
                active_variants = [None]

            for lamp_variant in active_variants:
                sim_key = _simulation_key(did, lamp_variant)
                selected_simulation_keys.append(sim_key)
                saved_cfg = (
                    st.session_state.get("per_device_config", {}).get(sim_key)
                    or st.session_state.get("per_device_config", {}).get(str(did), {})
                )

                if lamp_variant and dspec.get("lamp_variants"):
                    base_power = float(dspec["lamp_variants"][lamp_variant]["power_w"])
                else:
                    base_power = _safe_float(dspec.get("default_power", dspec.get("power", dspec.get("default_consumption", 0.0))), 0.0)

                default_power = float(saved_cfg.get("power", base_power))
                engine_key = saved_cfg.get("engine_key", dspec.get("default_engine"))
                battery_mode = saved_cfg.get("battery_mode", "Std")
                display_label = _simulation_label(did, lamp_variant)

                with st.expander(display_label, expanded=False):
                    if lamp_variant:
                        st.caption(t("ui.selected_lamp_type", lang, lamp_type=lamp_variant))

                    power = st.number_input(
                        t("ui.power_w", lang),
                        min_value=0.01,
                        value=float(default_power),
                        step=0.01,
                        key=f"power_{sim_key}",
                        disabled=disabled,
                    )

                    if system_type == "external_engine":
                        compatible = dspec["compatible_engines"]
                        if engine_key not in compatible:
                            engine_key = dspec["default_engine"]

                        engine_key = st.selectbox(
                            t("ui.solar_engine", lang),
                            compatible,
                            index=compatible.index(engine_key),
                            key=f"engine_{sim_key}",
                            disabled=disabled,
                            format_func=lambda x: f"{SOLAR_ENGINES[x]['short_name']} — {SOLAR_ENGINES[x]['name']}",
                        )

                        eng = SOLAR_ENGINES[engine_key]

                        if eng.get("batt_ext"):
                            battery_mode = st.radio(
                                t("ui.battery_mode", lang),
                                ["Std", "Ext"],
                                horizontal=True,
                                index=0 if battery_mode == "Std" else 1,
                                key=f"battery_mode_{sim_key}",
                                disabled=disabled,
                            )
                        else:
                            battery_mode = "Std"
                            st.caption(t("ui.std_only_engine", lang))
                    else:
                        engine_key = None
                        battery_mode = "Built-in"
                        st.caption(t("ui.built_in_source", lang))

                    summary = _engine_summary(did, engine_key, battery_mode)

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Power", f"{float(power):.2f} W")
                    with m2:
                        st.metric(t("ui.solar_panel", lang), f"{summary['pv']} W")
                    with m3:
                        st.metric("Battery", f"{summary['batt']} Wh")
                    with m4:
                        st.metric(t("ui.active_source", lang), summary["source_label"])

                    if system_type == "external_engine":
                        st.caption(t("ui.battery_mode_selected", lang, battery_mode=summary["battery_mode"]))

                    per_device_config[sim_key] = {
                        "device_id": did,
                        "lamp_variant": lamp_variant,
                        "display_label": display_label,
                        "power": float(power),
                        "engine_key": engine_key,
                        "battery_mode": battery_mode if battery_mode in ["Std", "Ext"] else "Std",
                    }

        st.session_state.per_device_config = per_device_config
        st.session_state.selected_simulation_keys = selected_simulation_keys
        _refresh_study_ready()

    _refresh_study_ready()
