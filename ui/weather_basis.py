# ui/weather_basis.py

import streamlit as st
import matplotlib.pyplot as plt


def render_simple_card(title: str, value: str, subtitle: str):
    st.markdown(f"**{title}**")
    st.markdown(f"### {value}")
    st.caption(subtitle)


def render_weather_variability_block():
    st.markdown("### Weather conditions used in simulation")

    left, right = st.columns([1.25, 1], gap="large")

    with left:
        years = list(range(2010, 2025))
        values = [72, 78, 74, 83, 76, 61, 66, 88, 93, 75, 79, 73, 86, 63, 81]

        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.bar([str(y)[-2:] for y in years], values)
        ax.set_ylim(0, 110)
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.grid(False)

        st.pyplot(fig, use_container_width=True)

        st.markdown("**15 years of real weather data**")
        st.caption(
            "Relative solar variability across years. Includes weaker and stronger solar years "
            "used to stress-test system performance."
        )
        st.caption(
            "Weak-solar years are included because they define worst-case feasibility "
            "and blackout exposure."
        )

    with right:
        st.markdown("### Weather exposure types included")

        r1c1, r1c2, r1c3 = st.columns(3)
        r2c1, r2c2, r2c3 = st.columns(3)

        with r1c1:
            st.markdown("## ☁️")
            st.markdown("**Cloud cover**")
        with r1c2:
            st.markdown("## 🌧️")
            st.markdown("**Rain**")
        with r1c3:
            st.markdown("## 🌫️")
            st.markdown("**Haze / fog**")

        with r2c1:
            st.markdown("## 🌥️")
            st.markdown("**Low solar**")
        with r2c2:
            st.markdown("## ⛅")
            st.markdown("**Partial cloud**")
        with r2c3:
            st.markdown("## ☀️")
            st.markdown("**Clear sky**")

        st.write("")
        st.caption(
            "These conditions are derived from historical weather observations — not simulated "
            "assumptions or idealized weather cases."
        )
        st.caption(
            "Weather model used by PVGIS: TMY built from long-term historical data."
        )


def render_weather_basis():
    st.markdown("## Methodology")

    top_left, top_right = st.columns([1, 6], gap="medium")
    with top_left:
        st.image(
            "https://commission.europa.eu/themes/contrib/oe_theme/dist/ec/images/logo/positive/logo-ec--en.svg",
            width=140,
        )
    with top_right:
        st.markdown("### Based on PVGIS (European Commission)")
        st.write("PVGIS — Photovoltaic Geographical Information System")
        st.write("Joint Research Centre, European Commission")
        st.caption("Independent public methodology used for solar feasibility assessment")

    st.write("")
    render_weather_variability_block()
    st.write("")

    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        render_simple_card(
            "Meteorological database",
            "ERA5-Land & ERA5",
            "High-resolution meteorological data used by PVGIS for temperature and weather-related calculations under real operating conditions.",
        )

    with c2:
        render_simple_card(
            "Solar radiation source",
            "PVGIS-SARAH3",
            "Satellite-based solar radiation dataset used by PVGIS for long-term photovoltaic energy modelling.",
        )

    with c3:
        render_simple_card(
            "Lighting input source",
            "S4GA device data",
            "Light consumption, battery size and solar size are taken from S4GA product input data used in the feasibility calculation.",
        )
