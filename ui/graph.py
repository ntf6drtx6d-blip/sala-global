print("UI GRAPH MODULE LOADED")

import altair as alt
import pandas as pd
import streamlit as st


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def short_device_label(full_name: str) -> str:
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def calc_battery_reserve_hours(result_row: dict):
    try:
        batt = float(result_row["batt"])
        power = max(float(result_row["power"]), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def _extract_monthly_empty_battery_pct(result_row: dict):
    candidates = [
        result_row.get("monthly_empty_battery_pct"),
        result_row.get("empty_battery_pct_by_month"),
        result_row.get("monthly_blackout_pct"),
        result_row.get("blackout_pct_by_month"),
        result_row.get("monthly_empty_pct"),
    ]

    for candidate in candidates:
        if isinstance(candidate, (list, tuple)) and len(candidate) == 12:
            try:
                return [float(x) for x in candidate]
            except Exception:
                pass

    return None


def _monthly_blackout_days_from_pct(monthly_pct):
    return [
        round((pct / 100.0) * days, 1)
        for pct, days in zip(monthly_pct, MONTH_DAYS)
    ]


def build_blackout_df(results: dict) -> pd.DataFrame:
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)
        monthly_pct = _extract_monthly_empty_battery_pct(r)

        if not monthly_pct:
            continue

        monthly_days = _monthly_blackout_days_from_pct(monthly_pct)

        for i, month in enumerate(MONTHS):
            days_val = float(monthly_days[i])

            if days_val <= 0:
                status_band = "zero"
            elif days_val <= 3:
                status_band = "near-threshold"
            else:
                status_band = "exposed"

            rows.append({
                "Month": month,
                "MonthIndex": i + 1,
                "MonthStart": i + 0.55,
                "MonthEnd": i + 1.45,
                "Device": label,
                "EmptyBatteryPct": float(monthly_pct[i]),
                "EstimatedBlackoutDays": days_val,
                "MonthDays": MONTH_DAYS[i],
                "StatusBand": status_band,
                "Meaning": (
                    f"Estimated days with battery at 0% in {month}: {days_val:.1f}. "
                    f"Share of month with empty battery: {float(monthly_pct[i]):.1f}%. "
                    f"Evaluated against the selected airport lighting requirement. "
                    f"Calendar month length: {MONTH_DAYS[i]} days."
                ),
            })

    return pd.DataFrame(rows)


def build_monthly_df(results: dict, required_hrs: float) -> pd.DataFrame:
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)
        reserve = calc_battery_reserve_hours(r)

        for i, month in enumerate(MONTHS):
            hours = float(r["hours"][i])
            required = float(required_hrs)
            gap = hours - required

            status_band = "met"
            if gap < 0:
                status_band = "near-threshold" if abs(gap) < 0.5 else "below"

            if reserve is not None:
                meaning = (
                    f"Required: {required:.1f} hrs/day. "
                    f"Achieved in {month}: {hours:.1f} hrs/day. "
                    f"Gap: {gap:+.1f} hrs/day. "
                    f"Battery reserve: {reserve:.1f} hrs."
                )
            else:
                meaning = (
                    f"Required: {required:.1f} hrs/day. "
                    f"Achieved in {month}: {hours:.1f} hrs/day. "
                    f"Gap: {gap:+.1f} hrs/day."
                )

            rows.append({
                "Month": month,
                "MonthIndex": i + 1,
                "MonthStart": i + 0.55,
                "MonthEnd": i + 1.45,
                "Device": label,
                "Hours": hours,
                "RequiredHours": required,
                "Gap": gap,
                "BatteryReserve": reserve,
                "StatusBand": status_band,
                "Meaning": meaning,
            })

    return pd.DataFrame(rows)


