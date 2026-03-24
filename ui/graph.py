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
    """
    Battery-only reserve estimate.
    Assumes usable battery energy = 70% of nominal battery capacity.
    """
    try:
        batt = float(result_row["batt"])
        power = max(float(result_row["power"]), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def _extract_monthly_empty_battery_pct(result_row: dict):
    """
    Tries several possible keys for monthly empty-battery exposure.
    Expected: 12 values.
    """
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
            rows.append({
                "Month": month,
                "MonthIndex": i + 1,
                "Device": label,
                "EmptyBatteryPct": float(monthly_pct[i]),
                "EstimatedBlackoutDays": float(monthly_days[i]),
                "MonthDays": MONTH_DAYS[i],
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
    st.markdown("## Monthly empty-battery days")
    st.caption("Estimated number of days in each month when battery reserve reaches empty state.")

    blackout_df = build_blackout_df(results)

    if blackout_df.empty:
        st.info("Monthly empty-battery data is not available in the current simulation output.")
        return

    plot_df = blackout_df[blackout_df["Device"].isin(visible_devices)].copy()

    if plot_df.empty:
        st.info("No devices selected for display.")
        return

    zero_df = plot_df[plot_df["StatusBand"] == "zero"].copy()
    yellow_df = plot_df[plot_df["StatusBand"] == "near-threshold"].copy()
    red_df = plot_df[plot_df["StatusBand"] == "exposed"].copy()

    x_axis = alt.X(
        "MonthIndex:Q",
        scale=alt.Scale(domain=[0.5, 12.5]),
        axis=alt.Axis(
            title="Month",
            values=list(range(1, 13)),
            labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]"
        )
    )

    y_axis = alt.Y(
        "EstimatedBlackoutDays:Q",
        scale=alt.Scale(domain=[0, max(2, float(plot_df['EstimatedBlackoutDays'].max()) + 2)]),
        title="Estimated empty-battery days"
    )

    # green = 0 days/month
    green_rect = alt.Chart(zero_df).mark_rect(
        color="#16a34a",
        opacity=0.12
    ).encode(
        x=alt.X(
            "MonthStart:Q",
            scale=alt.Scale(domain=[0.5, 12.5]),
            axis=alt.Axis(
                title="Month",
                values=list(range(1, 13)),
                labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]"
            )
        ),
        x2="MonthEnd:Q",
        y=alt.value(0),
        y2=alt.value(0),
        detail="Device:N",
    )

    # yellow = >0 and <=1 day
    yellow_rect = alt.Chart(yellow_df).mark_rect(
        color="#f59e0b",
        opacity=0.18
    ).encode(
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        x2="MonthEnd:Q",
        y=alt.value(0),
        y2="EstimatedBlackoutDays:Q",
        detail="Device:N",
    )

    # red = >1 day
    red_rect = alt.Chart(red_df).mark_rect(
        color="#dc2626",
        opacity=0.15
    ).encode(
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        x2="MonthEnd:Q",
        y=alt.value(0),
        y2="EstimatedBlackoutDays:Q",
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
            alt.Tooltip("EstimatedBlackoutDays:Q", title="Estimated empty-battery days", format=".1f"),
            alt.Tooltip("EmptyBatteryPct:Q", title="Empty-battery exposure", format=".1f"),
            alt.Tooltip("MonthDays:Q", title="Days in month", format=".0f"),
            alt.Tooltip("Meaning:N", title="Interpretation"),
        ],
    )

    # target line at zero
    target_df = pd.DataFrame({
        "MonthIndex": list(range(1, 13)),
        "Target": [0] * 12,
    })

    target_line = alt.Chart(target_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=2.4
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Target:Q", scale=alt.Scale(domain=[0, max(2, float(plot_df['EstimatedBlackoutDays'].max()) + 2)])),
    )

    target_label_df = pd.DataFrame({
        "MonthIndex": [12],
        "Target": [0],
        "Text": ["Target = 0 empty-battery days/month"],
    })

    target_label = alt.Chart(target_label_df).mark_text(
        align="right",
        dx=-8,
        dy=-10,
        fontSize=12,
        fontWeight="bold",
        color="#111827"
    ).encode(
        x="MonthIndex:Q",
        y="Target:Q",
        text="Text:N",
    )

    chart = (
        red_rect
        + yellow_rect
        + green_rect
        + line_chart
        + target_line
        + target_label
    ).properties(
        height=360
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        """
        <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:0.95rem;color:#475467;">
            <div><span style="display:inline-block;width:14px;height:14px;background:#16a34a;opacity:0.7;border-radius:3px;margin-right:6px;"></span>0 days in month</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#f59e0b;opacity:0.7;border-radius:3px;margin-right:6px;"></span>Up to 1 day in month</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#dc2626;opacity:0.7;border-radius:3px;margin-right:6px;"></span>More than 1 day in month</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Estimated monthly values are derived from monthly empty-battery exposure and the number of days in each calendar month."
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

    # NEW GRAPH ABOVE
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
        scale=alt.Scale(domain=[0.5, 12.5]),
        axis=alt.Axis(
            title="Month",
            values=list(range(1, 13)),
            labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]"
        )
    )

    y_axis = alt.Y(
        "Hours:Q",
        scale=alt.Scale(domain=[0, 24]),
        title="Achieved operating hours per day"
    )

    green_rect = alt.Chart(green_df).mark_rect(
        color="#16a34a",
        opacity=0.15
    ).encode(
        x=alt.X(
            "MonthStart:Q",
            scale=alt.Scale(domain=[0.5, 12.5]),
            axis=alt.Axis(
                title="Month",
                values=list(range(1, 13)),
                labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]"
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
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        x2="MonthEnd:Q",
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        y2="RequiredHours:Q",
        detail="Device:N",
    )

    red_rect = alt.Chart(red_df).mark_rect(
        color="#dc2626",
        opacity=0.15
    ).encode(
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0.5, 12.5])),
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
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Required:Q", title="Required hours", format=".1f")
        ],
    )

    label_df = pd.DataFrame({
        "MonthIndex": [12],
        "Required": [required_hours],
        "Text": [f"Required daily operation = {required_hours:.1f} hrs/day"],
    })

    label_chart = alt.Chart(label_df).mark_text(
        align="right",
        dx=-8,
        dy=-10,
        fontSize=12,
        fontWeight="bold",
        color="#111827"
    ).encode(
        x="MonthIndex:Q",
        y="Required:Q",
        text="Text:N",
    )

    chart = (
        red_rect
        + yellow_rect
        + green_rect
        + line_chart
        + req_line
        + label_chart
    ).properties(
        height=500
    ).interactive()

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
