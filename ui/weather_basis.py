# ui/weather_basis.py

import streamlit as st
from core.i18n import t

def _manufacturer_items():
    lang = st.session_state.get("language", "en")
    results = st.session_state.get("results", {}) or {}
    has_avlite = any(str((row or {}).get("system_type", "")).lower() == "avlite_fixture" for row in results.values())
    has_s4ga = any(str((row or {}).get("system_type", "")).lower() != "avlite_fixture" for row in results.values())
    items = []
    if has_s4ga:
        items.append((t("ui.device_source_info", lang), "S4GA (Poland)", t("ui.status", lang), t("ui.verified_by_sala", lang)))
    if has_avlite:
        items.append((t("ui.device_source_info", lang), "Avlite (Australia)", t("ui.status", lang), t("ui.estimated_by_sala", lang)))
    return items


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
    lang = st.session_state.get("language", "en")
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

    weather_grid_html = f"""<div style="min-width:340px;flex:1;">
<div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:8px;">
{t("ui.weather_conditions_used", lang)}
</div>

<div style="
display:grid;
grid-template-columns:repeat(3, minmax(92px, 1fr));
gap:10px;
margin-bottom:14px;">

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">☁️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">{t("ui.cloud_cover", lang)}</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">🌧️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">{t("ui.rain", lang)}</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">🌫️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">{t("ui.haze_fog", lang)}</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">🌥️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">{t("ui.low_solar", lang)}</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">⛅</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">{t("ui.partial_cloud", lang)}</div>
</div>

<div style="border:1px solid #e6eaf0;border-radius:12px;padding:12px 8px;background:#f8fafc;text-align:center;">
<div style="font-size:1.3rem;margin-bottom:6px;">☀️</div>
<div style="font-size:0.8rem;color:#475467;font-weight:700;">{t("ui.clear_sky", lang)}</div>
</div>
</div>

<div style="font-size:0.92rem;color:#667085;line-height:1.55;">
{t("ui.weather_observation_note", lang)}
</div>

<div style="font-size:0.85rem;color:#667085;line-height:1.5;margin-top:10px;">
{t("ui.weather_model_note", lang)}
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
{t("ui.weather_conditions_used", lang)}
</div>
</div>

<div style="min-width:340px;flex:1;">
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
{t("ui.real_weather_data", lang)}
</div>

<div style="font-size:0.84rem;color:#667085;line-height:1.45;margin-top:6px;">
{t("ui.solar_variability_note", lang)}
</div>

<div style="font-size:0.84rem;color:#667085;line-height:1.45;margin-top:6px;">
{t("ui.weak_solar_years_note", lang)}
</div>
</div>

{weather_grid_html}

</div>
</div>"""

    st.markdown(html, unsafe_allow_html=True)


def render_weather_basis():
    lang = st.session_state.get("language", "en")
    st.markdown(f"## {t('ui.methodology', lang)}")

    header_html = f"""<div style="
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
{t("ui.based_on_pvgis", lang)}
</div>
<div style="font-size:0.95rem;color:#344054;line-height:1.55;">
{t("ui.pvgis_full_name", lang)}<br>
{t("ui.pvgis_jrc_line", lang)}
</div>
<div style="font-size:0.9rem;color:#667085;line-height:1.5;margin-top:6px;">
{t("ui.pvgis_independent_methodology", lang)}
</div>
</div>
</div>
</div>"""
    st.markdown(header_html, unsafe_allow_html=True)

    render_weather_variability_block()

    c1, c2, c3 = st.columns(3)

    with c1:
        render_card(
            t("report.meteorological_database", lang),
            "ERA5",
            t("report.dataset_copy_meteo", lang),
        )

    with c2:
        render_card(
            t("report.solar_kicker", lang),
            "PVGIS-SARAH3",
            t("report.dataset_copy_primary", lang),
        )

    with c3:
        items = _manufacturer_items()
        if items:
            cards_html = "".join(
                f"""
                <div style="border:1px solid #d6e0ef;border-radius:12px;padding:12px 14px;background:#f8fbff;margin-bottom:10px;">
                    <div style="font-size:0.82rem;color:#667085;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;">{label1}</div>
                    <div style="font-size:1rem;color:#12355b;font-weight:900;line-height:1.25;margin:4px 0 8px 0;">{value1}</div>
                    <div style="font-size:0.82rem;color:#667085;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;">{label2}</div>
                    <div style="font-size:0.96rem;color:#12355b;font-weight:800;line-height:1.25;margin-top:4px;">{value2}</div>
                </div>
                """
                for label1, value1, label2, value2 in items
            )
            st.markdown(f"### {t('report.methodology.lighting_input_source', lang)}")
            st.markdown(cards_html, unsafe_allow_html=True)
