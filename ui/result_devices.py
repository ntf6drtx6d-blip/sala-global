
# ui/result_devices.py

import textwrap
import streamlit as st
import plotly.graph_objects as go

from ui.result_helpers import (
    battery_reserve_hours,
    device_blackout_days,
    format_achievable_hours,
    format_battery_hours,
    short_device_label,
    format_panel_azimuths,
    format_energy_wh,
    format_percent,
)


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    bg: str = "#ffffff",
    border: str = "#e6eaf0",
    color: str = "#1f2937",
    min_height: int = 170,
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
            <div style="font-size:2.1rem;color:{color};font-weight:900;line-height:1.1;word-break:break-word;">{value}</div>
            <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.45;">{subtitle}</div>
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


def device_status_chip(status: str):
    if status == "PASS":
        return '<span style="background:#ecfdf3;color:#067647;border:1px solid #abefc6;padding:4px 10px;border-radius:999px;font-size:0.82rem;font-weight:800;">Meets requirement</span>'
    return '<span style="background:#fef3f2;color:#b42318;border:1px solid #fecdca;padding:4px 10px;border-radius:999px;font-size:0.82rem;font-weight:800;">Below requirement</span>'


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


def _unique_panel_tilt_text(panel_list):
    try:
        vals = sorted({float(p.get("tilt", 0)) for p in (panel_list or [])})
        vals = [v for v in vals if v > 0]
        if not vals:
            return "N/A"
        if len(vals) == 1:
            return f"{vals[0]:.0f}°"
        return " / ".join(f"{v:.0f}°" for v in vals)
    except Exception:
        return "N/A"


def _panel_configuration_text(result_row):
    geometry = result_row.get("physical_panel_geometry")
    if geometry:
        return str(geometry)

    count = result_row.get("panel_count")
    try:
        count = int(count)
    except Exception:
        count = 0

    if count == 4:
        return "4-sided"
    if count == 2:
        return "2-sided"
    if count > 0:
        return f"{count}-panel"
    return "N/A"


def _render_key_value_table(rows, title=None):
    if title:
        st.markdown(f"### {title}")

    with st.container(border=True):
        for label, value in rows:
            c1, c2 = st.columns([1.2, 2.2])
            with c1:
                st.markdown(
                    f"<div style='color:#667085;font-weight:700;'>{label}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"<div style='color:#1f2937;'>{value}</div>",
                    unsafe_allow_html=True,
                )


def _monthly_graph_data(result_row):
    reserve = result_row.get("soc_monthly_end") or result_row.get("soc_monthly_avg") or []
    generated = result_row.get("charge_day_pct_by_month") or []
    discharge_day = result_row.get("discharge_pct_per_day")
    empty_days = result_row.get("empty_battery_days_by_month") or [0] * 12
    daylight = result_row.get("daylight_hours_by_month") or [0] * 12
    recharge_hr = result_row.get("recharge_pct_per_hr_by_month") or [0] * 12
    discharge_hr = float(result_row.get("discharge_pct_per_hr", 0.0))
    if discharge_day is None:
        discharge = [0.0] * 12
    else:
        discharge = [float(discharge_day)] * 12

    # normalize lengths
    reserve = list(reserve)[:12] + [None] * max(0, 12 - len(reserve))
    generated = list(generated)[:12] + [0.0] * max(0, 12 - len(generated))
    discharge = list(discharge)[:12] + [0.0] * max(0, 12 - len(discharge))
    empty_days = list(empty_days)[:12] + [0] * max(0, 12 - len(empty_days))
    daylight = list(daylight)[:12] + [0.0] * max(0, 12 - len(daylight))
    recharge_hr = list(recharge_hr)[:12] + [0.0] * max(0, 12 - len(recharge_hr))

    return reserve, generated, discharge, empty_days, daylight, recharge_hr, discharge_hr


