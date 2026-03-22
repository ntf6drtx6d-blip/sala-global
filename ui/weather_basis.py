# ui/weather_basis.py

import textwrap
import streamlit as st


def render_card(title: str, value: str, subtitle: str):
    html = textwrap.dedent(
        """
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            min-height:150px;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);">
            <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div style="font-size:1.65rem;font-weight:900;color:#1f2937;line-height:1.1;margin-bottom:12px;">{value}</div>
            <div style="font-size:0.92rem;color:#667085;line-height:1.5;">{subtitle}</div>
        </div>
        """
    ).format(title=title, value=value, subtitle=subtitle)

    st.markdown(html, unsafe_allow_html=True)


def render_weather_variability_block():
    bars_html = "".join(
        [
            '<div style="width:14px;height:38px;background:#dbe7ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:64px;background:#c4d7ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:50px;background:#d1e0ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:80px;background:#a9c5ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:58px;background:#bdd3ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:92px;background:#8fb5ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:54px;background:#c8dbff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:102px;background:#7ca9ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:72px;background:#acc8ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:44px;background:#d7e4ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:86px;background:#98bbff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:52px;background:#cddfff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:76px;background:#a5c3ff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:98px;background:#86afff;border-radius:6px 6px 0 0;"></div>',
            '<div style="width:14px;height:46px;background:#d3e2ff;border-radius:6px 6px 0 0;"></div>',
        ]
    )

    html = f"""
    <div style="
        border:1px solid #e6eaf0;
        border-radius:18px;
        padding:20px 22px;
        background:#ffffff;
        min-height:210px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">

        <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">
            Weather conditions used in simulation
        </div>

        <div style="display:flex;gap:22px;align-items:center;flex-wrap:wrap;">
            <div style="min-width:260px;flex:1;">
                <div style="display:flex;align-items:flex-end;gap:6px;height:112px;margin-bottom:8px;">
                    {bars_html}
                </div>
                <div style="font-size:0.9rem;color:#475467;font-weight:700;">
                    15 years of real weather data
                </div>
            </div>

            <div style="min-width:280px;flex:1;">
                <div style="font-size:1.5rem;line-height:1;margin-bottom:12px;">
                    ☀️ ⛅ ☁️ 🌧️ 🌫️ 🌬️
                </div>
                <div style="font-size:0.98rem;color:#344054;font-weight:700;line-height:1.45;margin-bottom:8px;">
                    Simulation is based on real weather variability — not ideal or average-only conditions.
                </div>
                <div style="font-size:0.92rem;color:#667085;line-height:1.55;">
                    The model includes cloudy, rainy and weak-solar periods observed over a long historical window,
                    so the feasibility check reflects realistic operating exposure rather than best-case weather.
                </div>
                <div style="font-size:0.85rem;color:#667085;line-height:1.5;margin-top:10px;">
                    Weather model used by PVGIS: TMY built from long-term historical data
                </div>
            </div>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_weather_basis():
    st.markdown("## Methodology")

    header_html = textwrap.dedent(
        """
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
                    <div style="font-size:0.9rem;color:#667085;line-height:1.5;margin-top:6px;">
                        Independent public methodology used for solar feasibility assessment
                    </div>
                </div>
            </div>
        </div>
        """
    )
    st.markdown(header_html, unsafe_allow_html=True)

    render_weather_variability_block()

    st.markdown("###")

    c1, c2, c3 = st.columns(3)

    with c1:
        render_card(
            "Meteorological database",
            "ERA5-Land & ERA5",
            "High-resolution meteorological data used by PVGIS for temperature and weather-related calculations under real operating conditions.",
        )

    with c2:
        render_card(
            "Solar radiation source",
            "PVGIS-SARAH3",
            "Satellite-based solar radiation dataset used by PVGIS for long-term photovoltaic energy modelling.",
        )

    with c3:
        render_card(
            "Lighting input source",
            "S4GA device data",
            "Light consumption, battery size and solar size are taken from S4GA product input data used in the feasibility calculation.",
        )
