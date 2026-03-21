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
                "MonthStart": i + 0.55,
                "MonthEnd": i + 1.45,
                "Device": label,
                "Hours": hours,
                "RequiredHours": required,
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

    # Green month-by-month bands
    green_rect = alt.Chart(green_df).mark_rect(
        color="#16a34a",
        opacity=0.18
    ).encode(
        x=alt.X(
            "MonthStart:Q",
            scale=alt.Scale(domain=[0.5, 12.5]),
            axis=alt.Axis(
                title="Annual cycle (Jan–Dec)",
                values=list(range(1, 13)),
                labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]"
            )
        ),
        x2="MonthEnd:Q",
        y=alt.Y(
            "RequiredHours:Q",
            scale=alt.Scale(domain=[0, 24]),
            title="Operating hours per day"
        ),
        y2="Hours:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Guaranteed hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    # Red month-by-month bands
    red_rect = alt.Chart(red_df).mark_rect(
        color="#dc2626",
        opacity=0.18
    ).encode(
        x=alt.X("MonthStart:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        x2="MonthEnd:Q",
        y=alt.Y("Hours:Q", scale=alt.Scale(domain=[0, 24])),
        y2="RequiredHours:Q",
        detail="Device:N",
        tooltip=[
            alt.Tooltip("Device:N", title="Device"),
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Hours:Q", title="Guaranteed hrs/day", format=".2f"),
            alt.Tooltip("RequiredHours:Q", title="Required hrs/day", format=".2f"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )

    # Device line
    line_chart = alt.Chart(plot_df).mark_line(
        point=True,
        strokeWidth=2.8
    ).encode(
        x=alt.X(
            "MonthIndex:Q",
            scale=alt.Scale(domain=[0.5, 12.5]),
            axis=alt.Axis(
                title="Annual cycle (Jan–Dec)",
                values=list(range(1, 13)),
                labelExpr="['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value-1]"
            )
        ),
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

    # Required line
    req_df = pd.DataFrame({
        "MonthIndex": list(range(1, 13)),
        "Required": [required_hours] * 12,
    })

    req_line = alt.Chart(req_df).mark_line(
        color="#111827",
        strokeDash=[10, 5],
        strokeWidth=3.2
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[alt.Tooltip("Required:Q", title="Required hrs/day", format=".1f")],
    )

    line_label_df = pd.DataFrame({
        "MonthIndex": [12],
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
        x="MonthIndex:Q",
        y="Required:Q",
        text="Text:N",
    )

    chart = (red_rect + green_rect + line_chart + req_line + line_label).properties(
        height=500
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Blue line = guaranteed operating hours per day by month. "
        "Black dashed line = required daily operation. "
        "Green rectangles = above requirement. Red rectangles = below requirement."
    )
