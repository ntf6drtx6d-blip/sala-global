
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


def _render_charge_discharge_chart(result_row):
    weeks = result_row.get("weekly_labels") or []
    reserve = result_row.get("weekly_reserve_pct") or []
    charge = result_row.get("weekly_charge_pct") or []
    discharge = result_row.get("weekly_discharge_pct") or []
    charge_hr = result_row.get("weekly_charge_pct_per_hr") or []
    discharge_hr = result_row.get("weekly_discharge_pct_per_hr") or []
    reserve_start = result_row.get("weekly_reserve_start_pct") or reserve
    reserve_end = result_row.get("weekly_reserve_end_pct") or reserve
    deficit_flags = result_row.get("weekly_deficit_flags") or []

    if not weeks or not reserve or not charge or not discharge:
        st.info("Battery charge/discharge behavior is not available for this device.")
        return

    fig = go.Figure()

    # Background shading by deficit/surplus week
    for i, week in enumerate(weeks):
        is_deficit = bool(deficit_flags[i]) if i < len(deficit_flags) else False
        color = "rgba(239,68,68,0.10)" if is_deficit else "rgba(34,197,94,0.08)"
        fig.add_vrect(
            x0=i - 0.5,
            x1=i + 0.5,
            fillcolor=color,
            line_width=0,
            layer="below",
        )

    common_custom = list(zip(
        reserve_start,
        reserve_end,
        charge_hr if charge_hr else [0.0] * len(weeks),
        discharge_hr if discharge_hr else [0.0] * len(weeks),
    ))

    fig.add_trace(
        go.Bar(
            x=list(range(len(weeks))),
            y=charge,
            name="Recharge (%/day)",
            marker=dict(color="rgba(34,197,94,0.85)"),
            customdata=common_custom,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Recharge: +%{y:.1f}%/day<br>"
                "Approx. recharge rate: %{customdata[2]:.2f}%/h<br>"
                "Reserve: %{customdata[0]:.1f}% → %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
            text=weeks,
            offsetgroup="charge",
        )
    )

    fig.add_trace(
        go.Bar(
            x=list(range(len(weeks))),
            y=discharge,
            name="Discharge (%/day)",
            marker=dict(color="rgba(239,68,68,0.80)"),
            customdata=common_custom,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Discharge: -%{y:.1f}%/day<br>"
                "Approx. discharge rate: %{customdata[3]:.2f}%/h<br>"
                "Reserve: %{customdata[0]:.1f}% → %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
            text=weeks,
            offsetgroup="discharge",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=list(range(len(weeks))),
            y=reserve,
            mode="lines+markers",
            name="Usable battery reserve (%)",
            line=dict(width=3),
            marker=dict(size=6),
            customdata=common_custom,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Usable reserve: %{y:.1f}%<br>"
                "Recharge: +%{customdata[2]:.2f}%/h<br>"
                "Discharge: -%{customdata[3]:.2f}%/h<br>"
                "Reserve change: %{customdata[0]:.1f}% → %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
            text=weeks,
        )
    )

    zero_points_x = [i for i, v in enumerate(reserve) if float(v) <= 0.001]
    zero_points_y = [reserve[i] for i in zero_points_x]
    if zero_points_x:
        fig.add_trace(
            go.Scatter(
                x=zero_points_x,
                y=zero_points_y,
                mode="markers",
                name="Reserve exhausted",
                marker=dict(size=9, symbol="x"),
                hovertemplate="<b>%{text}</b><br>Usable reserve exhausted (0%)<extra></extra>",
                text=[weeks[i] for i in zero_points_x],
            )
        )

    tickvals = list(range(0, len(weeks), 4))
    ticktext = [weeks[i] for i in tickvals]

    fig.update_layout(
        title="Weekly usable battery reserve, recharge and discharge behavior",
        barmode="group",
        height=420,
        xaxis=dict(
            title="Week",
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
        ),
        yaxis=dict(
            title="Usable battery reserve (%)",
            range=[0, 100],
        ),
        legend=dict(orientation="h", y=1.12, x=0),
        margin=dict(l=20, r=20, t=70, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "0% on this chart means usable battery reserve is exhausted and the device has reached its operational cut-off threshold. "
        "Green weeks indicate that recharge is sufficient to recover or maintain reserve. "
        "Red weeks indicate a battery-deficit regime: the light consumes stored reserve faster than it is replenished."
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

            _render_key_value_table(
                [
                    ("Lowest usable reserve reached", format_percent(r.get("lowest_usable_reserve_pct"), 1)),
                    ("Weeks in battery-deficit regime", str(int(r.get("weeks_in_deficit", 0)))),
                    ("Average daily energy in", format_energy_wh(r.get("avg_daily_energy_in_wh"))),
                    ("Average daily energy out", format_energy_wh(r.get("avg_daily_energy_out_wh"))),
                    ("Average annual recharge rate", format_percent(r.get("avg_recharge_pct_per_hr"), 2) + "/h"),
                    ("Average annual discharge rate", format_percent(r.get("discharge_pct_per_hr"), 2) + "/h"),
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