def _render_charge_discharge_chart(result_row):
    reserve, generated, discharge, empty_days, daylight, recharge_hr, discharge_hr = _monthly_graph_data(result_row)

    if not reserve or not generated:
        st.info("Battery charge/discharge behavior is not available for this device.")
        return

    fig = go.Figure()

    # Month shading: surplus vs deficit based on generated/consumed daily %
    for i, month in enumerate(MONTHS):
        is_deficit = generated[i] < discharge[i]
        color = "rgba(239,68,68,0.08)" if is_deficit else "rgba(34,197,94,0.06)"
        fig.add_vrect(
            x0=i - 0.5,
            x1=i + 0.5,
            fillcolor=color,
            line_width=0,
            layer="below",
        )

    custom = list(zip(
        generated,
        discharge,
        [g - d for g, d in zip(generated, discharge)],
        empty_days,
        recharge_hr,
        [discharge_hr] * 12,
        daylight,
    ))

    fig.add_trace(
        go.Scatter(
            x=MONTHS,
            y=reserve,
            name="Usable battery reserve (%)",
            mode="lines+markers",
            line=dict(width=3),
            marker=dict(size=7),
            yaxis="y1",
            customdata=custom,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Battery reserve: %{y:.1f}%<br>"
                "Generated: %{customdata[0]:.1f}%/day<br>"
                "Consumed: %{customdata[1]:.1f}%/day<br>"
                "Net: %{customdata[2]:+.1f}%/day<br>"
                "Empty battery days: %{customdata[3]}<br>"
                "Recharge rate: %{customdata[4]:.2f}%/h × %{customdata[6]:.1f} h daylight<br>"
                "Discharge rate: %{customdata[5]:.2f}%/h"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=MONTHS,
            y=generated,
            name="Generated (% of battery/day)",
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=6),
            yaxis="y2",
            customdata=custom,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Generated: %{y:.1f}%/day<br>"
                "Recharge rate: %{customdata[4]:.2f}%/h × %{customdata[6]:.1f} h daylight"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=MONTHS,
            y=discharge,
            name="Consumed (% of battery/day)",
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=6),
            yaxis="y2",
            customdata=custom,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Consumed: %{y:.1f}%/day<br>"
                "Discharge rate: %{customdata[5]:.2f}%/h"
                "<extra></extra>"
            ),
        )
    )

    zero_months = [MONTHS[i] for i, v in enumerate(reserve) if v is not None and float(v) <= 0.001]
    zero_vals = [v for v in reserve if v is not None and float(v) <= 0.001]
    if zero_months:
        fig.add_trace(
            go.Scatter(
                x=zero_months,
                y=zero_vals,
                mode="markers",
                name="Reserve exhausted",
                marker=dict(size=9, symbol="x"),
                hovertemplate="<b>%{x}</b><br>Usable reserve exhausted (0%)<extra></extra>",
                yaxis="y1",
            )
        )

    fig.update_layout(
        title="Battery charge vs discharge behavior",
        height=430,
        xaxis=dict(title="Month"),
        yaxis=dict(
            title="Usable battery reserve (%)",
            range=[0, 100],
        ),
        yaxis2=dict(
            title="Generated / consumed (% of usable battery per day)",
            overlaying="y",
            side="right",
            rangemode="tozero",
        ),
        legend=dict(orientation="h", y=1.12, x=0),
        margin=dict(l=20, r=20, t=70, b=20),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "0% on this chart means usable battery reserve is exhausted and the device has reached its operational cut-off threshold. "
        "Green months indicate that generated energy is sufficient to recover or maintain reserve. "
        "Red months indicate that the device consumes stored reserve faster than it is replenished."
    )


