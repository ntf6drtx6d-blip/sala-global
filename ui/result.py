# ui/result.py

import math
import textwrap

import folium
import streamlit as st

from pvgis_client import pvcalc_monthly_wh_per_day
from core.i18n import month_label, t
from ui.map_embed import render_folium_map
from ui.result_helpers import (
    annual_empty_battery_stats,
    count_device_statuses,
    operating_mode_name,
    operating_window_example,
    overall_conclusion_text,
    overall_interpretation_text,
    overall_state,
    result_device_display_name,
)
from ui.result_devices import render_device_capability_cards

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    bg: str = "#ffffff",
    border: str = "#e6eaf0",
    color: str = "#1f2937",
    min_height: int = 220,
):
    html = textwrap.dedent(
        """
        <div style="
            border:1px solid {border};
            border-radius:16px;
            padding:18px 20px;
            background:{bg};
            min-height:{min_height}px;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
            display:flex;
            flex-direction:column;
            justify-content:space-between;">
            <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div style="font-size:2.2rem;color:{color};font-weight:900;line-height:1.08;word-break:break-word;">{value}</div>
            <div style="font-size:0.95rem;color:#667085;margin-top:12px;line-height:1.5;">{subtitle}</div>
        </div>
        """
    ).format(
        title=title,
        value=value,
        subtitle=subtitle,
        bg=bg,
        border=border,
        color=color,
        min_height=min_height,
    )
    st.markdown(html, unsafe_allow_html=True)


def render_airport_name_box(airport_name: str, airport_icao: str = ""):
    lang = st.session_state.get("language", "en")
    icao_html = (
        f"<div style='font-size:0.95rem;color:#475467;font-weight:700;margin-top:6px;'>{t('ui.icao_prefix', lang)} {airport_icao}</div>"
        if airport_icao else ""
    )
    html = textwrap.dedent(
        """
        <div style="
            border:1px solid #e6eaf0;
            border-radius:14px;
            padding:14px 16px;
            background:#ffffff;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
            margin-bottom:14px;">
            <div style="font-size:0.88rem;color:#667085;font-weight:700;margin-bottom:6px;">{airport_study_point}</div>
            <div style="font-size:1.35rem;color:#1f2937;font-weight:900;line-height:1.15;">{airport_name}</div>
            {icao_html}
        </div>
        """
    ).format(
        airport_name=airport_name,
        icao_html=icao_html,
        airport_study_point=t("ui.airport_study_point", lang),
    )
    st.markdown(html, unsafe_allow_html=True)


def _fleet_capability_hours(results: dict):
    """Hours/day the weakest device sustains in its weakest month - i.e.
    every day of the year with no battery depletion. Mirrors the report's
    headline figure (see report/data_builder._capability_hours) and is the
    same quantity core/simulate.py compares against the requirement to
    decide PASS/FAIL, so it can't disagree with the verdict shown."""
    values = []
    for row in (results or {}).values():
        hours = [float(v) for v in (row.get("hours") or [])]
        if hours:
            values.append(min(hours))
    return min(values) if values else None


def render_required_time_card(hours_value: float, mode_text: str, results: dict = None):
    """Leads with verified capability rather than the requested profile.

    The requested figure is a client input; showing it as the headline
    number made readers take it for a system limit ("this only runs 2
    hrs/day"). It stays on the card as context, below the capability.
    """
    lang = st.session_state.get("language", "en")
    capability = _fleet_capability_hours(results)
    required_text = f"{math.ceil(float(hours_value))} {t('ui.hours_per_day_unit', lang)}"

    if capability is None:
        render_kpi_card(
            t("ui.required_daily_operation", lang),
            required_text,
            f"{mode_text}<br><span style='color:#344054;font-weight:700;'>{operating_window_example(hours_value)}</span>",
            min_height=220,
        )
        return

    if capability >= 23.95:
        value_text = t("report.continuous_operation", lang)
    else:
        value_text = f"{capability:.1f} {t('ui.hours_per_day_unit', lang)}"

    ratio = (capability / float(hours_value)) if float(hours_value) > 0 else None
    if capability < 23.95 and ratio is not None and ratio >= 1.2:
        requirement_note = t("ui.requirement_met_margin_short", lang).format(
            required=required_text, ratio=f"{ratio:.1f}"
        )
    else:
        requirement_note = t("ui.requirement_short", lang).format(required=required_text)

    render_kpi_card(
        t("report.verified_capability", lang),
        value_text,
        f"{t('report.verified_capability_helper', lang)}"
        f"<br><span style='color:#344054;font-weight:700;'>{requirement_note}</span>",
        min_height=220,
    )




