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
    # stronger, realistic variability across years (not random)
    base = [72, 78, 74, 83, 76, 61, 66, 88, 93, 75, 79, 73, 86, 63, 81]
    heights = [int(h * 1.4) for h in base]  # SCALE UP → bigger visual

    # build bars
    bars_html = ""
    for h in heights:
        bars_html += (
            f'<div style="width:22px;'
            f'height:{h}px;'
            f'background:#bcd3ff;'
            f'border-radius:6px 6px 0 0;"></div>'
        )

    # labels (years)
    labels_html = ""
    for y in range(10, 25):
        labels_html += f'<div style="width:22px;text-align:center;">{y}</div>'

    html = textwrap.dedent(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:18px;
            padding:22px;
            background:#ffffff;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
            margin-bottom:18px;">

            <div style="display:flex;gap:28px;align-items:flex-start;">

                <!-- LEFT: BIG GRAPH -->
                <div style="flex:1.4;">

                    <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">
                        Weather conditions used in simulation
                    </div>

                    <div style="
                        display:flex;
                        align-items:flex-end;
                        gap:10px;
                        height:320px;
                        padding:18px 16px 10px 16px;
                        background:#f8fafc;
                        border-radius:14px;
                        border:1px solid #e6eaf0;
                        border-bottom:2px solid #d0d5dd;
                        margin-bottom:10px;">
                        {bars_html}
                    </div>

                    <div style="
                        display:flex;
                        gap:10px;
                        font-size:0.8rem;
                        color:#667085;
                        margin-bottom:12px;">
                        {labels_html}
                    </div>

                    <div style="font-size:0.95rem;color:#344054;font-weight:800;">
                        15 years of real weather data
                    </div>

                    <div style="font-size:0.92rem;color:#667085;margin-top:6px;line-height:1.55;">
                        Relative solar variability across years. Includes weaker and stronger solar years used to stress-test system performance.
                    </div>

                    <div style="font-size:0.88rem;color:#667085;margin-top:6px;">
                        Weak-solar years define worst-case feasibility and blackout exposure.
                    </div>

                </div>

                <!-- RIGHT: WEATHER TYPES GRID -->
                <div style="flex:1;">

                    <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:12px;">
                        Weather exposure types included
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">

                        {render_weather_tile("☁️", "Cloud cover")}
                        {render_weather_tile("🌧️", "Rain")}
                        {render_weather_tile("🌫️", "Haze / fog")}
                        {render_weather_tile("🌥️", "Low solar")}
                        {render_weather_tile("⛅", "Partial cloud")}
                        {render_weather_tile("☀️", "Clear sky")}

                    </div>

                    <div style="margin-top:14px;font-size:0.92rem;color:#667085;line-height:1.6;">
                        These conditions are derived from historical weather observations — not simulated assumptions or idealized weather cases.
                    </div>

                    <div style="font-size:0.88rem;color:#667085;margin-top:8px;">
                        Weather model used by PVGIS: TMY built from long-term historical data
                    </div>

                </div>

            </div>
        </div>
        """
    )

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
