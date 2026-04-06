import math
import streamlit as st
import folium
from streamlit_folium import st_folium

from core.devices import DEVICES, SOLAR_ENGINES
from core.geocoding import search_airport


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

    if dspec["system_type"] == "builtin":
        return {
            "source_label": "Built-in solar system",
            "pv": dspec.get("pv", 0),
            "batt": dspec.get("batt", 0),
            "battery_mode": "Built-in",
        }

    eng = SOLAR_ENGINES[engine_key]
    batt = eng["batt_ext"] if (battery_mode == "Ext" and eng.get("batt_ext")) else eng["batt"]

    return {
        "source_label": eng["short_name"],
        "pv": eng["pv"],
        "batt": batt,
        "battery_mode": battery_mode,
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

    st.markdown("## Study setup")

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("### 1. Location")

        airport_row_1, airport_row_2 = st.columns([3.2, 1.1])

        with airport_row_1:
            airport_query = st.text_input(
                "Airport name",
                value=st.session_state.get("airport_query", ""),
                placeholder="e.g. Madrid Barajas Airport",
                key="airport_query_input",
                disabled=disabled,
            )

        with airport_row_2:
            st.write("")
            st.write("")
            if st.button("Find airport", use_container_width=True, disabled=disabled):
                query = airport_query.strip()

                if not query:
                    st.session_state.search_message = "Please enter an airport name."
                    st.rerun()

                normalized_query = " ".join(query.lower().split())
                last_query = st.session_state.get("last_airport_query")

                if last_query == normalized_query and st.session_state.get("study_point_confirmed"):
                    st.session_state.search_message = "This airport is already loaded."
                    st.rerun()

                try:
                    result = search_airport(query)

                    if not result:
                        st.session_state.search_message = f"No result found for '{query}'."
                        st.rerun()

                    if result.get("error") == "RATE_LIMIT":
                        st.session_state.search_message = (
                            "Search is temporarily rate-limited by the map service. "
                            "Please wait a moment and try again."
                        )
                        st.rerun()

                    st.session_state.airport_label = query or result["label"]
                    st.session_state.airport_query = query or result["label"]
                    st.session_state.lat = result["lat"]
                    st.session_state.lon = result["lon"]
                    st.session_state.airport_country = result.get("country", "-")
                    st.session_state.study_point_confirmed = True
                    st.session_state.last_airport_query = normalized_query
                    st.session_state.search_message = f"Found: {result['display_name']}"
                    st.session_state.map_click_info = (
                        f"Study point set to {st.session_state.airport_label} "
                        f"({result['lat']:.6f}, {result['lon']:.6f})"
                    )

                    if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
                        _apply_operating_profile()

                    _refresh_study_ready()
                    st.rerun()

                except Exception as e:
                    if "RATE_LIMIT_429" in str(e) or "429" in str(e):
                        st.session_state.search_message = (
                            "Search is temporarily rate-limited by the map service. "
                            "Please wait a moment and try again, or use Advanced coordinates."
                        )
                    else:
                        st.session_state.search_message = f"Search error: {e}"
                    st.rerun()

        if st.session_state.search_message:
            if st.session_state.search_message.startswith("Found:"):
                st.success(st.session_state.search_message)
            else:
                st.warning(st.session_state.search_message)

        with st.expander("Advanced coordinates", expanded=False):
            c1, c2 = st.columns(2)

            with c1:
                new_lat = st.number_input(
                    "Latitude",
                    min_value=-90.0,
                    max_value=90.0,
                    value=float(st.session_state.lat),
                    format="%.6f",
                    disabled=disabled,
                )

            with c2:
                new_lon = st.number_input(
                    "Longitude",
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
                st.session_state.map_click_info = f"Point selected: {new_lat:.6f}, {new_lon:.6f}"
                st.session_state.search_message = ""
                if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
                    _apply_operating_profile()
                _refresh_study_ready()

        st.markdown("### 2. Operating profile")
        st.caption("Define how long the system must operate every day.")

        mode_options = ["Custom hours per day", "24/7", "Dusk to dawn"]
        current_mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
        if current_mode not in mode_options:
            current_mode = "Custom hours per day"

        mode = st.radio(
            "Operating profile",
            mode_options,
            horizontal=True,
            index=mode_options.index(current_mode),
            key="operating_profile_mode_radio",
            disabled=disabled,
        )

        if st.session_state.get("operating_profile_mode") != mode:
            st.session_state.operating_profile_mode = mode
            _apply_operating_profile()

        if mode == "Custom hours per day":
            current_custom = st.session_state.get("required_hours")
            if current_custom is None:
                current_custom = 12.0

            required_custom = st.number_input(
                "Planned daily operating hours",
                min_value=0.1,
                max_value=24.0,
                value=float(current_custom),
                step=0.5,
                help="Total hours per day the lights are expected to operate.",
                key="required_custom_hours_input",
                disabled=disabled,
            )
            st.session_state.required_hours = required_custom
            st.caption("Total hours per day the lights are expected to operate.")

        elif mode == "24/7":
            st.session_state.required_hours = 24.0
            st.info("Applied operating profile: 24.0 hrs/day")

        elif mode == "Dusk to dawn":
            if st.session_state.get("study_point_confirmed", False):
                applied = round(longest_night_hours(st.session_state.lat), 1)
                st.session_state.required_hours = applied
                st.info(
                    f"Applied operating profile: {applied:.1f} hrs/day "
                    f"(based on the longest night at the selected study point)"
                )
            else:
                st.session_state.required_hours = None
                st.warning("Select the study location first to calculate Dusk-to-Dawn operating time.")

        _refresh_study_ready()

        st.markdown("### 3. Manufacturer")

        manufacturer_options = ["S4GA", "Avlite"]
        current_manufacturers = st.session_state.get("selected_manufacturers", ["S4GA", "Avlite"])
        selected_manufacturers = st.multiselect(
            "Manufacturers included in this study",
            manufacturer_options,
            default=current_manufacturers,
            key="selected_manufacturers_multiselect",
            disabled=disabled,
            help="Choose one or more manufacturers. Device list below will be filtered accordingly.",
        )
        st.session_state.selected_manufacturers = selected_manufacturers

        st.markdown("### 4. Select devices")

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
            "Devices included in this study",
            list(device_options.keys()),
            default=default_labels,
            key="selected_devices_multiselect",
            disabled=disabled,
        )

        selected_ids = [device_options[label] for label in selected_labels]
        st.session_state.selected_ids = selected_ids

    with right:
        st.markdown("### Study point")

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
                st.session_state.map_click_info = f"Point selected: {clicked_lat:.6f}, {clicked_lon:.6f}"
                st.session_state.search_message = ""
                if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
                    _apply_operating_profile()
                _refresh_study_ready()
                st.rerun()

        if st.session_state.map_click_info:
            st.success(st.session_state.map_click_info)

        if st.session_state.study_point_confirmed:
            st.caption(
                f"Study point sent to PVGIS: {st.session_state.lat:.6f}, {st.session_state.lon:.6f}"
            )
        else:
            st.caption("Select an airport or click on the map to define the study point.")


    st.markdown("### 5. Configure selected devices")

    per_device_config = {}
    selected_simulation_keys = []

    if not selected_ids:
        st.caption("Select at least one device to configure.")
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
                with st.expander(f"{_device_label(did)} — lamp types", expanded=False):
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button("Select all", key=f"select_all_variants_{did}", disabled=disabled):
                            st.session_state["selected_lamp_types"][did] = variants
                    with c2:
                        if st.button("Clear", key=f"clear_variants_{did}", disabled=disabled):
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
                        st.caption("Each selected lamp type will be simulated separately.")
                    else:
                        st.caption("No lamp type selected for this device family.")
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
                        st.caption(f"Selected lamp type: {lamp_variant}")

                    power = st.number_input(
                        "Power (W)",
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
                            "Solar Engine",
                            compatible,
                            index=compatible.index(engine_key),
                            key=f"engine_{sim_key}",
                            disabled=disabled,
                            format_func=lambda x: f"{SOLAR_ENGINES[x]['short_name']} — {SOLAR_ENGINES[x]['name']}",
                        )

                        eng = SOLAR_ENGINES[engine_key]

                        if eng.get("batt_ext"):
                            battery_mode = st.radio(
                                "Battery mode",
                                ["Std", "Ext"],
                                horizontal=True,
                                index=0 if battery_mode == "Std" else 1,
                                key=f"battery_mode_{sim_key}",
                                disabled=disabled,
                            )
                        else:
                            battery_mode = "Std"
                            st.caption("Battery mode: Std only for this Solar Engine.")
                    else:
                        engine_key = None
                        battery_mode = "Built-in"
                        st.caption("This device uses built-in solar panel and battery.")

                    summary = _engine_summary(did, engine_key, battery_mode)

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Power", f"{float(power):.2f} W")
                    with m2:
                        st.metric("Solar panel", f"{summary['pv']} W")
                    with m3:
                        st.metric("Battery", f"{summary['batt']} Wh")
                    with m4:
                        st.metric("Active source", summary["source_label"])

                    if system_type == "external_engine":
                        st.caption(f"Battery mode selected: {summary['battery_mode']}")

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
