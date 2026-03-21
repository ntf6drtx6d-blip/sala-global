# ui/battery.py
# ACTION: REPLACE ENTIRE FILE

import math
import pandas as pd
import altair as alt
import streamlit as st

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def short_device_label(full_name: str) -> str:
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def calc_battery_reserve_hours(result_row: dict):
    """
    Battery reserve = usable battery energy / consumption
    Usable battery assumed at 70%
    """
    try:
        batt = float(result_row["batt"])
        power = max(float(result_row["power"]), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def build_empty_battery_df(results: dict) -> pd.DataFrame:
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


def compact_device_note(label: str, result_row: dict) -> str:
    reserve = calc_battery_reserve_hours(result_row)
    monthly_days = result_row.get("empty_battery_days_by_month") or [0] * 12
    monthly_pct = result_row.get("empty_battery_pct_by_month") or [0] * 12

    idx = max(range(12), key=lambda i: monthly_days[i])
    worst_days = monthly_days[idx]
    worst_pct = float(monthly_pct[idx]) if monthly_pct else 0.0
    worst_month = MONTHS[idx]

    if reserve is None:
        reserve_text = "Battery autonomy not available."
    else:
        reserve_text = f"Battery autonomy: approx. {reserve:.1f} hrs from stored battery energy only."

    if worst_days == 0:
        return (
            f"{reserve_text} No empty-battery days are expected in any month for the selected operating mode."
        )

    return (
        f"{reserve_text} Highest battery depletion risk appears in {worst_month}: "
        f"{worst_days} days ({worst_pct:.1f}% of days in that month)."
    )


def render_battery():
    results = st.session_state.get("results", {})
    if not results:
        return

    st.markdown("## Battery depletion risk")

    st.caption(
        "This graph shows how many days in each month the battery would become fully discharged "
        "for the selected operating mode."
    )

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

    if plot_df.empty:
        st.info("No devices selected for display.")
        return

    all_zero = plot_df["EmptyBatteryDays"].sum() == 0

    # Compact explanation cards
    st.markdown("### What this means")

    for device_name, result_row in results.items():
        label = short_device_label(device_name)
        if label not in visible_devices:
            continue

        monthly_days = result_row.get("empty_battery_days_by_month") or [0] * 12
        idx = max(range(12), key=lambda i: monthly_days[i])
        worst_days = monthly_days[idx]
        worst_month = MONTHS[idx]
        reserve = calc_battery_reserve_hours(result_row)

        c1, c2, c3 = st.columns(3)

        with c1:
            reserve_value = f"{reserve:.1f} hrs" if reserve is not None else "N/A"
            st.markdown(
                f"""
                <div style="
                    border:1px solid #e6eaf0;
                    border-radius:14px;
                    padding:16px 18px;
                    background:#ffffff;
                    min-height:120px;
                    box-shadow:0 2px 10px rgba(16,24,40,0.04);">
                    <div style="font-size:0.95rem;color:#667085;font-weight:700;">{label}</div>
                    <div style="font-size:2.2rem;font-weight:900;color:#1f2937;margin-top:8px;">{reserve_value}</div>
                    <div style="font-size:0.95rem;color:#667085;margin-top:8px;">Battery autonomy</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                f"""
                <div style="
                    border:1px solid #e6eaf0;
                    border-radius:14px;
                    padding:16px 18px;
                    background:#ffffff;
                    min-height:120px;
                    box-shadow:0 2px 10px rgba(16,24,40,0.04);">
                    <div style="font-size:0.95rem;color:#667085;font-weight:700;">Worst month</div>
                    <div style="font-size:2.2rem;font-weight:900;color:#1f2937;margin-top:8px;">{worst_month}</div>
                    <div style="font-size:0.95rem;color:#667085;margin-top:8px;">Highest depletion risk month</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                f"""
                <div style="
                    border:1px solid #e6eaf0;
                    border-radius:14px;
                    padding:16px 18px;
                    background:#ffffff;
                    min-height:120px;
                    box-shadow:0 2px 10px rgba(16,24,40,0.04);">
                    <div style="font-size:0.95rem;color:#667085;font-weight:700;">Empty-battery days</div>
                    <div style="font-size:2.2rem;font-weight:900;color:#1f2937;margin-top:8px;">{worst_days} days</div>
                    <div style="font-size:0.95rem;color:#667085;margin-top:8px;">In the worst month</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div style="font-size:0.96rem;color:#475467;margin-top:10px;margin-bottom:16px;line-height:1.55;">
                {compact_device_note(label, result_row)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if all_zero:
        st.success("No empty-battery days are expected in any month for the selected operating mode.")
        return

    st.markdown("### Monthly empty-battery days")

    base = alt.Chart(plot_df).encode(
        x=alt.X(
            "Month:N",
            sort=MONTHS,
            title="Month"
        ),
        y=alt.Y(
            "EmptyBatteryDays:Q",
            title="Days with empty battery"
        ),
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
    )

    compact_chart = (
        base.mark_line(point=True, strokeWidth=2.5)
        + base.mark_area(opacity=0.12)
    ).properties(height=240)

    st.altair_chart(compact_chart, use_container_width=True)

    with st.expander("Expand monthly battery-risk chart", expanded=False):
        expanded_chart = (
            base.mark_line(point=True, strokeWidth=3)
            + base.mark_area(opacity=0.14)
        ).properties(height=420)

        st.altair_chart(expanded_chart, use_container_width=True)

    st.caption(
        "The line shows monthly battery depletion risk for the selected operating mode. "
        "Filled area is used only to improve readability."
    )
