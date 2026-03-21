# ui/setup.py
# ACTION: REPLACE ENTIRE FILE

import math
import streamlit as st
import folium
import requests
from streamlit_folium import st_folium

from core.devices import DEVICES, SOLAR_ENGINES


# ---------------- INITIAL LOCAL STATE ----------------

def _init_setup_defaults():
    if "setup_initialized" not in st.session_state:
        st.session_state.setup_initialized = True

        # clean defaults
        st.session_state.airport_label = ""
        st.session_state.airport_query = ""
        st.session_state.selected_ids = []
        st.session_state.per_device_config = {}

        # keep coordinates hidden in advanced, but default hours = 12
        if "required_hours" not in st.session_state:
            st.session_state.required_hours = 12.0
        else:
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

    # final flag used by next modules
    st.session_state.study_ready = bool(
        st.session_state.get("study_point_confirmed", False)
        and len(st.session_state.get("selected_ids", [])) > 0
    )


# ---------------- GEO ----------------

def geocode_airport(query):
    if not query or not query.strip():
        return None

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "jsonv2", "limit": 1}
    headers = {"User-Agent": "SALA-Simulator/1.0"}

    resp = requests.get(url, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        return None

    top = data[0]
    return {
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name", query),
    }


# ---------------- MAP ----------------

def create_map(lat, lon, label):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=14,
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


# ---------------- ASTRONOMY / DUSK-TO-DAWN ----------------

def _day_length_hours(lat_deg: float, decl_deg: float) -> float:
    """
    Approximate daylight hours for a given latitude and solar declination.
    Includes simple sunrise/sunset refraction correction via zenith 90.833°.
    """
    lat = math.radians(lat_deg)
    decl = math.radians(decl_deg)
    zenith = math.radians(90.833)

    cos_h = (math.cos(zenith) - math.sin(lat) * math.sin(decl)) / (math.cos(lat) * math.cos(decl))

    if cos_h <= -1:
        return 24.0
    if cos_h >= 1:
        return 0.0

    hour_angle = math.acos(cos_h)
    return 24.0 * hour_angle / math.pi


def longest_night_hours(lat_deg: float) -> float:
    """
    Approximate longest night at this latitude using winter-solstice declination.
    Good enough for UX + feasibility profile mode.
    """
    abs_lat = max(min(float(lat_deg), 89.0), -89.0)

    # winter solstice depends on hemisphere
    decl = -23.44 if abs_lat >= 0 else 23.44
    day = _day_length_hours(abs_lat, decl)
    night = 24.0 - day

    return max(0.0, min(24.0, night))


# ---------------- HELPERS ----------------

def _device_label(device_id):
    d = DEVICES[device_id]
    return f"{d['code']} — {d['name']}"


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


def _apply_operating_profile():
    mode = st.session_state.get("operating_profile_mode", "Custom hours per day")

    if mode == "24/7":
        st.session_state.required_hours = 24.0
    elif mode == "Dusk to dawn":
        st.session_state.required_hours = round(longest_night_hours(st.session_state.lat), 1)
    # for Custom, required_hours already comes from user input


# ---------------- MAIN UI ----------------

def render_setup():
    _init_setup_defaults()

    st.markdown("## Study setup")

    left, right = st.columns([1, 1])

    # ---------------- LEFT ----------------
    with left:
        st.markdown("### Location")

        airport_col, button_col = st.columns([3, 1])

        with airport_col:
            airport_query = st.text_input(
                "Airport name",
                value=st.session_state.get("airport_query", ""),
                placeholder="e.g. Madrid Barajas Airport",
                key="airport_query_input"
            )

        with button_col:
            st.write("")
            st.write("")
            if st.button("Find airport", use_container_width=True):
                try:
                    result = geocode_airport(airport_query)
                    if result:
                        st.session_state.lat = result["lat"]
                        st.session_state.lon = result["lon"]
                        st.session_state.airport_label = airport_query.strip() or result["display_name"]
                        st.session_state.airport_query = airport_query.strip() or result["display_name"]
                        st.session_state.search_message = f"Found: {result['display_name']}"
                        st.session_state.study_point_confirmed = True
                        _apply_operating_profile()
                        st.rerun()
                    else:
                        st.session_state.search_message = "Airport not found."
                        st.rerun()
                except Exception as e:
                    st.session_state.search_message = f"Search error: {e}"
                    st.rerun()

        if st.session_state.search_message:
            if st.session_state.search_message.startswith("Found:"):
                st.success(st.session_state.search_message)
            else:
                st.warning(st.session_state.search_message)

        st.markdown("### Operating profile")

        mode = st.radio(
            "Operating profile",
            ["Custom hours per day", "24/7", "Dusk to dawn"],
            horizontal=True,
            index=["Custom hours per day", "24/7", "Dusk to dawn"].index(
                st.session_state.get("operating_profile_mode", "Custom hours per day")
            ),
            key="operating_profile_mode_radio"
        )
        st.session_state.operating_profile_mode = mode

        if mode == "Custom hours per day":
            st.session_state.required_hours = st.number_input(
                "Planned daily operating hours",
                min_value=0.0,
                max_value=24.0,
                value=float(st.session_state.get("required_hours", 12.0)),
                step=0.5,
                help="Total hours per day the lights are expected to operate."
            )
            st.caption("Total hours per day the lights are expected to operate.")

        elif mode == "24/7":
            st.session_state.required_hours = 24.0
            st.info("Applied operating profile: 24.0 hrs/day")

        elif mode == "Dusk to dawn":
            applied = round(longest_night_hours(st.session_state.lat), 1)
            st.session_state.required_hours = applied
            st.info(
                f"Applied operating profile: {applied:.1f} hrs/day "
                f"(based on the longest night at the selected study point)"
            )

        with st.expander("Advanced coordinates", expanded=False):
            new_lat = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=float(st.session_state.lat),
                format="%.6f",
            )
            new_lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=float(st.session_state.lon),
                format="%.6f",
            )

            coords_changed = (
                abs(new_lat - st.session_state.lat) > 1e-9
                or abs(new_lon - st.session_state.lon) > 1e-9
            )

            st.session_state.lat = new_lat
            st.session_state.lon = new_lon

            if coords_changed:
                st.session_state.study_point_confirmed = True
                if st.session_state.operating_profile_mode == "Dusk to dawn":
                    _apply_operating_profile()

    # ---------------- RIGHT ----------------
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
            height=420,
            returned_objects=["last_clicked"],
            key="study_map_modular",
        )

        clicked = map_data.get("last_clicked") if isinstance(map_data, dict) else None
        if clicked:
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
                if st.session_state.operating_profile_mode == "Dusk to dawn":
                    _apply_operating_profile()
                st.rerun()

        if st.session_state.map_click_info:
            st.success(st.session_state.map_click_info)

        if st.session_state.study_point_confirmed:
            st.caption(
                f"Study point sent to PVGIS: {st.session_state.lat:.6f}, {st.session_state.lon:.6f}"
            )
        else:
            st.caption("Select an airport or click on the map to define the study point.")

    # ---------------- DEVICES ----------------
    st.markdown("### Select devices")

    device_options = {_device_label(k): k for k in DEVICES.keys()}

    selected_labels = st.multiselect(
        "Devices included in this study",
        list(device_options.keys()),
        default=_default_multiselect_labels(),
        key="selected_devices_multiselect",
    )

    selected_ids = [device_options[label] for label in selected_labels]
    st.session_state.selected_ids = selected_ids

    # ---------------- CONFIGURATION ----------------
    st.markdown("### Configure selected devices")

    per_device_config = {}

    if not selected_ids:
        st.info("Select at least one device to configure.")
        st.session_state.per_device_config = {}
        st.session_state.study_ready = False
        return

    for did in selected_ids:
        dspec = DEVICES[did]
        system_type = dspec["system_type"]

        with st.expander(_device_label(did), expanded=False):
            saved_cfg = st.session_state.get("per_device_config", {}).get(did, {})

            default_power = float(saved_cfg.get("power", dspec["default_power"]))
            engine_key = saved_cfg.get("engine_key", dspec.get("default_engine"))
            battery_mode = saved_cfg.get("battery_mode", "Std")

            power = st.number_input(
                "Power (W)",
                min_value=0.01,
                value=float(default_power),
                step=0.01,
                key=f"power_{did}",
            )

            if system_type == "external_engine":
                compatible = dspec["compatible_engines"]
                if engine_key not in compatible:
                    engine_key = dspec["default_engine"]

                engine_key = st.selectbox(
                    "Solar Engine",
                    compatible,
                    index=compatible.index(engine_key),
                    key=f"engine_{did}",
                    format_func=lambda x: f"{SOLAR_ENGINES[x]['short_name']} — {SOLAR_ENGINES[x]['name']}",
                )

                eng = SOLAR_ENGINES[engine_key]

                if eng.get("batt_ext"):
                    battery_mode = st.radio(
                        "Battery mode",
                        ["Std", "Ext"],
                        horizontal=True,
                        index=0 if battery_mode == "Std" else 1,
                        key=f"battery_mode_{did}",
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

            per_device_config[did] = {
                "power": float(power),
                "engine_key": engine_key,
                "battery_mode": battery_mode if battery_mode in ["Std", "Ext"] else "Std",
            }

    st.session_state.per_device_config = per_device_config

    # final ready flag
    st.session_state.study_ready = bool(
        st.session_state.get("study_point_confirmed", False)
        and len(st.session_state.get("selected_ids", [])) > 0
    )

    if not st.session_state.study_ready:
        st.warning("To start the study, select an airport or study point and at least one device.")
