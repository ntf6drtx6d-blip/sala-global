# ui/graph.py
# ACTION: REPLACE ENTIRE FILE

import altair as alt
import pandas as pd
import streamlit as st


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def build_monthly_df(results, required_hrs):
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)

        for i, month in enumerate(MONTHS):
            hours = float(r["hours"][i])
            required = float(required_hrs)

            rows.append({
                "Month": month,
                "MonthIndex": i + 1,
                "Device": label,
                "Hours": hours,
                "RequiredHours": required,

                # Green band only when above requirement
                "GreenTop": hours if hours >= required else required,
                "GreenBottom": required if hours >= required else required,

                # Red band only when below requirement
                "RedTop": required if hours < required else hours,
                "RedBottom": hours if hours < required else hours,

                "AboveRequirement": hours >= required,
                "BelowRequirement": hours < required,

                "Meaning": (
                    f"{label}: {hours:.2f} hrs/day in {month}. "
                    f"Required daily operation: {required:.2f} hrs/day."
                )
            })

    return pd.DataFrame(rows)


def render_graph():
    st.markdown("## Annual operating profile")
    st.caption("12-month solar performance from January to December")

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
    green_df = plot_df[plot_df["AboveRequirement"]].copy()
    red_df = plot_df[plot_df["BelowRequirement"]].copy()

    # Green fill only where device is above requirement
    green_fill = alt.Chart(green_df).mark_area(
        color="#16a34a",
        opacity=0.18
    ).encode(
        x=alt.X("Month:N", sort=MONTHS, title="Annual cycle (Jan–Dec)"),
        y=alt.Y(
            "GreenTop:Q",
            scale=alt.Scale(domain=[0, 24]),
            title="Operating hours per day"
        ),
        y2="GreenBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Guaranteed hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    # Red fill only where device is below requirement
    red_fill = alt.Chart(red_df).mark_area(
        color="#dc2626",
        opacity=0.18
    ).encode(
        x=alt.X("Month:N", sort=MONTHS),
        y=alt.Y("RedTop:Q", scale=alt.Scale(domain=[0, 24])),
        y2="RedBottom:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Guaranteed hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    line_chart = alt.Chart(plot_df).mark_line(
        point=True,
        strokeWidth=2.8
    ).encode(
        x=alt.X("Month:N", sort=MONTHS),
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        color=alt.Color(
            "Device:N",
            title="Selected devices",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="top-right"),
        ),
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Guaranteed hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    req_df = pd.DataFrame({
        "Month": MONTHS,
        "Required": [required_hours] * 12,
        "Label": [f"Required daily operation = {required_hours:.1f} hrs/day"] * 12,
    })

    req_line = alt.Chart(req_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=3.2
    ).encode(
        x=alt.X("Month:N", sort=MONTHS),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Required:Q", title="Required hrs/day", format=".1f"),
            alt.Tooltip("Label:N", title="Reference"),
        ],
    )

    line_label_df = pd.DataFrame({
        "Month": ["Dec"],
        "Required": [required_hours],
        "Text": [f"Required daily operation = {required_hours:.1f} hrs/day"],
    })

    line_label = alt.Chart(line_label_df).mark_text(
        align="right",
        dx=-8,
        dy=-10,
        fontSize=12,
        fontWeight="bold",
        color="#111827"
    ).encode(
        x=alt.X("Month:N", sort=MONTHS),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    chart = (red_fill + green_fill + line_chart + req_line + line_label).properties(
        height=500
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Blue line = guaranteed operating hours per day by month. "
        "Black dashed line = required daily operation. "
        "Green area = above requirement. Red area = below requirement."
    )
