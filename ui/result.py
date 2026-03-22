# ui/result.py

import math
import textwrap

import folium
import streamlit as st
from streamlit_folium import st_folium


def format_required_hours(hours: float) -> str:
    return f"{math.ceil(float(hours))} hrs/day"


def format_achievable_hours(hours: float) -> str:
    return f"{math.floor(float(hours))} hrs/day"


def format_battery_hours(hours: float) -> str:
    h = float(hours)
    whole = int(h)
    minutes = int(round((h - whole) * 60))
    if minutes == 60:
        whole += 1
        minutes = 0
    if minutes == 0:
        return f"{whole}h"
    return f"{whole}h {minutes:02d}m"


def operating_mode_name() -> str:
    mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
    if mode == "24/7":
        return "24/7 operation"
    if mode == "Dusk to dawn":
        return "Dusk-to-Dawn"
    return "Custom operation"


def operating_window_example(hours_value: float) -> str:
    h = max(0.0, min(float(hours_value), 24.0))
    if h >= 24:
        return "00:00–24:00"

    end_hour = 6.0
    start_hour = (end_hour - h) % 24

    def fmt(x: float) -> str:
        whole = int(x) % 24
        minutes = int(round((x - int(x)) * 60))
        if minutes == 60:
            whole = (whole + 1) % 24
            minutes = 0
        return f"{whole:02d}:{minutes:02d}"

    return f"{fmt(start_hour)}–{fmt(end_hour)}"


def short_device_label(full_name: str) -> str:
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def annual_empty_battery_stats(results: dict):
    pcts = []
    for _, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is not None:
            try:
                pcts.append(float(pct))
            except Exception:
                pass

    if not pcts:
        return None, None

    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100.0)
    return worst_days, worst_pct
def worst_sustainable_hours(results: dict):
    mins = []
    for _, r in results.items():
        hours = r.get("hours", [])
        if hours:
            try:
                mins.append(min(float(x) for x in hours))
            except Exception:
                pass

    if not mins:
        return None

    return min(mins)

def count_device_statuses(results: dict):
    total = len(results)
    passed = 0
    failed = 0

    for _, r in results.items():
        if r.get("status") == "PASS":
            passed += 1
        else:
            failed += 1

    return total, passed, failed


def overall_state(results: dict) -> str:
    total, passed, failed = count_device_statuses(results)

    if total == 0:
        return "unknown"
    if passed == total:
        return "all_pass"
    if failed == total:
        return "none_pass"
    return "mixed"


def overall_conclusion_text(results: dict) -> str:
    state = overall_state(results)

    if state == "all_pass":
        return "All selected devices meet the required operating profile."
    if state == "none_pass":
        return "None of the selected devices meet the required operating profile."
    if state == "mixed":
        return "Mixed result across selected devices."
    return "The selected device set could not be fully assessed."


def overall_interpretation_text(results: dict) -> str:
    total, passed, failed = count_device_statuses(results)
    days, pct = annual_empty_battery_stats(results)
    state = overall_state(results)

    if state == "all_pass":
        return "All selected devices support the selected operating profile year-round."

    if state == "none_pass":
        if days is None or pct is None:
            return "No selected device supports the selected operating profile year-round."
        return (
            f"No selected device supports the selected operating profile year-round. "
            f"The highest blackout risk within the selected set is {days} days/year ({pct:.1f}%)."
        )

    if state == "mixed":
        line_1 = f"{passed} of {total} selected devices meet the requirement. {failed} devices remain below requirement."
        if days is None or pct is None:
            return line_1
        return (
            f"{line_1} The overall set is treated as not fully compliant because at least one selected device "
            f"remains below requirement. Worst-device blackout risk is {days} days/year ({pct:.1f}%)."
        )

    return "The selected device set could not be fully assessed."


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


def render_airport_name_box(airport_name: str):
    html = textwrap.dedent(
        """
        <div style="
            border:1px solid #e6eaf0;
            border-radius:14px;
            padding:14px 16px;
            background:#ffffff;
            box-shadow:0 2px 10px rgba(16,24,40,0.04);
            margin-bottom:14px;">
            <div style="font-size:0.88rem;color:#667085;font-weight:700;margin-bottom:6px;">Airport / study point</div>
            <div style="font-size:1.35rem;color:#1f2937;font-weight:900;line-height:1.15;">{airport_name}</div>
        </div>
        """
    ).format(airport_name=airport_name)
    st.markdown(html, unsafe_allow_html=True)


