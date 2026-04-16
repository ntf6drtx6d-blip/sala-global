# ui/result_devices.py

import textwrap

import plotly.graph_objects as go
import streamlit as st

from core.i18n import month_label, month_labels, t
from ui.result_helpers import battery_reserve_hours, device_blackout_days, format_battery_hours, format_energy_wh, short_device_label


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


STATUS_STYLES = {
    "neutral": {"border": "#d0d5dd", "color": "#101828", "bg": "#ffffff"},
    "success": {"border": "#12b76a", "color": "#067647", "bg": "#ecfdf3"},
    "warning": {"border": "#f79009", "color": "#b54708", "bg": "#fff7ed"},
    "danger": {"border": "#f04438", "color": "#b42318", "bg": "#fef3f2"},
}


def render_kpi_card(title, value, helper=None, border_status="neutral"):
    style = STATUS_STYLES.get(border_status, STATUS_STYLES["neutral"])
    helper_html = (
        f"<div style='font-size:0.78rem;color:#667085;line-height:1.35;margin-top:10px;'>{helper}</div>"
        if helper else ""
    )
    st.markdown(
        textwrap.dedent(
            f"""
            <div style="
                background:{style['bg']};
                border:1.4px solid {style['border']};
                border-radius:16px;
                padding:14px 14px 12px 14px;
                min-height:136px;
                display:flex;
                flex-direction:column;
                justify-content:space-between;">
                <div style="font-size:0.78rem;color:#667085;font-weight:700;letter-spacing:0.02em;text-transform:uppercase;line-height:1.25;">
                    {title}
                </div>
                <div style="font-size:1.45rem;font-weight:900;color:{style['color']};line-height:1.15;margin-top:10px;overflow-wrap:anywhere;">
                    {value}
                </div>
                {helper_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_interpretation_line(text, status="neutral"):
    style = STATUS_STYLES.get(status, STATUS_STYLES["neutral"])
    st.markdown(
        textwrap.dedent(
            f"""
            <div style="
                border:1px solid {style['border']};
                border-radius:12px;
                padding:10px 12px;
                background:#fafbfc;
                color:#344054;
                font-size:0.95rem;
                line-height:1.4;
                margin:6px 0 14px 0;">
                {text}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_device_basis_card(title, rows):
    st.markdown(
        f"<div style='font-size:0.98rem;font-weight:800;color:#101828;margin-bottom:10px;'>{title}</div>",
        unsafe_allow_html=True,
    )
    card_rows = "".join(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:7px 0;border-top:1px solid #eef2f6;">
            <div style="color:#667085;font-size:0.88rem;font-weight:700;flex:0 0 36%;max-width:36%;">{label}</div>
            <div style="color:#101828;font-size:0.92rem;font-weight:700;text-align:right;flex:1;min-width:0;overflow-wrap:anywhere;">{value}</div>
        </div>
        """
        for label, value in rows
    )
    st.markdown(
        f"""
        <div style="border:1px solid #e6eaf0;border-radius:16px;padding:14px 16px;background:#ffffff;min-height:176px;">
            {card_rows}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_wp(val):
    try:
        return f"{float(val):.1f} Wp"
    except Exception:
        return "N/A"


def _fmt_pct(val):
    try:
        return f"{float(val):.0f}%"
    except Exception:
        return "N/A"


def _lowest_battery_label(result_row, total_pct):
    base = _fmt_pct(total_pct)
    if total_pct is None:
        return base
    cutoff = _safe_float(result_row.get("cutoff_pct"), 0.0)
    if abs(float(total_pct) - cutoff) < 0.05:
        return f"{base} (cut-off level)"
    return base


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _unique_panel_wp_text(panel_list):
    try:
        vals = sorted({float(p.get("wp", 0)) for p in (panel_list or [])})
        vals = [v for v in vals if v > 0]
        if not vals:
            return "N/A"
        if len(vals) == 1:
            return f"{vals[0]:.1f} W"
        return " / ".join(f"{v:.1f} W" for v in vals)
    except Exception:
        return "N/A"


def _panel_geometry_text(result_row):
    lang = st.session_state.get("language", "en")
    geometry = str(result_row.get("physical_panel_geometry") or "").strip()
    if geometry:
        normalized = geometry.lower()
        if normalized == "two opposite angled panels":
            return t("ui.two_opposite_angled_panels", lang)
        return normalized
    count = int(result_row.get("panel_count", 0) or 0)
    if count == 4:
        return t("ui.four_vertical_panels", lang)
    if count == 2:
        return t("ui.two_panels", lang)
    return t("ui.panel_array", lang)


def _solar_configuration_summary(result_row):
    lang = st.session_state.get("language", "en")
    panel_list = result_row.get("panel_list", []) or []
    panel_count = int(result_row.get("panel_count", len(panel_list) or 0))
    panel_power = _unique_panel_wp_text(panel_list)
    geometry = _panel_geometry_text(result_row)
    if panel_count <= 1:
        return t("ui.single_panel", lang)
    if panel_count > 0 and panel_power != "N/A":
        return f"{panel_count} x {panel_power} ({geometry})"
    return geometry.title()


def _lighting_input_source(result_row):
    lang = st.session_state.get("language", "en")
    if str(result_row.get("system_type", "")).lower() == "avlite_fixture":
        return (
            t("ui.estimated_by_sala", lang),
            "Avlite",
            t("ui.estimated_basis_copy", lang),
            "warning",
        )
    return (
        t("ui.verified_by_sala", lang),
        "S4GA",
        t("ui.verified_basis_copy", lang),
        "success",
    )


def _monthly_graph_data(result_row):
    generated = list(result_row.get("charge_day_pct_by_month") or [])[:12]
    discharge_day = result_row.get("discharge_pct_per_day")
    empty_days = list(result_row.get("empty_battery_days_by_month") or [])[:12]

    generated = generated + [0.0] * max(0, 12 - len(generated))
    empty_days = empty_days + [0] * max(0, 12 - len(empty_days))
    discharge = [float(discharge_day or 0.0)] * 12
    return generated, discharge, empty_days


def _usable_to_total_pct(result_row, usable_pct):
    cutoff = _safe_float(result_row.get("cutoff_pct"), 0.0)
    usable_share = max(0.0, 1.0 - cutoff / 100.0)
    return cutoff + max(_safe_float(usable_pct), 0.0) * usable_share


def _risk_status_from_days(days):
    days = int(days or 0)
    if days == 0:
        return "success"
    if days <= 5:
        return "warning"
    return "danger"


def _risk_status_from_total_pct(result_row, total_pct):
    cutoff = _safe_float(result_row.get("cutoff_pct"), 0.0)
    if total_pct is None:
        return "neutral"
    gap = float(total_pct) - cutoff
    if gap >= 25:
        return "success"
    if gap >= 10:
        return "warning"
    return "danger"


def _annual_result_status(result_row):
    value = str(result_row.get("status", "FAIL")).upper()
    if value == "PASS":
        return "success"
    if value == "NEAR THRESHOLD":
        return "warning"
    return "danger"


def _annual_result_text(result_row):
    value = str(result_row.get("status", "FAIL")).upper()
    lang = st.session_state.get("language", "en")
    if value == "PASS":
        return t("ui.pass", lang)
    if value == "NEAR THRESHOLD":
        return t("ui.near_threshold", lang)
    return t("ui.fail", lang)


def _interpretation_text(result_row, blackout_days):
    value = str(result_row.get("status", "FAIL")).upper()
    lang = st.session_state.get("language", "en")
    if value == "PASS":
        return {
            "en": "System maintains required operation throughout the year.",
            "es": "El sistema mantiene la operación requerida durante todo el año.",
            "fr": "Le système maintient le fonctionnement requis tout au long de l’année.",
        }.get(lang, "System maintains required operation throughout the year.")
    if value == "NEAR THRESHOLD":
        return {
            "en": "System is near the compliance threshold.",
            "es": "El sistema está cerca del umbral de conformidad.",
            "fr": "Le système est proche du seuil de conformité.",
        }.get(lang, "System is near the compliance threshold.")
    return {
        "en": "System does not sustain required operation under annual worst-case conditions.",
        "es": "El sistema no sostiene la operación requerida en las condiciones anuales más desfavorables.",
        "fr": "Le système ne maintient pas le fonctionnement requis dans les conditions annuelles les plus défavorables.",
    }.get(lang, "System does not sustain required operation under annual worst-case conditions.")


def _panel_count(result_row):
    try:
        if str(result_row.get("system_type", "")).lower() != "avlite_fixture":
            return 1
        panel_list = result_row.get("panel_list", []) or []
        if panel_list:
            return len(panel_list)
        return int(result_row.get("panel_count", 0) or 0)
    except Exception:
        return 0


def _device_metrics(result_row):
    generated, discharge, empty_days = _monthly_graph_data(result_row)
    required_hours = _safe_float(st.session_state.get("required_hours"), 0.0)
    blackout_days = device_blackout_days(result_row) or 0

    preclip_min = list(result_row.get("soc_monthly_preclip_min") or result_row.get("soc_monthly_min") or [])[:12]
    preclip_min = preclip_min + [None] * max(0, 12 - len(preclip_min))

    margin_by_month = [float(g) - float(d) for g, d in zip(generated, discharge)]
    if any(float(v) > 0 for v in empty_days):
        weakest_month_idx = max(range(12), key=lambda i: float(empty_days[i]))
    elif margin_by_month:
        weakest_month_idx = min(range(12), key=lambda i: margin_by_month[i])
    else:
        weakest_month_idx = 0

    lowest_total_pct = _usable_to_total_pct(result_row, preclip_min[weakest_month_idx])
    worst_blackout_risk = max(int(round(float(v))) for v in empty_days) if empty_days else 0
    generated_consumed_close = bool(generated) and max(abs(float(g) - float(d)) for g, d in zip(generated, discharge)) <= 2.0
    return {
        "generated": generated,
        "discharge": discharge,
        "empty_days": empty_days,
        "required_hours": required_hours,
        "blackout_days_year": int(blackout_days),
        "worst_blackout_risk": int(worst_blackout_risk),
        "weakest_month_idx": weakest_month_idx,
        "lowest_battery_state_pct": lowest_total_pct,
        "annual_result": _annual_result_text(result_row),
        "generated_consumed_close": generated_consumed_close,
        "is_single_panel": _panel_count(result_row) <= 1,
    }


def render_operational_chart(result_row, metrics):
    lang = st.session_state.get("language", "en")
    month_tick_labels = month_labels(lang)
    x_values = month_tick_labels
    generated = metrics["generated"]
    discharge = metrics["discharge"]
    empty_days = metrics["empty_days"]
    show_empty_days = any(float(v) > 0 for v in empty_days)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=generated,
            name=t("ui.generated", lang),
            mode="lines+markers",
            line=dict(color="#16a34a", width=2.6),
            marker=dict(size=6, color="#16a34a"),
            hovertemplate=f"{t('ui.month', lang)}: %{{x}}<br>{t('ui.generated', lang)}: %{{y:.2f}}%/day<extra></extra>",
        )
    )
    if show_empty_days:
        fig.add_trace(
            go.Bar(
                x=x_values,
                y=empty_days,
                name=t("ui.monthly_0_battery_days", lang),
                yaxis="y2",
                marker=dict(color="rgba(59,130,246,0.72)", line=dict(color="#2563eb", width=1.2)),
                width=0.42,
                hovertemplate=f"{t('ui.month', lang)}: %{{x}}<br>{t('ui.monthly_0_battery_days', lang)}: %{{y:.0f}}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=discharge,
            name=t("ui.consumed", lang),
            mode="lines+markers",
            line=dict(color="#f97316", width=2.6),
            marker=dict(size=6, color="#f97316"),
            hovertemplate=f"{t('ui.month', lang)}: %{{x}}<br>{t('ui.consumed', lang)}: %{{y:.2f}}%/day<extra></extra>",
        )
    )

    fig.update_layout(
        height=320,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=18, r=18, t=24, b=16),
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(255,255,255,0.85)"),
        hovermode="x unified",
        barmode="overlay",
        xaxis=dict(
            title=t("ui.month", lang),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title=t("ui.percent_battery_per_day", lang),
            range=[0, max(max(generated + discharge + [0]), 5) * 1.18],
            gridcolor="rgba(16,24,40,0.08)",
            zeroline=False,
        ),
        yaxis2=(
            dict(
                title=dict(text=t("ui.monthly_0_battery_days", lang), font=dict(color="#2563eb")),
                overlaying="y",
                side="right",
                range=[0, 30],
                tickmode="array",
                tickvals=[0, 10, 20, 30],
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor="#2563eb",
                tickfont=dict(color="#2563eb"),
                ticks="outside",
                ticklen=5,
            )
            if show_empty_days else
            dict(visible=False)
        ),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(t("ui.energy_table_caption", lang))

    detail_rows = []
    for month, month_text, gen, cons, days in zip(MONTHS, month_tick_labels, generated, discharge, empty_days):
        detail_rows.append(
            {
                t("ui.month", lang): month_text,
                t("ui.recharge_per_day", lang): f"{float(gen):.2f}",
                t("ui.discharge_per_day", lang): f"{float(cons):.2f}",
                t("ui.monthly_0_battery_days", lang): f"{float(days):.0f}",
            }
        )
    with st.expander(t("ui.detailed_energy_table", lang), expanded=False):
        st.dataframe(detail_rows, width="stretch", hide_index=True)


def _device_header(label, result_row):
    status = _annual_result_status(result_row)
    style = STATUS_STYLES.get(status, STATUS_STYLES["neutral"])
    status_text = _annual_result_text(result_row)
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px;padding:12px 14px;border-radius:14px;background:{style['bg']};border:1px solid {style['border']};">
            <div style="font-size:1.25rem;font-weight:900;color:#101828;line-height:1.15;">{label}</div>
            <div style="
                display:inline-flex;
                align-items:center;
                justify-content:center;
                border:1.3px solid {style['border']};
                background:{style['bg']};
                color:{style['color']};
                border-radius:999px;
                padding:8px 12px;
                font-size:0.8rem;
                font-weight:800;
                line-height:1.25;
                text-align:center;
                max-width:48%;">
                {status_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_device_capability_cards(results: dict):
    lang = st.session_state.get("language", "en")
    st.markdown(f"## {t('ui.device_breakdown', lang)}")

    for device_name, result_row in results.items():
        label = short_device_label(device_name)
        metrics = _device_metrics(result_row)
        status_text = _annual_result_text(result_row)
        status_key = _annual_result_status(result_row)
        style = STATUS_STYLES.get(status_key, STATUS_STYLES["neutral"])
        with st.expander(f"{label} • {status_text}", expanded=False):
            with st.container(border=True):
                _device_header(label, result_row)

                cols = st.columns(4)
                cards = [
                    (
                        t("ui.required_daily_operation", lang),
                        f"{metrics['required_hours']:.0f} {t('ui.hours_per_day_unit', lang)}",
                        t("ui.checked_operating_requirement", lang),
                        "neutral",
                    ),
                    (
                        t("ui.worst_blackout_risk", lang),
                        f"{metrics['blackout_days_year']} {t('ui.days_per_year_unit', lang)}",
                        t("ui.annual_days_full_depletion", lang),
                        _risk_status_from_days(metrics["blackout_days_year"]),
                    ),
                    (
                        t("ui.lowest_battery_state", lang),
                        _lowest_battery_label(result_row, metrics["lowest_battery_state_pct"]),
                        t("ui.lowest_level_reached", lang, month=month_label(MONTHS[metrics["weakest_month_idx"]], lang)),
                        _risk_status_from_total_pct(result_row, metrics["lowest_battery_state_pct"]),
                    ),
                    (
                        t("ui.annual_result", lang),
                        metrics["annual_result"],
                        t("ui.annual_classification", lang),
                        _annual_result_status(result_row),
                    ),
                ]
                for col, (title, value, helper, status) in zip(cols, cards):
                    with col:
                        render_kpi_card(title, value, helper, status)

                render_interpretation_line(
                    _interpretation_text(result_row, metrics["blackout_days_year"]),
                    _annual_result_status(result_row),
                )

                left, right = st.columns(2)
                with left:
                    render_device_basis_card(
                        t("ui.battery", lang),
                        [
                            (t("ui.technology", lang), str(result_row.get("battery_type", "N/A"))),
                            (t("ui.battery_autonomy", lang), format_battery_hours(battery_reserve_hours(result_row))),
                            (t("ui.total_capacity", lang), format_energy_wh(result_row.get("batt"))),
                            (t("ui.usable_window", lang), format_energy_wh(result_row.get("usable_battery_wh"))),
                            (t("ui.cutoff", lang), _fmt_pct(result_row.get("cutoff_pct"))),
                        ],
                    )
                with right:
                    render_device_basis_card(
                        t("ui.solar", lang),
                        (
                            [
                                (t("ui.configuration", lang), _solar_configuration_summary(result_row)),
                                (t("ui.nominal_power", lang), _fmt_wp(result_row.get("total_nominal_wp", result_row.get("pv")))),
                                (t("ui.single_panel_tilt", lang), f"{_safe_float(result_row.get('tilt', result_row.get('equivalent_panel_tilt', 0))):.0f}°"),
                            ]
                            if metrics["is_single_panel"]
                            else [
                                (t("ui.configuration", lang), _solar_configuration_summary(result_row)),
                                (t("ui.nominal_power", lang), _fmt_wp(result_row.get("total_nominal_wp", result_row.get("pv")))),
                                (t("ui.effective_power", lang), _fmt_wp(result_row.get("equivalent_panel_wp", result_row.get("pv")))),
                                (t("ui.effective_ratio", lang), _fmt_pct(result_row.get("equivalent_pct_of_physical_nominal"))),
                                (t("ui.equivalent_tilt", lang), f"{_safe_float(result_row.get('equivalent_panel_tilt', result_row.get('tilt', 0))):.0f}°"),
                            ]
                        ),
                    )

                source_status, source_name, source_copy, source_style = _lighting_input_source(result_row)
                source_palette = STATUS_STYLES.get(source_style, STATUS_STYLES["neutral"])
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid {source_palette['border']};
                        background:{source_palette['bg']};
                        border-radius:16px;
                        padding:14px 16px;
                        margin-top:14px;">
                        <div style="display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap;">
                            <div>
                                <div style="font-size:0.84rem;color:#667085;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;">
                                    {t("ui.light_data_provider", lang)}
                                </div>
                                <div style="font-size:1.02rem;color:#101828;font-weight:900;margin-top:6px;">
                                    {source_name}
                                </div>
                            </div>
                            <div style="
                                border:1px solid {source_palette['border']};
                                color:{source_palette['color']};
                                background:#ffffffb3;
                                border-radius:999px;
                                padding:8px 12px;
                                font-size:0.8rem;
                                font-weight:800;">
                                {source_status}
                            </div>
                        </div>
                        <div style="font-size:0.92rem;color:#475467;line-height:1.45;margin-top:10px;">
                            {source_copy}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(f"### {t('ui.daily_battery_energy_balance', lang)}")
                render_operational_chart(result_row, metrics)
                if metrics["generated_consumed_close"]:
                    st.caption(t("ui.generated_consumed_close", lang))
