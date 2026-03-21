# ui/battery.py
# ACTION: REPLACE ENTIRE FILE

import pandas as pd
import altair as alt
import streamlit as st

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def calc_battery_reserve_hours(result_row):
    """
    Battery reserve = usable battery energy / consumption
    Usable battery assumed at 70%
    """
    batt = float(result_row["batt"])
    power = max(float(result_row["power"]), 0.01)
    return batt * 0.70 / power


def build_empty_battery_df(results):
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)
        monthly_days = r.get("empty_battery_days_by_month") or [0] * 12
        monthly_pct = r.get("empty_battery_pct_by_month") or [0] * 12

        for i, month in enumerate(MONTHS):
            rows.append({
                "Device": label,
                "Month": month,
                "MonthIndex": i + 1,
                "EmptyBatteryDays": int(monthly_days[i]),
                "EmptyBatteryPct": float(monthly_pct[i]),
            })

    return pd.DataFrame(rows)


def render_battery():
    st.markdown("## Empty battery risk by month")

    st.caption(
        "This section shows how many days in each month the battery would become fully discharged "
        "for the selected operating mode."
    )

    results = st.session_state.get("results", {})
    required_hours = float(st.session_state.get("required_hours", 12.0))

    if not results:
        return

    df = build_empty_battery_df(results)
    device_labels = list(df["Device"].unique())

    visible_devices = st.multiselect(
        "Devices shown in battery-risk chart",
        device_labels,
        default=device_labels,
        help="Untick devices to hide them from the chart.",
        key="battery_devices_filter"
    )

    plot_df = df[df["Device"].isin(visible_devices)].copy()

    # Summary cards per device
    st.markdown("### Device summary")

    for device_name, r in results.items():
        label = short_device_label(device_name)
        if label not in visible_devices:
            continue

        reserve = calc_battery_reserve_hours(r)
        monthly_days = r.get("empty_battery_days_by_month") or [0] * 12
        monthly_pct = r.get("empty_battery_pct_by_month") or [0] * 12

        worst_idx = max(range(12), key=lambda i: monthly_days[i])
        worst_days = monthly_days[worst_idx]
        worst_pct = monthly_pct[worst_idx]
        worst_month = MONTHS[worst_idx]

        total_days = sum(monthly_days)

        c1, c2, c3, c4 = st.columns([1.4, 1.1, 1.2, 1.4])

        with c1:
            st.markdown(f"**{label}**")

        with c2:
            st.metric("Battery reserve", f"{reserve:.1f} hrs")

        with c3:
            st.metric("Worst month", worst_month)

        with c4:
            st.metric("Empty-battery days", f"{worst_days} days")

        if worst_days == 0:
            st.caption(
                f"{label} shows no battery depletion days in any month for the selected operating profile "
                f"({required_hours:.1f} hrs/day)."
            )
        else:
            st.caption(
                f"{label} may experience battery depletion in {worst_month} "
                f"({worst_days} days, {worst_pct:.1f}% of days in that month)."
            )

        st.markdown("---")

    st.markdown("### Monthly empty-battery days")

    if plot_df.empty:
        st.info("No devices selected for display.")
        return

    chart = alt.Chart(plot_df).mark_bar().encode(
        x=alt.X("Month:N", sort=MONTHS, title="Month"),
        y=alt.Y("EmptyBatteryDays:Q", title="Days with empty battery"),
        color=alt.Color(
            "Device:N",
            title="Device",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="top-right")
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("EmptyBatteryDays:Q", title="Days with empty battery"),
            alt.Tooltip("EmptyBatteryPct:Q", title="Share of month", format=".1f"),
        ],
    ).properties(height=420)

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Bars show the number of days in each month when the battery would become fully discharged "
        "for the selected operating mode."
    )

    st.markdown("### Monthly table")

    pivot_days = plot_df.pivot(index="Month", columns="Device", values="EmptyBatteryDays").reindex(MONTHS)
    st.dataframe(pivot_days.fillna(0).astype(int), use_container_width=True)