def render_required_time_card(hours_value: float, mode_text: str):
    rounded_hours = math.ceil(float(hours_value))
    window_text = operating_window_example(hours_value)
    pct = max(0, min(100, (float(hours_value) / 24.0) * 100))

    html = (
        f'<div style="border:1px solid #e6eaf0;border-radius:16px;padding:18px 20px;'
        f'background:#ffffff;min-height:230px;box-shadow:0 2px 10px rgba(16,24,40,0.04);">'
        f'<div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">'
        f'Airport lighting requirement</div>'
        f'<div style="font-size:2.2rem;color:#1f2937;font-weight:900;line-height:1.05;">'
        f'{rounded_hours} hrs/day</div>'
        f'<div style="font-size:1rem;color:#667085;margin-top:8px;">{mode_text}</div>'
        f'<div style="margin-top:16px;">'
        f'<div style="font-size:0.88rem;color:#475467;font-weight:700;margin-bottom:8px;">'
        f'Required daily lighting window</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#667085;margin-bottom:6px;">'
        f'<span>00:00</span><span>24:00</span></div>'
        f'<div style="position:relative;width:100%;height:12px;background:#eef2f6;border-radius:999px;overflow:hidden;">'
        f'<div style="width:{pct:.1f}%;height:100%;background:#1f4fbf;border-radius:999px;"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:flex-end;margin-top:8px;">'
        f'<span style="font-size:0.88rem;color:#1f4fbf;font-weight:800;background:#eef4ff;'
        f'padding:4px 10px;border-radius:999px;">{rounded_hours} h</span>'
        f'</div>'
        f'<div style="font-size:0.88rem;color:#667085;margin-top:8px;">'
        f'Example operating window: {window_text}</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_meeting_devices_card(results: dict):
    total, passed, _ = count_device_statuses(results)
    bg = "#ecfdf3" if passed == total and total > 0 else "#ffffff"
    border = "#abefc6" if passed == total and total > 0 else "#e6eaf0"
    color = "#067647" if passed == total and total > 0 else "#1f2937"

    render_kpi_card(
        "Devices meeting requirement",
        f"{passed} / {total}",
        "Selected devices that support the required operating profile year-round.",
        bg=bg,
        border=border,
        color=color,
        min_height=220,
    )


def render_below_requirement_devices_card(results: dict):
    total, _, failed = count_device_statuses(results)
    bg = "#fef3f2" if failed > 0 else "#ecfdf3"
    border = "#fecdca" if failed > 0 else "#abefc6"
    color = "#b42318" if failed > 0 else "#067647"

    render_kpi_card(
        "Devices below requirement",
        f"{failed} / {total}",
        "Selected devices that remain below the required operating profile.",
        bg=bg,
        border=border,
        color=color,
        min_height=220,
    )


def render_blackout_card(days_value, pct_value):
    if days_value is None or pct_value is None:
        main = "N/A"
        secondary = "Worst-device blackout risk not available"
        bg = "#ffffff"
        border = "#e6eaf0"
        color = "#1f2937"
    else:
        main = f"{days_value} days/year"
        secondary = f"{pct_value:.1f}% of the year"
        if int(days_value) == 0:
            bg = "#ecfdf3"
            border = "#abefc6"
            color = "#067647"
        else:
            bg = "#fef3f2"
            border = "#fecdca"
            color = "#b42318"

    html = (
        f'<div style="border:1px solid {border};border-radius:16px;padding:18px 20px;'
        f'background:{bg};min-height:220px;box-shadow:0 2px 10px rgba(16,24,40,0.04);">'
        f'<div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">'
        f'Worst device blackout risk</div>'
        f'<div style="font-size:2.2rem;color:{color};font-weight:900;line-height:1.05;">'
        f'{main}</div>'
        f'<div style="font-size:1rem;color:#667085;margin-top:10px;">{secondary}</div>'
        f'<div style="font-size:0.9rem;color:#475467;margin-top:12px;line-height:1.45;">'
        f'Highest blackout exposure found within the selected device set.'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_location_map(lat: float, lon: float, airport_name: str):
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=10,
        control_scale=True,
        tiles="CartoDB positron",
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

    st_folium(
        fmap,
        width=None,
        height=320,
        returned_objects=[],
        key="result_location_map",
    )


def render_explanation_blocks(results: dict):
    days, pct = annual_empty_battery_stats(results)
    sustainable = worst_sustainable_hours(results)
    state = overall_state(results)
    total, passed, failed = count_device_statuses(results)

    if days is None or pct is None:
        meaning_value = "Review needed"
        meaning_text = "The annual blackout risk could not be calculated for the selected operating profile."
        meaning_bg = "#fff7db"
        meaning_border = "#f5c451"
        meaning_color = "#7a5a00"
        action_value = "Review setup"
        action_text = "Review the selected inputs and rerun the study."
    elif state == "all_pass":
        meaning_value = "All devices supported"
        meaning_text = "All selected devices support the required operating profile throughout the year."
        meaning_bg = "#ecfdf3"
        meaning_border = "#abefc6"
        meaning_color = "#067647"
        action_value = "No change required"
        action_text = "Configuration can be used as selected."
    elif state == "none_pass":
        meaning_value = "No devices supported"
        meaning_text = (
            f"No selected device supports the required operating profile year-round. "
            f"Worst-device blackout risk is {days} days/year ({pct:.1f}%)."
        )
        meaning_bg = "#fef3f2"
        meaning_border = "#fecdca"
        meaning_color = "#b42318"
        action_value = "Adjust setup"
        action_text = "Reduce daily operating hours or strengthen the configuration."
    else:
        meaning_value = "Mixed result"
        meaning_text = (
            f"{passed} of {total} selected devices meet the requirement. "
            f"{failed} devices remain below requirement."
        )
        meaning_bg = "#fff7db"
        meaning_border = "#f5c451"
        meaning_color = "#7a5a00"
        action_value = "Review failing devices"
        action_text = "Keep compliant devices as selected and review the devices that remain below requirement."

    c1, c2, c3 = st.columns(3)

    with c1:
        render_kpi_card(
            "What this result means",
            meaning_value,
            meaning_text,
            bg=meaning_bg,
            border=meaning_border,
            color=meaning_color,
            min_height=200,
        )

    with c2:
        value = format_achievable_hours(sustainable) if sustainable is not None else "N/A"
        subtitle = (
            "Lowest daily operating time the weakest device can sustain continuously during the weakest solar period."
            if sustainable is not None
            else "Could not be calculated."
        )
        render_kpi_card(
            "Lowest sustainable operation in set",
            value,
            subtitle,
            min_height=200,
        )

    with c3:
        render_kpi_card(
            "Recommended action",
            action_value,
            action_text,
            min_height=200,
        )


def battery_reserve_hours(result_row: dict):
    try:
        batt = float(result_row.get("batt", 0))
        power = max(float(result_row.get("power", 0.01)), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def device_status_chip(status: str):
    if status == "PASS":
        return '<span style="background:#ecfdf3;color:#067647;border:1px solid #abefc6;padding:4px 10px;border-radius:999px;font-size:0.82rem;font-weight:800;">Meets requirement</span>'
    return '<span style="background:#fef3f2;color:#b42318;border:1px solid #fecdca;padding:4px 10px;border-radius:999px;font-size:0.82rem;font-weight:800;">Below requirement</span>'


def render_device_capability_cards(results: dict):
    st.markdown("## Operating requirement vs energy capability")

    required = float(st.session_state.get("required_hours", 0))

    for device_name, r in results.items():
        label = short_device_label(device_name)
        hours = r.get("hours", [])
        achievable = min(hours) if hours else None
        reserve = battery_reserve_hours(r)

        req_text = format_required_hours(required)
        ach_text = format_achievable_hours(achievable) if achievable is not None else "N/A"
        reserve_text = format_battery_hours(reserve) if reserve is not None else "N/A"

        status_html = device_status_chip(r.get("status", "FAIL"))

        st.markdown(
            f"""
            <div style="margin-top:18px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">
                <div style="font-size:1.05rem;font-weight:900;color:#1f2937;">{label}</div>
                <div>{status_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            render_kpi_card(
                "Required operation",
                req_text,
                "What the airport needs",
                min_height=155,
            )

        with c2:
            render_kpi_card(
                "Achievable (worst month)",
                ach_text,
                "Lowest guaranteed month",
                min_height=155,
            )

        with c3:
            render_kpi_card(
                "Battery-only reserve",
                reserve_text,
                "No-sun fallback capability",
                min_height=155,
            )

        if achievable is not None and reserve is not None:
            note = (
                f"The airport requires {required:.1f} hrs/day. "
                f"For {label}, the lowest sustainable result during the year is {achievable:.1f} hrs/day. "
                f"Battery-only reserve is approximately {reserve:.1f} hrs. "
            )
            if r.get("status") == "PASS":
                note += "This device remains above the required operating profile throughout the full annual cycle."
            else:
                note += "This device falls below the required operating profile during part of the year."
        else:
            note = "Device-level operating capability could not be fully calculated."

        st.markdown(
            f"""
            <div style="
                border-left:4px solid #3b5ccc;
                background:#f8fafc;
                padding:14px 16px;
                border-radius:10px;
                margin-top:10px;
                margin-bottom:8px;
                color:#344054;
                line-height:1.6;">
                {note}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.get("results", {})
    if not results:
        return

    state = overall_state(results)
    days, pct = annual_empty_battery_stats(results)
    total, passed, failed = count_device_statuses(results)

    airport_name = st.session_state.get("airport_label", "") or "Selected study point"
    required_hours = float(st.session_state.get("required_hours", 0))
    mode_name = operating_mode_name()
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
        render_airport_name_box(airport_name)
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
                    Overall conclusion
                </div>
                <div style="font-size:2rem;line-height:1.2;font-weight:800;color:{box_fg};margin-bottom:12px;">
                    {headline}
                </div>
                <div style="font-size:1rem;color:#475467;">
                    {subtext}
                </div>
            </div>
            """
        ).format(
            border=border,
            box_bg=box_bg,
            box_fg=box_fg,
            headline=overall_conclusion_text(results),
            subtext=overall_interpretation_text(results),
        )

        st.markdown(summary_html, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            render_required_time_card(required_hours, mode_name)
        with c2:
            render_blackout_card(days, pct)

        c3, c4 = st.columns(2)
        with c3:
            render_meeting_devices_card(results)
        with c4:
            render_below_requirement_devices_card(results)

    st.markdown("### What this means")
    render_explanation_blocks(results)

    render_device_capability_cards(results)
