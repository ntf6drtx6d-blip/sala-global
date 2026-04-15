from __future__ import annotations

from typing import List, Sequence, Tuple

import plotly.graph_objects as go
import streamlit as st

from core.i18n import month_label, month_labels, t


MONTH_COUNT = 12


def _safe_months(values: Sequence[str] | None) -> List[str]:
    default = month_labels(st.session_state.get("language", "en"))
    if not values:
        return default
    lang = st.session_state.get("language", "en")
    cleaned = [month_label(str(v), lang) for v in values][:MONTH_COUNT]
    return cleaned if cleaned else default



def _safe_numeric_series(values: Sequence[float] | None, length: int, default: float = 0.0) -> List[float]:
    if not values:
        return [default] * length

    cleaned: List[float] = []
    for value in list(values)[:length]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        cleaned.append(number)

    if len(cleaned) < length:
        cleaned.extend([default] * (length - len(cleaned)))

    return cleaned



def _parse_blackout_days(text: str) -> float | None:
    if not text:
        return None
    token = str(text).strip().split()[0]
    try:
        return float(token)
    except ValueError:
        return None



def _metric_card(title: str, value: str, help_text: str, border_color: str = "#d0d5dd") -> None:
    st.markdown(
        f"""
        <div style="
            border:1px solid {border_color};
            border-radius:16px;
            background:#ffffff;
            padding:16px;
            min-height:128px;
        ">
            <div style="font-size:12px;color:#667085;text-transform:uppercase;font-weight:700;letter-spacing:0.03em;margin-bottom:10px;">
                {title}
            </div>
            <div style="font-size:30px;line-height:1.05;font-weight:800;color:#101828;margin-bottom:8px;">
                {value}
            </div>
            <div style="font-size:13px;line-height:1.4;color:#667085;">
                {help_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def _battery_demo(hour: int) -> Tuple[float, float, float]:
    solar_profile = {
        0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
        6: 5.0, 7: 12.0, 8: 25.0, 9: 40.0, 10: 52.0, 11: 60.0,
        12: 64.0, 13: 62.0, 14: 54.0, 15: 40.0, 16: 24.0, 17: 10.0,
        18: 2.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0,
    }
    solar_input = solar_profile.get(hour, 0.0)
    load = 8.0 if hour >= 18 or hour <= 5 else 0.0

    if 6 <= hour <= 16:
        reserve = 32.0 + ((hour - 6) / 10.0) * 58.0
    elif 17 <= hour <= 23:
        reserve = 90.0 - ((hour - 17) / 6.0) * 48.0
    else:
        reserve = 42.0 - ((hour + 1) / 6.0) * 10.0

    reserve = max(5.0, min(100.0, reserve))
    return reserve, solar_input, load



def _battery_panel(hour: int) -> None:
    lang = st.session_state.get("language", "en")
    reserve, solar_input, load = _battery_demo(hour)
    net_flow = solar_input - load
    flow_label = t("legacy.panel_to_battery", lang) if net_flow >= 0 else t("legacy.battery_to_lamp", lang)

    st.markdown(f"### {t('legacy.how_one_solar_light_works', lang)}")
    st.caption(t("legacy.simple_visual_explanation", lang))

    st.progress(int(round(reserve)), text=t("legacy.battery_level", lang, reserve=reserve))

    c1, c2 = st.columns(2)
    with c1:
        st.metric(t("legacy.hour", lang), f"{hour:02d}:00")
        st.metric(t("legacy.solar_input", lang), f"{solar_input:.1f} Wh")
    with c2:
        st.metric(t("legacy.load", lang), f"{load:.1f} Wh")
        st.metric(t("legacy.net_flow", lang), f"{net_flow:+.1f} Wh")

    st.caption(flow_label)



def _reserve_chart(months: List[str], reserve_pct: List[float]) -> go.Figure:
    lang = st.session_state.get("language", "en")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=reserve_pct,
            mode="lines+markers",
            name=t("ui.battery_reserve", lang),
            line={"width": 3},
        )
    )
    fig.add_hline(y=35, line_dash="dot", line_color="#98a2b3")
    fig.add_hline(y=15, line_dash="dot", line_color="#f79009")
    fig.add_hline(y=0, line_dash="solid", line_color="#d92d20")
    fig.update_layout(
        title=t("ui.battery_reserve", lang),
        height=360,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        xaxis_title=t("ui.month", lang),
        yaxis_title=f"{t('ui.battery_reserve', lang)} (%)",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    fig.update_yaxes(range=[0, 100], gridcolor="#eaecf0")
    fig.update_xaxes(gridcolor="#f2f4f7")
    return fig



def _monthly_balance_chart(months: List[str], generated: List[float], demand: List[float]) -> go.Figure:
    lang = st.session_state.get("language", "en")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=months, y=generated, name=t("ui.generated", lang)))
    fig.add_trace(go.Scatter(x=months, y=demand, mode="lines+markers", name=t("ui.required_operation", lang), line={"width": 3}))
    fig.update_layout(
        title=t("ui.daily_battery_energy_balance", lang),
        height=340,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        xaxis_title=t("ui.month", lang),
        yaxis_title="Wh / month",
        plot_bgcolor="white",
        paper_bgcolor="white",
        barmode="group",
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    fig.update_yaxes(gridcolor="#eaecf0")
    fig.update_xaxes(gridcolor="#f2f4f7")
    return fig



def render_energy_flow(
    selected_device_name: str,
    required_hours: float,
    overall_result: str,
    worst_blackout_risk: str,
    lowest_reserve_pct: float,
    months: Sequence[str] | None,
    reserve_pct: Sequence[float] | None,
    generated_monthly_wh: Sequence[float] | None,
    demand_monthly_wh: Sequence[float] | None,
    worst_month: str,
) -> None:
    """Render the Energy Flow tab.

    Clean version of the original page:
    - validates inputs
    - avoids broken raw HTML blocks leaking into the page/PDF
    - keeps only stable Streamlit/Plotly rendering for the main content
    """

    lang = st.session_state.get("language", "en")
    months_clean = _safe_months(months)
    reserve_clean = _safe_numeric_series(reserve_pct, len(months_clean), default=0.0)
    generated_clean = _safe_numeric_series(generated_monthly_wh, len(months_clean), default=0.0)
    demand_clean = _safe_numeric_series(demand_monthly_wh, len(months_clean), default=0.0)

    try:
        required_hours_value = float(required_hours)
    except (TypeError, ValueError):
        required_hours_value = 0.0

    try:
        lowest_reserve_value = float(lowest_reserve_pct)
    except (TypeError, ValueError):
        lowest_reserve_value = 0.0

    overall_clean = str(overall_result or "N/A").upper()
    worst_month_clean = str(worst_month or "N/A")
    selected_device_clean = str(selected_device_name or t("legacy.unknown_device", lang))
    blackout_days = _parse_blackout_days(str(worst_blackout_risk))

    result_border = "#12b76a" if overall_clean == "PASS" else "#f04438"
    risk_border = "#12b76a" if blackout_days == 0 else "#f04438"
    reserve_border = "#12b76a" if lowest_reserve_value >= 35 else "#f79009" if lowest_reserve_value >= 15 else "#f04438"

    st.markdown(f"## {t('legacy.energy_flow_title', lang)}")
    st.caption(t("legacy.energy_flow_caption", lang))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card(t("legacy.required_daily_operation", lang), f"{required_hours_value:.0f} {t('ui.hours_per_day_unit', lang)}", t("legacy.daily_operation_checked", lang))
    with c2:
        _metric_card(t("legacy.worst_blackout_risk", lang), str(worst_blackout_risk), t("legacy.highest_blackout_exposure", lang), risk_border)
    with c3:
        _metric_card(t("legacy.lowest_battery_reserve", lang), f"{lowest_reserve_value:.0f}%", t("legacy.lowest_reserve_reached", lang), reserve_border)
    with c4:
        _metric_card(t("legacy.annual_result", lang), overall_clean, t("legacy.feasibility_against_requirement", lang), result_border)

    left, right = st.columns([1, 1.35], gap="large")
    with left:
        hour = st.slider(t("legacy.hour", lang), min_value=0, max_value=23, value=14, step=1, key="energy_flow_hour")
        _battery_panel(hour)

    with right:
        st.plotly_chart(_reserve_chart(months_clean, reserve_clean), use_container_width=True)

    st.markdown(f"### {t('legacy.worst_case_period', lang)}")
    wc1, wc2, wc3 = st.columns(3)
    wc1.metric(t("legacy.worst_month", lang), worst_month_clean)
    wc2.metric(t("legacy.lowest_reserve", lang), f"{lowest_reserve_value:.0f}%")
    wc3.metric(t("legacy.blackout_exposure", lang), str(worst_blackout_risk))
    st.caption(t("legacy.worst_case_caption", lang))

    st.plotly_chart(_monthly_balance_chart(months_clean, generated_clean, demand_clean), use_container_width=True)

    with st.expander(t("legacy.checked_requirement_meaning", lang)):
        st.write(t("legacy.checked_requirement_body", lang))

    st.caption(t("legacy.selected_device", lang, device=selected_device_clean))
