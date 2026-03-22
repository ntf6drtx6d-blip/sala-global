# ui/weather_basis.py

import streamlit as st


def render_card(title: str, value: str, subtitle: str):
    html = """
    <div style="
        border:1px solid #e6eaf0;
        border-radius:16px;
        padding:18px 20px;
        background:#ffffff;
        min-height:150px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">
        <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
        <div style="font-size:1.65rem;font-weight:900;color:#1f2937;line-height:1.1;margin-bottom:12px;">{value}</div>
        <div style="font-size:0.92rem;color:#667085;line-height:1.45;">{subtitle}</div>
    </div>
    """.format(title=title, value=value, subtitle=subtitle)
    st.markdown(html, unsafe_allow_html=True)


import streamlit as st
import textwrap


def render_card(title: str, value: str, subtitle: str):
    html = textwrap.dedent("""
    <div style="
        border:1px solid #e6eaf0;
        border-radius:16px;
        padding:18px 20px;
        background:#ffffff;
        min-height:150px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">
        <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
        <div style="font-size:1.65rem;font-weight:900;color:#1f2937;line-height:1.1;margin-bottom:12px;">{value}</div>
        <div style="font-size:0.92rem;color:#667085;line-height:1.45;">{subtitle}</div>
    </div>
    """).format(title=title, value=value, subtitle=subtitle)

    st.markdown(html, unsafe_allow_html=True)


def render_weather_basis():
    st.markdown("## Methodology")

    header_html = textwrap.dedent("""
    <div style="
        border:1px solid #d6e0ef;
        border-radius:18px;
        padding:18px 20px;
        background:#f7faff;
        margin-bottom:18px;">
        <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
            <img src="https://commission.europa.eu/themes/contrib/oe_theme/dist/ec/images/logo/positive/logo-ec--en.svg"
                 style="height:44px;">
            <div>
                <div style="font-size:1.05rem;font-weight:900;color:#12355b;margin-bottom:4px;">
                    Based on PVGIS (European Commission)
                </div>
                <div style="font-size:0.95rem;color:#344054;line-height:1.55;">
                    PVGIS — Photovoltaic Geographical Information System<br>
                    Joint Research Centre, European Commission
                </div>
            </div>
        </div>
    </div>
    """)
    st.markdown(header_html, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        render_card(
            "Solar radiation database",
            "PVGIS-SARAH3",
            "Satellite-based solar radiation dataset used by PVGIS for long-term energy modelling.",
        )

    with c2:
        render_card(
            "Meteorological database",
            "ERA5-Land & ERA5",
            "Meteorological base used by PVGIS for temperature and weather-related calculations.",
        )

    with c3:
        render_card(
            "Lighting input source",
            "S4GA device data",
            "Light consumption, battery size and solar size are taken from S4GA product input data.",
        )

    st.markdown("###")

    d1, d2, d3 = st.columns(3)

    with d1:
        render_card(
            "Historical data window",
            "15 years",
            "Long-term historical basis for annual simulation.",
        )

    with d2:
        render_card(
            "Weather model",
            "TMY",
            "Typical Meteorological Year used for feasibility assessment.",
        )

    with d3:
        render_card(
            "Coverage",
            "Jan–Dec",
            "Full annual cycle, including weak solar periods.",
        )
