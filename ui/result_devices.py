# ui/result_devices.py

import textwrap
import streamlit as st

from ui.result_helpers import (
    battery_reserve_hours,
    device_blackout_days,
    format_achievable_hours,
    format_battery_hours,
    short_device_label,
    format_panel_azimuths,
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
                panels_text = f"{int(r.get('panel_count', len(panel_list) or 0))} × {_unique_panel_wp_text(panel_list)}"
                nominal_tilt_text = _unique_panel_tilt_text(panel_list)
                azimuth_text = format_panel_azimuths(panel_list)

                st.markdown("### Solar input used in simulation")

                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #e6eaf0;
                        border-radius:14px;
                        background:#ffffff;
                        padding:14px 16px;
                        margin-top:8px;
                        margin-bottom:12px;
                        box-shadow:0 2px 10px rgba(16,24,40,0.04);
                    ">
                        <div style="display:grid;grid-template-columns: minmax(220px, 280px) 1fr;row-gap:8px;column-gap:18px;">
                            <div style="color:#667085;font-weight:700;">Nominal multi-face PV</div>
                            <div style="color:#1f2937;">{_fmt_wp(nominal_wp)}</div>

                            <div style="color:#667085;font-weight:700;">Effective PV used in simulation</div>
                            <div style="color:#1f2937;">{_fmt_wp(effective_wp)}</div>

                            <div style="color:#667085;font-weight:700;">Effective PV as % of nominal</div>
                            <div style="color:#1f2937;">{_fmt_pct(effective_pct)}</div>

                            <div style="color:#667085;font-weight:700;">Equivalent PV tilt used in simulation</div>
                            <div style="color:#1f2937;">{float(equivalent_tilt):.0f}°</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("### Physical panel geometry")
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #e6eaf0;
                        border-radius:14px;
                        background:#ffffff;
                        padding:14px 16px;
                        margin-top:8px;
                        box-shadow:0 2px 10px rgba(16,24,40,0.04);
                    ">
                        <div style="display:grid;grid-template-columns: minmax(220px, 280px) 1fr;row-gap:8px;column-gap:18px;">
                            <div style="color:#667085;font-weight:700;">Configuration</div>
                            <div style="color:#1f2937;">{configuration}</div>

                            <div style="color:#667085;font-weight:700;">Panels</div>
                            <div style="color:#1f2937;">{panels_text}</div>

                            <div style="color:#667085;font-weight:700;">Nominal panel tilt(s)</div>
                            <div style="color:#1f2937;">{nominal_tilt_text}</div>

                            <div style="color:#667085;font-weight:700;">Nominal panel azimuth</div>
                            <div style="color:#1f2937;">{azimuth_text}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
