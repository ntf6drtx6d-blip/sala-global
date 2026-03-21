# ui/setup.py
# ACTION: REPLACE ENTIRE FILE

import streamlit as st
import folium
import requests
from streamlit_folium import st_folium

from core.devices import DEVICES, SOLAR_ENGINES


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


# ---------------- HELPERS ----------------

def _device_label(device_id):
    d = DEVICES[device_id]
    return f"{d['code']} — {d['name']}"


def _engine_summary(device_id, engine_key, battery_mode):
    dspec = DEVICES[device_id]

    if dspec["system_type"] == "builtin":
        pv = dspec.get("pv", 0)
        batt = dspec.get("batt", 0)
        return {
            "source_label": "Built-in solar system",
            "pv": pv,
            "batt": batt,
            "battery_mode": "Built-in",
        }

    eng = SOLAR_ENGINES[engine_key]
    pv = eng["pv"]

    if battery_mode == "Ext" and eng.get("batt_ext"):
        batt = eng["batt_ext"]
    else:
        batt = eng["batt"]

    return {
        "source_label": eng["short_name"],
        "pv": pv,
        "batt": batt,
        "battery_mode": battery_mode,
    }


def _default_multiselect_labels():
    labels = []
    for did in st.session_state.get("selected_ids", []):
        if did in DEVICES:
            labels.append(_device_label(did))
    return labels


# ---------------- MAIN UI ----------------

def render_setup():
    st.markdown("## Study setup")

    left, right = st.columns([1, 1])

    # ---------------- LEFT ----------------
    with left:
        airport_query = st.text_input(
            "Airport name",
            value=st.session_state.airport_label,
            placeholder="e.g. Madrid Barajas Airport",
        )

        if st.button("Find airport"):
            try:
                result = geocode_airport(airport_query)
                if result:
                    st.session_state.lat = result["lat"]
                    st.session_state.lon = result["lon"]
                    st.session_state.airport_label = airport_query.strip() or result["display_name"]
                    st.session_state.search_message = f"Found: {result['display_name']}"
                    st.rerun()
                else:
                    st.session_state.search_message = "Airport not found."
                    st.rerun()
            except Exception as e:
                st.session_state.search_message = f"Search error: {e}"
                st.rerun()

        st.session_state.required_hours = st.number_input(
            "Planned daily operating hours",
            min_value=0.0,
            max_value=24.0,
            value=float(st.session_state.required_hours),
            step=0.5,
            help="Total hours per day the lights are expected to operate.",
        )

        st.caption("Total hours per day the lights are expected to operate.")

        if st.session_state.search_message:
            if st.session_state.search_message.startswith("Found:"):
                st.success(st.session_state.search_message)
            else:
                st.warning(st.session_state.search_message)

        with st.expander("Advanced coordinates", expanded=False):
            st.session_state.lat = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=float(st.session_state.lat),
                format="%.6f",
            )
            st.session_state.lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=float(st.session_state.lon),
                format="%.6f",
            )

    # ---------------- RIGHT ----------------
    with right:
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

            if abs(clicked_lat - st.session_state.lat) > 1e-7 or abs(clicked_lon - st.session_state.lon) > 1e-7:
                st.session_state.lat = clicked_lat
                st.session_state.lon = clicked_lon
                st.session_state.map_click_info = f"Point selected: {clicked_lat:.6f}, {clicked_lon:.6f}"
                st.rerun()

        if st.session_state.map_click_info:
            st.success(st.session_state.map_click_info)

        st.caption(
            f"Study point sent to PVGIS: {st.session_state.lat:.6f}, {st.session_state.lon:.6f}"
        )

    # ---------------- DEVICES ----------------
    st.markdown("### Select devices")

    device_options = {_device_label(k): k for k in DEVICES.keys()}

    selected_labels = st.multiselect(
        "Devices included in this study",
        list(device_options.keys()),
        default=_default_multiselect_labels() or list(device_options.keys())[:2],
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
        return

    for did in selected_ids:
        dspec = DEVICES[did]
        system_type = dspec["system_type"]

        with st.expander(_device_label(did), expanded=False):
            # existing saved values if present
            saved_cfg = st.session_state.get("per_device_config", {}).get(did, {})

            default_power = float(saved_cfg.get("power", dspec["default_power"]))
            engine_key = saved_cfg.get("engine_key", dspec.get("default_engine"))
            battery_mode = saved_cfg.get("battery_mode", "Std")

            # Power
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
                st.caption(
                    f"Battery mode selected: {summary['battery_mode']}"
                )

            per_device_config[did] = {
                "power": float(power),
                "engine_key": engine_key,
                "battery_mode": battery_mode if battery_mode in ["Std", "Ext"] else "Std",
            }

    st.session_state.per_device_config = per_device_config
