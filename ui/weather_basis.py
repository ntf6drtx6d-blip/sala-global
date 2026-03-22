# ui/weather_basis.py

import streamlit as st


def render_card(title: str, value: str, subtitle: str):
    html = f"""<div style="
border:1px solid #e6eaf0;
border-radius:16px;
padding:18px 20px;
background:#ffffff;
min-height:150px;
box-shadow:0 2px 10px rgba(16,24,40,0.04);">
<div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
<div style="font-size:1.65rem;font-weight:900;color:#1f2937;line-height:1.1;margin-bottom:12px;">{value}</div>
<div style="font-size:0.92rem;color:#667085;line-height:1.5;">{subtitle}</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_weather_variability_block():
    heights = [72, 78, 74, 83, 76, 61, 66, 88, 93, 75, 79, 73, 86, 63, 81]
    years = list(range(2010, 2025))
    weak_years = {61, 63, 66}

    bars_html = ""
    for year, h in zip(years, heights):
        color = "#9fb6e9" if h in weak_years else "#bcd3ff"
        bars_html += f"""<div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
<div style="width:18px;height:{h}px;background:{color};border-radius:7px 7px 0 0;"></div>
<div style="font-size:0.74rem;color:#667085;line-height:1;">{str(year)[-2:]}</div>
</div>"""

    weather_grid_html = """<div style="min-width:340px;flex:1;">
<div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:8px;">
Weather exposure types included
</div>

<div style="
display:grid;
grid-template-columns:repeat(3, minmax(92px, 1fr));
gap:10px;
margin-bottom:14px;">

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">☁️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">Cloud cover</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">🌧️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">Rain</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">🌫️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">Haze / fog</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">🌥️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">Low solar</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">⛅</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">Partial cloud</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">☀️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">Clear sky</div>
</div>
</div>

<div style="font-size:0.92rem;color:#667085;line-height:1.55;">
These conditions are derived from historical weather observations — not simulated assumptions or idealized weather cases.
</div>

<div style="font-size:0.85rem;color:#667085;line-height:1.5;margin-top:10px;">
Weather model used by PVGIS: TMY built from long-term historical data
</div>
</div>"""

    html = f"""<div style="
border:1px solid #e6eaf0;
border-radius:18px;
padding:20px 22px;
background:#ffffff;
box-shadow:0 2px 10px rgba(16,24,40,0.04);
margin-bottom:18px;">

<div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap;margin-bottom:10px;">

<div style="min-width:360px;flex:1;">
<div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:8px;">
Weather conditions used in simulation
</div>
</div>

<div style="min-width:340px;flex:1;">
<div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:8px;">
Weather exposure types included
</div>
</div>

</div>

<div style="display:flex;gap:24px;align-items:stretch;flex-wrap:wrap;">

<div style="
min-width:360px;
flex:1;
display:flex;
flex-direction:column;
justify-content:space-between;
height:100%;
">

<div style="
display:flex;
align-items:flex-end;
gap:8px;
flex:1;
min-height:260px;
margin-bottom:12px;
padding:12px 10px 6px 10px;
background:#f8fafc;
border-radius:12px;
border:1px solid #e6eaf0;
">
{bars_html}
</div>

<div style="font-size:0.94rem;color:#475467;font-weight:700;">
15 years of real weather data
</div>

<div style="font-size:0.84rem;color:#667085;line-height:1.45;margin-top:6px;">
Relative solar variability across years. Includes weaker and stronger solar years used to stress-test system performance.
</div>

<div style="font-size:0.84rem;color:#667085;line-height:1.45;margin-top:6px;">
Weak-solar years are included because they define worst-case feasibility and blackout exposure.
</div>
</div>

{weather_grid_html}

</div>
</div>"""

    st.markdown(html, unsafe_allow_html=True)


def render_weather_basis():
    st.markdown("## Methodology")

    header_html = """<div style="
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
</div>"""
    st.markdown(header_html, unsafe_allow_html=True)

    render_weather_variability_block()

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