def render_device_capability_cards(results: dict):
    st.markdown("## Device-level performance breakdown")

    required = float(st.session_state.get("required_hours", 0))

    for device_name, r in results.items():
        label = short_device_label(device_name)
        hours = r.get("hours", [])
        achievable = min(hours) if hours else None
        reserve = battery_reserve_hours(r)
        blackout_days = device_blackout_days(r)

        ach_text = format_achievable_hours(achievable) if achievable is not None else "N/A"
        reserve_text = format_battery_hours(reserve) if reserve is not None else "N/A"
        blackout_text = f"{blackout_days} days/year" if blackout_days is not None else "N/A"

        status_html = device_status_chip(r.get("status", "FAIL"))

        with st.expander(f"{label}", expanded=(len(results) == 1)):
            st.markdown(
                f"""
                <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:10px;">
                    <div>{status_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                render_kpi_card(
                    "Blackout days",
                    blackout_text,
                    "Days per year when this device is expected to fall below requirement",
                    min_height=150,
                )

            with c2:
                render_kpi_card(
                    "Achievable (worst month)",
                    ach_text,
                    "Lowest sustainable daily operation",
                    min_height=150,
                )

            with c3:
                render_kpi_card(
                    "Battery-only reserve",
                    reserve_text,
                    "Fallback without solar input",
                    min_height=150,
                )

            if achievable is not None and reserve is not None:
                note = (
                    f"The airport requires {required:.1f} hrs/day. "
                    f"For {label}, the lowest sustainable result during the year is {achievable:.1f} hrs/day. "
                    f"Battery-only reserve is approximately {reserve:.1f} hrs. "
                )

                if blackout_days is not None:
                    note += f"Blackout risk for this device is {blackout_days} days/year. "

                if r.get("status") == "PASS":
                    note += "This device remains above the required operating profile throughout the full annual cycle."
                else:
                    note += "The limitation is driven by insufficient solar energy recovery, not battery size alone."
            else:
                note = "Device-level operating capability could not be fully calculated."

            st.markdown(
                f"""
                <div style="
                    border-left:4px solid #3b5ccc;
                    background:#f8fafc;
                    padding:14px 16px;
                    border-radius:10px;
                    margin-top:12px;
                    color:#344054;
                    line-height:1.6;">
                    {note}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if r.get("system_type") == "avlite_fixture":
                panel_list = r.get("panel_list", []) or []
                nominal_wp = r.get("total_nominal_wp")
                effective_wp = r.get("equivalent_panel_wp", r.get("pv"))
                effective_pct = r.get("equivalent_pct_of_physical_nominal")
                equivalent_tilt = r.get("equivalent_panel_tilt", 33)

                configuration = _panel_configuration_text(r)
                panel_count = int(r.get("panel_count", len(panel_list) or 0))
                panels_text = f"{panel_count} × {_unique_panel_wp_text(panel_list)}"
                nominal_tilt_text = _unique_panel_tilt_text(panel_list)
                azimuth_text = format_panel_azimuths(panel_list)

                _render_key_value_table(
                    [
                        ("Nominal multi-face PV", _fmt_wp(nominal_wp)),
                        ("Effective PV used in simulation", _fmt_wp(effective_wp)),
                        ("Effective PV as % of nominal", _fmt_pct(effective_pct)),
                        ("Equivalent PV tilt used in simulation", f"{float(equivalent_tilt):.0f}°"),
                    ],
                    title="Solar input used in simulation",
                )

                _render_key_value_table(
                    [
                        ("Configuration", configuration),
                        ("Panels", panels_text),
                        ("Nominal panel tilt(s)", nominal_tilt_text),
                        ("Nominal panel azimuth", azimuth_text),
                    ],
                    title="Physical panel geometry",
                )

            _render_key_value_table(
                [
                    ("Battery type", str(r.get("battery_type", "N/A"))),
                    ("Battery cut-off limit", _fmt_pct(r.get("cutoff_pct"))),
                    ("Usable battery capacity", format_energy_wh(r.get("usable_battery_wh"))),
                ],
                title="Battery basis used in simulation",
            )

            st.markdown("### Battery charge vs discharge behavior")
            _render_charge_discharge_chart(r)

            worst_month_idx = 0
            empties = r.get("empty_battery_days_by_month") or [0] * 12
            if empties:
                worst_month_idx = max(range(min(12, len(empties))), key=lambda i: empties[i])

            gen_by_month = r.get("monthly_generation_wh_day") or [None] * 12
            out_by_day = r.get("avg_daily_energy_out_wh")

            _render_key_value_table(
                [
                    ("Lowest usable reserve reached", format_percent(r.get("lowest_usable_reserve_pct"), 1)),
                    ("Blackout days / year", str(int(blackout_days or 0))),
                    ("Worst month generated energy", f"{MONTHS[worst_month_idx]} — {format_energy_wh(gen_by_month[worst_month_idx] if worst_month_idx < len(gen_by_month) else None)}"),
                    ("Required energy", format_energy_wh(out_by_day)),
                ]
            )

            faa_ref = r.get("faa_reference", "FAA AC 150/5345-50B §3.4.2.2")
            faa3 = "Compliant" if r.get("faa_3sunhours_compliant") else "Not compliant"
            faa8 = "Compliant" if r.get("faa_8h_compliant") else "Not compliant"

            _render_key_value_table(
                [
                    ("FAA reference", faa_ref),
                    ("Energy available from 3 sun hours", format_energy_wh(r.get("faa_3sunhours_energy_wh"))),
                    ("Energy required for 8 hours at full intensity", format_energy_wh(r.get("faa_8h_required_wh"))),
                    ("FAA 3 sun-hours charge check", faa3),
                    ("FAA 8-hour operation check", faa8),
                ],
                title="FAA 3-sun-hour benchmark",
            )

            st.caption(
                "This benchmark shows whether the light can recover enough energy from 3 sun hours "
                "and whether its usable battery alone can support 8 hours of full-intensity operation."
            )
