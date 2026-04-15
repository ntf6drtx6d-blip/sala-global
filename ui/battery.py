# ui/battery.py

import streamlit as st
import math

from core.i18n import month_labels, t


def _min_achievable_hours(r):
    hours = r.get("hours", [])
    if not hours:
        return None
    return min(hours)


def _battery_reserve_hours(r):
    try:
        batt = float(r.get("batt", 0))
        power = max(float(r.get("power", 0.01)), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def _format_hours(h):
    if h is None:
        return "—"
    lang = st.session_state.get("language", "en")
    h = float(h)
    whole = int(h)
    minutes = int(round((h - whole) * 60))
    if minutes == 0:
        return f"{whole} {t('ui.hours_per_day_unit', lang)}"
    return f"{whole}h {minutes:02d}m"


def _kpi_card(title, value, subtitle):
    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            min-height:150px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
        ">
            <div style="font-size:0.9rem;color:#667085;font-weight:700;">
                {title}
            </div>
            <div style="font-size:2.2rem;font-weight:900;color:#1f2937;">
                {value}
            </div>
            <div style="font-size:0.9rem;color:#667085;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _interpretation(required, achievable, reserve):
    lang = st.session_state.get("language", "en")
    if achievable is None or reserve is None:
        return t("legacy.insufficient_data_interpretation", lang)

    return t(
        "legacy.battery_interpretation",
        lang,
        required=required,
        achievable=achievable,
        reserve=reserve,
    )


def render_battery_section(results: dict):
    if not results:
        return
    lang = st.session_state.get("language", "en")

    st.markdown(f"## {t('legacy.operating_requirement_vs_capability', lang)}")

    required = float(st.session_state.get("required_hours", 0))

    # pick primary device
    primary_name = list(results.keys())[0]
    r = results[primary_name]

    achievable = _min_achievable_hours(r)
    reserve = _battery_reserve_hours(r)

    c1, c2, c3 = st.columns(3)

    with c1:
        _kpi_card(
            t("legacy.required_operation", lang),
            f"{required:.0f} {t('ui.hours_per_day_unit', lang)}",
            t("legacy.what_airport_needs", lang),
        )

    with c2:
        _kpi_card(
            t("legacy.achievable_worst_month", lang),
            f"{_format_hours(achievable)}/day",
            t("legacy.lowest_guaranteed_month", lang),
        )

    with c3:
        _kpi_card(
            t("legacy.battery_only_reserve", lang),
            _format_hours(reserve),
            t("legacy.no_sun_fallback", lang),
        )

    st.markdown(
        f"""
        <div style="
            margin-top:18px;
            padding:16px 18px;
            border-left:4px solid #2e5aac;
            background:#f8fafc;
            border-radius:8px;
            font-size:0.95rem;
            color:#344054;
            line-height:1.6;">
            {_interpretation(required, achievable, reserve)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- GRAPH ----------

    st.markdown(f"### {t('legacy.battery_depletion_pattern', lang)}")

    monthly = r.get("monthly_empty_battery_days", [])

    if not monthly:
        return

    import plotly.graph_objects as go

    months = month_labels(lang)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months,
        y=monthly,
        mode="lines+markers",
        fill="tozeroy",
        line=dict(width=2),
        name=t("legacy.empty_battery_days", lang)
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title=None,
        yaxis_title=f"{t('ui.days', lang)}/{t('ui.month', lang).lower()}",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
