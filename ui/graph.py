# ui/graph.py
# ACTION: REPLACE ENTIRE FILE

import altair as alt
import pandas as pd
import streamlit as st


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def build_monthly_df(results, required_hrs):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)

        for i, month in enumerate(months):
            hours = float(r["hours"][i])
            required = float(required_hrs)
            diff = hours - required

            rows.append({
                "Month": month,
                "MonthIndex": i + 1,
                "Device": label,
                "Hours": hours,
                "RequiredHours": required,
                "Difference": diff,
                "StatusBand": "Above requirement" if diff >= 0 else "Below requirement",
                "FillTop": max(hours, required),
                "FillBottom": min(hours, required),
                "Meaning": (
                    f"{label}: {hours:.2f} hrs/day in {month}. "
                    f"Required daily operation: {required:.2f} hrs/day."
                )
            })

    return pd.DataFrame(rows)


def render_graph():
    st.markdown("## Annual operating profile (12-month solar performance)")

    results = st.session_state.results
    required_hours = float(st.session_state.required_hours)

    chart_df = build_monthly_df(results, required_hours)
    device_labels = list(chart_df["Device"].unique())

    visible_devices = st.multiselect(
        "Devices shown on graph",
        device_labels,
        default=device_labels,
        help="Untick devices to hide them from the graph.",
    )

    plot_df = chart_df[chart_df["Device"].isin(visible_devices)].copy()
    above_df = plot_df[plot_df["Hours"] >= plot_df["RequiredHours"]].copy()
    below_df = plot_df[plot_df["Hours"] < plot_df["RequiredHours"]].copy()

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Green fill where device is above requirement
    green_fill = alt.Chart(above_df).mark_area(
        color="#16a34a",
        opacity=0.17
    ).encode(
        x=alt.X("Month:N", sort=month_order, title="Annual cycle (Jan–Dec)"),
        y=alt.Y(
            "FillTop:Q",
            scale=alt.Scale(domain=[0, 24]),
            title="Operating hours per day"
        ),
        y2="FillBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    # Red fill where device is below requirement
    red_fill = alt.Chart(below_df).mark_area(
        color="#dc2626",
        opacity=0.22
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("FillTop:Q", scale=alt.Scale(domain=[0, 24])),
        y2="FillBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    # Device lines
    line_chart = alt.Chart(plot_df).mark_line(
        point=True,
        strokeWidth=2.8
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        color=alt.Color(
            "Device:N",
            title="Device",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="top-right"),
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Simulated hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("StatusBand:N", title="Status"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    # Required operating line
    req_df = pd.DataFrame({
        "Month": month_order,
        "Required": [required_hours] * 12,
        "Label": [f"Required daily operation: {required_hours:.1f} hrs/day"] * 12,
    })

    req_line = alt.Chart(req_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=3.2
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Required:Q", title="Required hrs/day", format=".1f"),
            alt.Tooltip("Label:N", title="Reference"),
        ],
    )

    # Label directly on the dashed line
    line_label_df = pd.DataFrame({
        "Month": ["Dec"],
        "Required": [required_hours],
        "Text": [f"Required daily operation: {required_hours:.1f} hrs/day"],
    })

    line_label = alt.Chart(line_label_df).mark_text(
        align="right",
        dx=-10,
        dy=-8,
        fontSize=12,
        fontWeight="bold",
        color="#111827"
    ).encode(
        x=alt.X("Month:N", sort=month_order),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    chart = (green_fill + red_fill + line_chart + req_line + line_label).properties(
        height=470
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Each point shows achievable daily operating hours in a given month. "
        "Black dashed line = required daily operation. "
        "Green = above requirement. Red = below requirement."
    )
