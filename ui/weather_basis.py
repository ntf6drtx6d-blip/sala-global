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
    heights = [38, 64, 50, 80, 58, 92, 54, 102, 72, 44, 86, 52, 76, 98, 46]
    years = list(range(2010, 2025))

    bars_html = ""
    for year, h in zip(years, heights):
        bars_html += f"""<div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
<div style="width:14px;height:{h}px;background:#bcd3ff;border-radius:6px 6px 0 0;"></div>
<div style="font-size:0.72rem;color:#667085;line-height:1;">{str(year)[-2:]}</div>
</div>"""

    weather_grid_html = """<div style="min-width:340px;flex:1;">
<div style="font-size:0.98rem;color:#344054;font-weight:700;line-height:1.45;margin-bottom:12px;">
Weather exposure types included
</div>

<div style="
display:grid;
grid-template-columns:repeat(3, minmax(84px, 1fr));
gap:10px;
margin-bottom:14px;">

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:10px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.25rem;margin-bottom:4px;">☁️</div>
<div style="font-size:0.78rem;color:#475467;font-weight:700;">Cloud cover</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:10px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.25rem;margin-bottom:4px;">🌧️</div>
<div style="font-size:0.78rem;color:#475467;font-weight:700;">Rain</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:10px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.25rem;margin-bottom:4px;">🌫️</div>
<div style="font-size:0.78rem;color:#475467;font-weight:700;">Haze / fog</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:10px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.25rem;margin-bottom:4px;">🌥️</div>
<div style="font-size:0.78rem;color:#475467;font-weight:700;">Low solar</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:10px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.25rem;margin-bottom:4px;">⛅</div>
<div style="font-size:0.78rem;color:#475467;font-weight:700;">Partial cloud</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:10px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.25rem;margin-bottom:4px;">☀️</div>
<div style="font-size:0.78rem;color:#475467;font-weight:700;">Clear sky</div>
</div>
</div>

<div style="font-size:0.92rem;color:#667085;line-height:1.55;">
The feasibility check accounts for cloud cover, rain, haze and weak-solar periods observed over a long historical window — not ideal or average-only conditions.
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

<div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:12px;">
Weather conditions used in simulation
</div>

<div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;">

<div style="min-width:320px;flex:1;">
<div style="display:flex;align-items:flex-end;gap:6px;height:132px;margin-bottom:8px;">
{bars_html}
</div>
<div style="font-size:0.92rem;color:#475467;font-weight:700;">
15 years of real weather data
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