def _row_solar_resource_wh_day(row: dict) -> list[float]:
    values = list(row.get("monthly_solar_resource_wh_day") or [])[:12]
    values = values + [0.0] * max(0, 12 - len(values))
    if any(float(v) > 0 for v in values):
        return values

    meta = row.get("pvgis_meta") or {}
    lat = meta.get("lat")
    lon = meta.get("lon")
    pv = row.get("pv")
    tilt = row.get("tilt") if row.get("tilt") is not None else meta.get("slope")
    azim = row.get("azim") if row.get("azim") is not None else meta.get("aspect")
    try:
        if lat is not None and lon is not None and pv is not None and tilt is not None and azim is not None:
            regen = pvcalc_monthly_wh_per_day(
                lat=float(lat),
                lon=float(lon),
                pv_wp=float(pv),
                tilt_deg=float(tilt),
                aspect_deg=float(azim),
            )
            regen = list(regen or [])[:12]
            regen = regen + [0.0] * max(0, 12 - len(regen))
            if any(float(v) > 0 for v in regen):
                return regen
    except Exception:
        pass

    fallback = list(row.get("monthly_generation_wh_day") or [])[:12]
    fallback = fallback + [0.0] * max(0, 12 - len(fallback))
    return fallback


def _suppress_zero_blackout_worst_month(row: dict) -> bool:
    empty_days = list(row.get("empty_battery_days_by_month") or [])[:12]
    empty_days = empty_days + [0] * max(0, 12 - len(empty_days))
    if any(float(v) > 0 for v in empty_days):
        return False
    hours = [float(v) for v in (list(row.get("hours") or [])[:12] + [0.0] * 12)[:12]]
    if not hours:
        return False
    # For fully saturated zero-blackout devices, a user-facing "worst month"
    # is not meaningful. These rows are capped at 24h/day all year, so showing
    # a month derived from solar-resource tie-breakers is misleading.
    return min(hours) >= 23.95

def _worst_device_month(results: dict, device_name: str) -> str | None:
    row = (results or {}).get(device_name) or {}
    if not row:
        for result_key, candidate in (results or {}).items():
            if result_device_display_name(result_key, candidate) == device_name:
                row = candidate
                break
    if _suppress_zero_blackout_worst_month(row):
        return None
    lang = st.session_state.get("language", "en")
    values = list(row.get("empty_battery_days_by_month") or [])[:12]
    values = values + [0] * max(0, 12 - len(values))
    solar_resource = _row_solar_resource_wh_day(row)
    hours = list(row.get("hours") or [])[:12]
    hours = hours + [0.0] * max(0, 12 - len(hours))

    if values and max(float(v) for v in values) > 0:
        max_days = max(float(v) for v in values)
        candidates = [i for i in range(12) if float(values[i]) == max_days]
        idx = min(
            candidates,
            key=lambda i: (
                float(solar_resource[i]),
                float(hours[i]) if hours else float("inf"),
                i,
            ),
        )
        return month_label(MONTHS[idx], lang)

    if not solar_resource or not any(float(v) > 0 for v in solar_resource):
        if not hours or not any(float(v) > 0 for v in hours):
            return None
        idx = min(range(12), key=lambda i: (float(hours[i]), i))
        return month_label(MONTHS[idx], lang)

    idx = min(
        range(12),
        key=lambda i: (
            float(solar_resource[i]),
            float(hours[i]) if hours else float("inf"),
            i,
        ),
    )
    if not hours and not solar_resource:
        return None
    return month_label(MONTHS[idx], lang)


def render_blackout_card(days_value, pct_value, device_name, worst_month, total_devices=0):
    lang = st.session_state.get("language", "en")
    if days_value is None or pct_value is None:
        main = "N/A"
        subtitle = "Worst-device 0% battery exposure not available."
        bg = "#ffffff"
        border = "#e6eaf0"
        color = "#1f2937"
    else:
        lines = []
        if int(days_value) == 0:
            lines.append(t("ui.no_annual_blackout_expected", lang))
            if total_devices == 1 and worst_month:
                lines.append(t("ui.worst_month_only", lang, month=worst_month))
        elif total_devices == 1:
            if worst_month:
                lines.append(t("ui.worst_month_only", lang, month=worst_month))
        else:
            lines.append(f"{pct_value:.1f}% of the year")
            if device_name:
                lines.append(t("ui.worst_device_named", lang, device=device_name))
            if worst_month:
                lines.append(t("ui.worst_month_only", lang, month=worst_month))
        subtitle = "<br>".join(lines)
        main = f"{days_value} {t('ui.days_per_year_unit', lang)}"

        if int(days_value) == 0:
            bg = "#ecfdf3"
            border = "#abefc6"
            color = "#067647"
        else:
            bg = "#fef3f2"
            border = "#fecdca"
            color = "#b42318"

    render_kpi_card(
        t("ui.monthly_0_battery_days", lang),
        main,
        subtitle,
        bg=bg,
        border=border,
        color=color,
        min_height=220,
    )