def render_blackout_graph(results: dict, visible_devices: list[str]):
    required_hours = float(st.session_state.get("required_hours", 0))
    try:
        from ui.result_helpers import operating_window_example
        window_text = operating_window_example(required_hours)
    except Exception:
        window_text = ""

    st.markdown("## Monthly 0% battery days by device")
    st.caption(
        f"Shows, for each selected device, how many days per month the battery is expected to reach 0% "
        f"under the selected airport lighting requirement of {required_hours:.0f} hrs/day"
        + (f" ({window_text})" if window_text else "")
        + "."
    )

    blackout_df = build_blackout_df(results)

    if blackout_df.empty:
        st.info("Monthly empty-battery data is not available in the current simulation output.")
        return

    plot_df = blackout_df[blackout_df["Device"].isin(visible_devices)].copy()

    if plot_df.empty:
        st.info("No devices selected for display.")
        return

    plot_df["Severity"] = plot_df["EstimatedBlackoutDays"].apply(
        lambda d: "0 days"
        if d <= 0
        else "1–3 days"
        if d <= 3
        else "3+ days"
    )

    y_max = 31

    tooltip_fields = [
        alt.Tooltip("Device:N", title="Device"),
        alt.Tooltip("Month:N", title="Month"),
        alt.Tooltip("EstimatedBlackoutDays:Q", title="0% battery days", format=".1f"),
        alt.Tooltip("EmptyBatteryPct:Q", title="Share of month with empty battery", format=".1f"),
        alt.Tooltip("MonthDays:Q", title="Days in month", format=".0f"),
        alt.Tooltip("Meaning:N", title="Interpretation"),
    ]

    bars = alt.Chart(plot_df).mark_bar(size=22).encode(
        x=alt.X(
            "Month:N",
            sort=MONTHS,
            axis=alt.Axis(title="Month", labelAngle=0),
        ),
        xOffset=alt.XOffset("Device:N"),
        y=alt.Y(
            "EstimatedBlackoutDays:Q",
            scale=alt.Scale(domain=[0, y_max]),
            title="Days",
        ),
        color=alt.Color(
            "Device:N",
            legend=alt.Legend(title="Device"),
        ),
        opacity=alt.condition(
            alt.datum.EstimatedBlackoutDays > 0,
            alt.value(0.9),
            alt.value(0.35)
        ),
        tooltip=tooltip_fields,
    )

    zero_line_df = pd.DataFrame({
        "Month": MONTHS,
        "Target": [0] * 12,
    })

    zero_line = alt.Chart(zero_line_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=2.0
    ).encode(
        x=alt.X("Month:N", sort=MONTHS),
        y=alt.Y("Target:Q", scale=alt.Scale(domain=[0, y_max])),
    )

    zero_label_df = pd.DataFrame({
        "Month": ["Dec"],
        "Target": [0],
        "Text": ["Target = 0 days"],
    })

    zero_label = alt.Chart(zero_label_df).mark_text(
        align="right",
        dx=-8,
        dy=-10,
        fontSize=12,
        fontWeight="bold",
        color="#111827"
    ).encode(
        x=alt.X("Month:N", sort=MONTHS),
        y=alt.Y("Target:Q", scale=alt.Scale(domain=[0, y_max])),
        text="Text:N",
    )

    chart = (
        (bars + zero_line + zero_label)
        .properties(height=360)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#667085",
            titleColor="#667085",
            gridColor="#eaecf0",
        )
        .configure_legend(
            orient="bottom",
            titleColor="#475467",
            labelColor="#475467",
        )
    )

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        f"Any value above 0 indicates expected full battery depletion on at least some days in that month "
        f"under the selected airport lighting requirement of {required_hours:.0f} hrs/day."
    )


