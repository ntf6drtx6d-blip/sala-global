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
            days_val = float(monthly_days[i])

            if days_val <= 0:
                status_band = "zero"
            elif days_val <= 1:
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
                    f"Estimated empty-battery days in {month}: {days_val:.1f}. "
                    f"Empty-battery exposure: {float(monthly_pct[i]):.1f}% of the month. "
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
    st.markdown("## Monthly empty-battery days")
    st.caption("Estimated days per month with battery at 0%.")

    blackout_df = build_blackout_df(results)

    if blackout_df.empty:
        st.info("Monthly empty-battery data is not available in the current simulation output.")
        return

    plot_df = blackout_df[blackout_df["Device"].isin(visible_devices)].copy()

    if plot_df.empty:
        st.info("No devices selected for display.")
        return

    y_max = 31

    for device in visible_devices:
        device_df = plot_df[plot_df["Device"] == device].copy()
        if device_df.empty:
            continue

        st.markdown(f"**{device}**")

        device_df["Severity"] = device_df["EstimatedBlackoutDays"].apply(
            lambda d: "0 days"
            if d <= 0
            else "Up to 3 days"
            if d <= 3
            else "More than 3 days"
        )

        x_axis = alt.X(
            "Month:N",
            sort=MONTHS,
            axis=alt.Axis(title="Month", labelAngle=0)
        )

        y_axis = alt.Y(
            "EstimatedBlackoutDays:Q",
            scale=alt.Scale(domain=[0, y_max]),
            title="Days"
        )

        tooltip_fields = [
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("EstimatedBlackoutDays:Q", title="Days with battery at 0%", format=".1f"),
            alt.Tooltip("EmptyBatteryPct:Q", title="Battery at 0% exposure", format=".1f"),
            alt.Tooltip("MonthDays:Q", title="Days in month", format=".0f"),
            alt.Tooltip("Meaning:N", title="Interpretation"),
        ]

        bars = alt.Chart(device_df).mark_bar(
            opacity=0.22,
            size=42
        ).encode(
            x=x_axis,
            y=y_axis,
            color=alt.Color(
                "Severity:N",
                scale=alt.Scale(
                    domain=["0 days", "Up to 3 days", "More than 3 days"],
                    range=["#e5e7eb", "#f59e0b", "#dc2626"],
                ),
                legend=None,
            ),
            tooltip=tooltip_fields,
        )

        line_chart = alt.Chart(device_df).mark_line(
            point=True,
            strokeWidth=2.8,
            color="#5b7aa6"
        ).encode(
            x=x_axis,
            y=alt.Y(
                "EstimatedBlackoutDays:Q",
                scale=alt.Scale(domain=[0, y_max]),
                title="Days"
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

        chart = (bars + line_chart + zero_line + zero_label).properties(
            height=230
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

    st.markdown(
        """
        <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:0.95rem;color:#475467;">
            <div><span style="display:inline-block;width:14px;height:14px;background:#e5e7eb;border-radius:3px;margin-right:6px;border:1px solid #cbd5e1;"></span>0 days</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#f59e0b;opacity:0.7;border-radius:3px;margin-right:6px;"></span>1–3 days</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#dc2626;opacity:0.7;border-radius:3px;margin-right:6px;"></span>More than 3 days</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "This chart shows in which months the battery is expected to reach 0%, and for how many days."
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
