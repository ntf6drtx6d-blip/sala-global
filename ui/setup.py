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

    # main marker
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

    # halo
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


# ---------------- MAIN UI ----------------

def render_setup():
    st.markdown("## Study setup")

    left, right = st.columns([1, 1])

    # ---------------- LEFT ----------------
    with left:

        # Airport input
        airport_query = st.text_input(
            "Airport name",
            value=st.session_state.airport_label,
            placeholder="e.g. Madrid Barajas Airport"
        )

        # Find airport button
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

        # Hours input (IMPORTANT FIX)
        st.session_state.required_hours = st.number_input(
            "Planned daily operating hours",
            min_value=0.0,
            max_value=24.0,
            value=float(st.session_state.required_hours),
            step=0.5,
            help="Total hours per day the lights are expected to operate."
        )

        st.caption("Total hours per day the lights are expected to operate.")

        # Messages
        if st.session_state.search_message:
            if st.session_state.search_message.startswith("Found:"):
                st.success(st.session_state.search_message)
            else:
                st.warning(st.session_state.search_message)

        # Advanced coordinates
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

        # click on map
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

    device_options = {
        f"{k}. {v['code']} — {v['name']}": k
        for k, v in DEVICES.items()
    }

    selected_labels = st.multiselect(
        "Devices included in this study",
        list(device_options.keys()),
        default=list(device_options.keys())[:2]
    )

    st.session_state.selected_ids = [
        device_options[label] for label in selected_labels
    ]

    # ---------------- CONFIGURATION ----------------

    st.markdown("### Configure selected devices")

    per_device_config = {}

    for did in st.session_state.selected_ids:
        dspec = DEVICES[did]

        with st.expander(f"{dspec['code']} — {dspec['name']}", expanded=False):

            # power
            power = st.number_input(
                f"Power (W)",
                min_value=0.01,
                value=float(dspec["default_power"]),
                step=0.01,
                key=f"power_{did}"
            )

            engine_key = None
            battery_mode = "Std"

            if dspec["system_type"] == "external_engine":
                engine_key = st.selectbox(
                    "Solar Engine",
                    dspec["compatible_engines"],
                    index=dspec["compatible_engines"].index(dspec["default_engine"]),
                    key=f"engine_{did}"
                )

                eng = SOLAR_ENGINES[engine_key]

                if eng.get("batt_ext"):
                    battery_mode = st.radio(
                        "Battery mode",
                        ["Std", "Ext"],
                        horizontal=True,
                        key=f"battery_mode_{did}"
                    )

            per_device_config[did] = {
                "power": float(power),
                "engine_key": engine_key,
                "battery_mode": battery_mode,
            }

    st.session_state.per_device_config = per_device_config