def render_graph():
    results = st.session_state.get("results", {})
    if not results:
        return

    required_hours = float(st.session_state.get("required_hours", 0))
    chart_df = build_monthly_df(results, required_hours)
    device_labels = list(chart_df["Device"].unique())

    visible_devices = st.multiselect(
        "Devices shown on graph",
        device_labels,
        default=device_labels,
        help="Untick devices to hide them from the graphs.",
        key="graph_devices_filter",
    )

    render_blackout_graph(results, visible_devices)

    st.markdown("## Annual operating profile")
    st.caption("12-month solar performance from January to December.")

    plot_df = chart_df[chart_df["Device"].isin(visible_devices)].copy()

    if plot_df.empty:
        st.info("No devices selected for display.")
        return

    green_df = plot_df[plot_df["StatusBand"] == "met"].copy()
    yellow_df = plot_df[plot_df["StatusBand"] == "near-threshold"].copy()
    red_df = plot_df[plot_df["StatusBand"] == "below"].copy()

    x_axis = alt.X(
        "MonthIndex:Q",
        scale=alt.Scale(domain=[0, 12.5]),
        axis=alt.Axis(
            title="Month",
            values=list(range(1, 13)),
            labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]",
            labelAngle=0,
            domain=True,
            domainWidth=2,
            tickWidth=2,
            tickSize=6,
            labelPadding=8,
        )
    )

    y_axis = alt.Y(
        "Hours:Q",
        scale=alt.Scale(domain=[0, 24]),
        axis=alt.Axis(
            title="Achieved operating hours per day",
            domain=True,
            domainWidth=2,
            tickWidth=2,
            tickSize=6,
            grid=True,
            labelPadding=6,
        ),
    )

    green_rect = alt.Chart(green_df).mark_rect(
        color="#16a34a",
        opacity=0.15
    ).encode(
        x=alt.X(
            "MonthStart:Q",
            scale=alt.Scale(domain=[0, 12.5]),
            axis=alt.Axis(
                title="Month",
                values=list(range(1, 13)),
                labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]",
                labelAngle=0,
            )
        ),
        x2="MonthEnd:Q",
        y=alt.Y(
            "RequiredHours:Q",
            scale=alt.Scale(domain=[0, 24]),
            title="Achieved operating hours per day"
        ),
        y2="Hours:Q",
        detail="Device:N",
    )

    yellow_rect = alt.Chart(yellow_df).mark_rect(
        color="#f59e0b",
        opacity=0.18
    ).encode(
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0, 12.5])),
        x2="MonthEnd:Q",
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        y2="RequiredHours:Q",
        detail="Device:N",
    )

    red_rect = alt.Chart(red_df).mark_rect(
        color="#dc2626",
        opacity=0.15
    ).encode(
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0, 12.5])),
        x2="MonthEnd:Q",
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        y2="RequiredHours:Q",
        detail="Device:N",
    )

    line_chart = alt.Chart(plot_df).mark_line(
        point=True,
        strokeWidth=2.8
    ).encode(
        x=x_axis,
        y=y_axis,
        color=alt.Color(
            "Device:N",
            title="Selected devices",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="top-right"),
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("RequiredHours:Q", title="Required hours", format=".1f"),
            alt.Tooltip("Hours:Q", title="Achieved hours", format=".1f"),
            alt.Tooltip("Gap:Q", title="Gap vs requirement", format="+.1f"),
            alt.Tooltip("BatteryReserve:Q", title="Battery reserve", format=".1f"),
            alt.Tooltip("Meaning:N", title="Interpretation"),
        ],
    )

    req_df = pd.DataFrame({
        "MonthIndex": list(range(1, 13)),
        "Required": [required_hours] * 12,
    })

    req_line = alt.Chart(req_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=3.0
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Required:Q", title="Required hours", format=".1f")
        ],
    )

    zero_df = pd.DataFrame({
        "MonthIndex": [0, 12.5],
        "Zero": [0, 0],
    })

    zero_line = alt.Chart(zero_df).mark_line(
        color="#475467",
        strokeWidth=1.6
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("Zero:Q", scale=alt.Scale(domain=[0, 24])),
    )

    req_connector_df = pd.DataFrame({
        "x": [0.2, 0.2],
        "y": [0, required_hours],
    })

    req_connector = alt.Chart(req_connector_df).mark_line(
        color="#111827",
        strokeWidth=2.2
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 24])),
    )

    req_label_df = pd.DataFrame({
        "MonthIndex": [0.35],
        "Required": [required_hours],
        "Text": [f"{required_hours:.1f} hrs/day required"],
    })

    req_label = alt.Chart(req_label_df).mark_text(
        align="left",
        dx=8,
        dy=-8,
        fontSize=12,
        fontWeight="bold",
        color="#111827"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    req_icon_df = pd.DataFrame({
        "MonthIndex": [0.2],
        "Required": [required_hours],
        "Icon": ["✈"],
    })

    req_icon = alt.Chart(req_icon_df).mark_text(
        align="center",
        baseline="middle",
        dx=0,
        dy=-18,
        fontSize=15,
        color="#111827"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Icon:N",
    )

    zero_label_df = pd.DataFrame({
        "MonthIndex": [0.35],
        "Zero": [0],
        "Text": ["0 hrs/day"],
    })

    zero_label = alt.Chart(zero_label_df).mark_text(
        align="left",
        dx=8,
        dy=12,
        fontSize=11,
        color="#475467"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("Zero:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    chart_note_df = pd.DataFrame({
        "MonthIndex": [6.5],
        "Hours": [23.2],
        "Text": ["Dashed line = required airport lighting operation"],
    })

    chart_note = alt.Chart(chart_note_df).mark_text(
        align="center",
        fontSize=11,
        color="#344054"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0, 12.5])),
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    chart = (
        green_rect
        + yellow_rect
        + red_rect
        + zero_line
        + req_connector
        + req_line
        + line_chart
        + req_icon
        + req_label
        + zero_label
        + chart_note
    ).properties(
        height=500
    ).interactive().configure_axis(
        labelFontSize=12,
        titleFontSize=13,
        gridColor="#E5E7EB",
        gridOpacity=0.8,
    ).configure_view(
        stroke="#D0D5DD",
        strokeWidth=1.2,
        clip=False
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        """
        <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:0.95rem;color:#475467;">
            <div><span style="display:inline-block;width:14px;height:14px;background:#16a34a;opacity:0.7;border-radius:3px;margin-right:6px;"></span>Requirement met</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#f59e0b;opacity:0.7;border-radius:3px;margin-right:6px;"></span>Near threshold (&lt; 0.5 hrs/day shortfall)</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#dc2626;opacity:0.7;border-radius:3px;margin-right:6px;"></span>Below requirement</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Hover any point to compare required hours, achieved hours, gap versus requirement, and battery reserve. "
        "Battery reserve means battery-only fallback capability without solar input."
    )