def render_device_summary_line(results: dict):
    total, passed, failed = count_device_statuses(results)
    lang = st.session_state.get("language", "en")

    if total <= 1:
        return

    if failed == 0:
        text = t("report.devices_meet_requirement", lang, passed=passed, total=total)
        color = "#067647"
        bg = "#ecfdf3"
        border = "#abefc6"
    else:
        text = {
            "en": f"{failed} of {total} devices below requirement",
            "es": f"{failed} de {total} dispositivos por debajo del requisito",
            "fr": f"{failed} dispositifs sur {total} en dessous de l’exigence",
        }.get(lang, f"{failed} of {total} devices below requirement")
        color = "#b42318"
        bg = "#fef3f2"
        border = "#fecdca"

    html = f"""
    <div style="
        border:1px solid {border};
        background:{bg};
        color:{color};
        padding:16px 18px;
        border-radius:16px;
        font-weight:800;
        font-size:1.02rem;
        margin-top:18px;
        box-shadow:0 2px 10px rgba(16,24,40,0.04);">
        {text}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_consumption_basis_block(results: dict):
    lang = st.session_state.get("language", "en")
    has_avlite = any(str((row or {}).get("system_type", "")).lower() == "avlite_fixture" for row in (results or {}).values())
    has_s4ga = any(str((row or {}).get("system_type", "")).lower() != "avlite_fixture" for row in (results or {}).values())

    items = []
    if has_s4ga:
        items.append(("S4GA", t("ui.verified_by_sala", lang), "#ecfdf3", "#abefc6", "#067647"))
    if has_avlite:
        items.append(("Avlite", t("ui.estimated_by_sala", lang), "#fff7db", "#f5c451", "#7a5a00"))

    if not items:
        return

    rows = "".join(
        f"""
        <div style="
            border:1px solid {border};
            background:{bg};
            color:{color};
            border-radius:12px;
            padding:10px 12px;
            font-size:0.90rem;
            font-weight:700;
            line-height:1.45;">
            <div><strong>{t('ui.device_source_info', lang)}:</strong> {brand}</div>
            <div><strong>{t('ui.status', lang)}:</strong> {status}</div>
        </div>
        """
        for brand, status, bg, border, color in items
    )

    st.markdown(
        f"""
        <div style="margin-top:16px;">
            <div style="font-size:0.82rem;color:#667085;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">
                {t('ui.light_data_provider', lang)}
            </div>
            <div style="display:flex;flex-direction:column;gap:8px;">
                {rows}
            </div>
            <div style="font-size:0.84rem;color:#475467;font-weight:700;line-height:1.45;margin-top:8px;">
                {t('ui.feasibility_basis_caption', lang)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_location_map(lat: float, lon: float, airport_name: str):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=10,
        control_scale=True,
        tiles="OpenStreetMap",
    )

    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color="#c0392b",
        fill=True,
        fill_color="#c0392b",
        fill_opacity=0.9,
        weight=2,
        tooltip=airport_name or "Selected study point",
    ).add_to(fmap)

    results = st.session_state.get("results", {})
    map_height = 460 if len(results) > 1 else 400

    render_folium_map(
        fmap,
        height=map_height,
        returned_objects=[],
        key="result_location_map",
        interactive=False,
    )


def render_result():
    lang = st.session_state.get("language", "en")
    st.markdown(f"## {t('ui.feasibility_result', lang)}")

    results = st.session_state.get("results", {})
    if not results:
        return

    state = overall_state(results)
    days, pct, worst_device_name = annual_empty_battery_stats(results)
    worst_month = _worst_device_month(results, worst_device_name)

    airport_name = st.session_state.get("airport_label", "") or "Selected study point"
    airport_icao = st.session_state.get("airport_icao", "") or ""
    required_hours = float(st.session_state.get("required_hours", 0))
    mode_name = operating_mode_name()
    window_text = operating_window_example(required_hours)
    lat = float(st.session_state.get("lat", 0))
    lon = float(st.session_state.get("lon", 0))

    if state == "all_pass":
        box_bg = "#ecfdf3"
        box_fg = "#067647"
        border = "#abefc6"
    elif state == "none_pass":
        box_bg = "#fef3f2"
        box_fg = "#b42318"
        border = "#fecdca"
    else:
        box_bg = "#fff7db"
        box_fg = "#7a5a00"
        border = "#f5c451"

    left, right = st.columns([1.05, 1.6], gap="large")

    with left:
        render_airport_name_box(airport_name, airport_icao)
        render_location_map(lat, lon, airport_name)
        st.caption(f"{lat:.6f}, {lon:.6f}")

    with right:
        summary_html = textwrap.dedent(
            """
            <div style="
                border:1px solid {border};
                border-radius:18px;
                padding:22px 24px;
                background:{box_bg};
                box-shadow:0 2px 10px rgba(16,24,40,0.04);
                margin-bottom:22px;">
                <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">
                    {overall_conclusion}
                </div>
                <div style="font-size:2rem;line-height:1.2;font-weight:800;color:{box_fg};margin-bottom:12px;">
                    {headline}
                </div>
                <div style="font-size:1rem;color:#475467;line-height:1.5;">
                    {subtext}
                </div>
            </div>
            """
        ).format(
            border=border,
            box_bg=box_bg,
            box_fg=box_fg,
            overall_conclusion=t("ui.overall_conclusion", lang),
            headline=overall_conclusion_text(results),
            subtext=overall_interpretation_text(results),
        )

        st.markdown(summary_html, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            render_required_time_card(required_hours, mode_name, results)
        with c2:
            render_blackout_card(
                days,
                pct,
                worst_device_name,
                worst_month,
                total_devices=len(results or {}),
            )

        render_device_summary_line(results)


__all__ = ["render_result", "render_device_capability_cards"]
