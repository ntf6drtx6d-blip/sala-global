print("UI GRAPH MODULE LOADED")

import altair as alt
import pandas as pd
import streamlit as st

from core.i18n import month_label, month_labels, t

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _month_label_expr(lang: str) -> str:
    labels = month_labels(lang)
    quoted = ",".join(f"'{label}'" for label in labels)
    return f"[{quoted}][datum.value-1]"


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


def _extract_monthly_empty_battery_days(result_row: dict):
    candidates = [
        result_row.get("empty_battery_days_by_month"),
        result_row.get("monthly_empty_battery_days"),
        result_row.get("monthly_blackout_days"),
        result_row.get("blackout_days_by_month"),
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
    lang = st.session_state.get("language", "en")
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)

        monthly_days = _extract_monthly_empty_battery_days(r)
        monthly_pct = _extract_monthly_empty_battery_pct(r)

        if monthly_days is None and monthly_pct is not None:
            monthly_days = _monthly_blackout_days_from_pct(monthly_pct)

        if monthly_days is None:
            continue

        if monthly_pct is None:
            monthly_pct = []
            for i, days_val in enumerate(monthly_days):
                try:
                    pct_val = (float(days_val) / float(MONTH_DAYS[i])) * 100.0
                except Exception:
                    pct_val = 0.0
                monthly_pct.append(pct_val)

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
                "MonthLabel": month_label(month, lang),
                "MonthIndex": i + 1,
                "Device": label,
                "EmptyBatteryPct": float(monthly_pct[i]),
                "EstimatedBlackoutDays": days_val,
                "MonthDays": MONTH_DAYS[i],
                "StatusBand": status_band,
                "Meaning": t(
                    "ui.blackout_meaning",
                    lang,
                    month=month_label(month, lang),
                    days=days_val,
                    pct=float(monthly_pct[i]),
                    month_days=MONTH_DAYS[i],
                ),
            })

    return pd.DataFrame(rows)


def _render_blackout_detail_table(blackout_df: pd.DataFrame, visible_devices: list[str]):
    detail_df = blackout_df[blackout_df["Device"].isin(visible_devices)].copy()
    if detail_df.empty or float(detail_df["EstimatedBlackoutDays"].max()) <= 0:
        return

    detail_df = detail_df.groupby("Device", group_keys=False).filter(
        lambda frame: float(frame["EstimatedBlackoutDays"].sum()) > 0
    )
    if detail_df.empty:
        return

    pivot = detail_df.pivot(index="Device", columns="Month", values="EstimatedBlackoutDays").reindex(columns=MONTHS)
    pivot = pivot.fillna(0.0)
    pivot.insert(0, "Annual days / year", detail_df.groupby("Device")["EstimatedBlackoutDays"].sum().round(1))
    pivot = pivot.reset_index()
    lang = st.session_state.get("language", "en")
    rename_map = {"Device": t("ui.device", lang), "Annual days / year": t("ui.days_per_year_unit", lang)}
    rename_map.update({month: month_label(month, lang) for month in MONTHS})
    pivot = pivot.rename(columns=rename_map)

    with st.expander(t("ui.monthly_0_battery_days", lang), expanded=False):
        st.caption(t("ui.blackout_detail_caption", lang))
        st.dataframe(
            pivot.style.format({col: "{:.1f}" for col in pivot.columns if col != t("ui.device", lang)}),
            width="stretch",
            hide_index=True,
        )


def build_monthly_df(results: dict, required_hrs: float) -> pd.DataFrame:
    lang = st.session_state.get("language", "en")
    rows = []

    for device_name, r in results.items():
        label = short_device_label(device_name)
        reserve = calc_battery_reserve_hours(r)

        hours_series = r.get("hours", [])
        if not isinstance(hours_series, (list, tuple)) or len(hours_series) != 12:
            continue

        for i, month in enumerate(MONTHS):
            hours = float(hours_series[i])
            required = float(required_hrs)
            gap = hours - required

            status_band = "met"
            if gap < 0:
                status_band = "near-threshold" if abs(gap) < 0.5 else "below"

            if reserve is not None:
                meaning = t(
                    "ui.required_achieved_gap_full",
                    lang,
                    required=required,
                    month=month_label(month, lang),
                    hours=hours,
                    gap=gap,
                    reserve=reserve,
                )
            else:
                meaning = t(
                    "ui.required_achieved_gap",
                    lang,
                    required=required,
                    month=month_label(month, lang),
                    hours=hours,
                    gap=gap,
                )

            rows.append({
                "Month": month,
                "MonthLabel": month_label(month, lang),
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


def _render_operating_profile_detail_table(chart_df: pd.DataFrame, visible_devices: list[str], required_hours: float):
    plot_df = chart_df[chart_df["Device"].isin(visible_devices)].copy()
    if plot_df.empty:
        return

    month_order = {month: idx for idx, month in enumerate(MONTHS)}
    lang = st.session_state.get("language", "en")
    target_row = {t("ui.device", lang): t("ui.defined_compliance_target", lang)}
    for month in MONTHS:
        target_row[month] = f"{required_hours:.1f}h"

    rows = [target_row]
    for device in plot_df["Device"].drop_duplicates():
        device_df = plot_df[plot_df["Device"] == device].copy()
        device_df["MonthOrder"] = device_df["Month"].map(month_order)
        device_df = device_df.sort_values("MonthOrder")
        row = {t("ui.device", lang): device}
        for _, item in device_df.iterrows():
            row[item["Month"]] = f"{float(item['Hours']):.1f}h ({float(item['Gap']):+.1f})"
        rows.append(row)

    table_df = pd.DataFrame(rows, columns=[t("ui.device", lang), *MONTHS]).fillna("—")
    table_df = table_df.rename(columns={month: month_label(month, lang) for month in MONTHS})

    device_col = t("ui.device", lang)

    def _delta_cell_style(value):
        if not isinstance(value, str) or "(" not in value or value == "—":
            return ""
        if "(+" in value:
            return "color:#067647;font-weight:700;"
        if "(-" in value:
            return "color:#b42318;font-weight:700;"
        return ""

    with st.expander(t("ui.detailed_operating_profile_table", lang), expanded=False):
        st.caption(t("ui.operating_profile_table_caption", lang))
        st.dataframe(
            table_df.style.map(_delta_cell_style, subset=[col for col in table_df.columns if col != device_col]),
            width="stretch",
            hide_index=True,
        )


def render_blackout_graph(results: dict, visible_devices: list[str]):
    lang = st.session_state.get("language", "en")
    month_tick_labels = month_labels(lang)
    st.markdown(f"## {t('ui.monthly_0_battery_days', lang)}")

    required_hours = float(st.session_state.get("required_hours", 0))
    if required_hours > 0:
        st.caption(t("ui.blackout_chart_caption_with_hours", lang, hours=required_hours))
    else:
        st.caption(t("ui.blackout_chart_caption", lang))

    blackout_df = build_blackout_df(results)

    if blackout_df.empty:
        st.info(t("ui.no_empty_battery_data", lang))
        return

    plot_df = blackout_df[blackout_df["Device"].isin(visible_devices)].copy()

    if plot_df.empty:
        st.info(t("ui.no_devices_selected", lang))
        return

    if float(plot_df["EstimatedBlackoutDays"].max()) <= 0:
        st.info(t("ui.no_zero_battery_months", lang))
        return

    y_max = max(5, float(plot_df["EstimatedBlackoutDays"].max()) + 2)

    tooltip_fields = [
        alt.Tooltip("Device:N", title=t("ui.device", lang)),
        alt.Tooltip("MonthLabel:N", title=t("ui.month", lang)),
        alt.Tooltip("EstimatedBlackoutDays:Q", title=t("ui.monthly_0_battery_days", lang), format=".1f"),
        alt.Tooltip("EmptyBatteryPct:Q", title=t("ui.share_of_month_empty", lang), format=".1f"),
        alt.Tooltip("MonthDays:Q", title=t("ui.days_in_month", lang), format=".0f"),
        alt.Tooltip("Meaning:N", title=t("ui.interpretation", lang)),
    ]

    bars = alt.Chart(plot_df).mark_bar(
        opacity=0.55,
        size=22
    ).encode(
        x=alt.X("MonthLabel:N", sort=month_tick_labels, axis=alt.Axis(title=t("ui.month", lang), labelAngle=0)),
        y=alt.Y(
            "EstimatedBlackoutDays:Q",
            title=t("ui.days", lang),
            scale=alt.Scale(domain=[0, y_max])
        ),
        xOffset=alt.XOffset("Device:N"),
        color=alt.Color(
            "Device:N",
            title=t("ui.device", lang),
            scale=alt.Scale(scheme="tableau10"),
        ),
        tooltip=tooltip_fields,
    )

    line_chart = alt.Chart(plot_df).mark_line(
        point=True,
        strokeWidth=2.2
    ).encode(
        x=alt.X("MonthLabel:N", sort=month_tick_labels),
        y=alt.Y(
            "EstimatedBlackoutDays:Q",
            scale=alt.Scale(domain=[0, y_max])
        ),
        color=alt.Color(
            "Device:N",
            title=t("ui.device", lang),
            scale=alt.Scale(scheme="tableau10"),
        ),
        detail="Device:N",
        tooltip=tooltip_fields,
    )

    zero_line_df = pd.DataFrame({
        "MonthLabel": month_tick_labels,
        "Target": [0] * 12,
    })

    zero_line = alt.Chart(zero_line_df).mark_line(
        color="#dc2626",
        strokeDash=[8, 4],
        strokeWidth=2.0
    ).encode(
        x=alt.X("MonthLabel:N", sort=month_tick_labels),
        y=alt.Y("Target:Q", scale=alt.Scale(domain=[0, y_max])),
    )

    zero_label_df = pd.DataFrame({
        "MonthLabel": [month_tick_labels[-1]],
        "Target": [0],
        "Text": [t("ui.target_zero_days", lang)],
    })

    zero_label = alt.Chart(zero_label_df).mark_text(
        align="right",
        dx=-8,
        dy=-10,
        fontSize=11,
        fontWeight="bold",
        color="#dc2626"
    ).encode(
        x=alt.X("MonthLabel:N", sort=month_tick_labels),
        y=alt.Y("Target:Q", scale=alt.Scale(domain=[0, y_max])),
        text="Text:N",
    )

    chart = (
        bars
        + line_chart
        + zero_line
        + zero_label
    ).properties(
        height=280
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        t("ui.zero_battery_days_explainer", lang)
    )
    _render_blackout_detail_table(blackout_df, visible_devices)


def render_graph():
    lang = st.session_state.get("language", "en")
    results = st.session_state.get("results", {})
    if not results:
        return

    required_hours = float(st.session_state.get("required_hours", 0))
    chart_df = build_monthly_df(results, required_hours)

    if chart_df.empty:
        st.info(t("ui.graph_data_unavailable", lang))
        return

    device_labels = list(chart_df["Device"].unique())

    visible_devices = st.multiselect(
        t("ui.devices_shown_on_graph", lang),
        device_labels,
        default=device_labels,
        help=t("ui.devices_shown_help", lang),
        key="graph_devices_filter",
    )

    render_blackout_graph(results, visible_devices)

    st.markdown(f"## {t('ui.annual_operating_profile', lang)}")
    st.caption(t("ui.solar_performance_caption", lang))

    plot_df = chart_df[chart_df["Device"].isin(visible_devices)].copy()

    if plot_df.empty:
        st.info(t("ui.no_devices_selected", lang))
        return

    green_df = plot_df[plot_df["StatusBand"] == "met"].copy()
    yellow_df = plot_df[plot_df["StatusBand"] == "near-threshold"].copy()
    red_df = plot_df[plot_df["StatusBand"] == "below"].copy()

    x_axis = alt.X(
        "MonthIndex:Q",
        scale=alt.Scale(domain=[0.5, 12.5]),
        axis=alt.Axis(
            title=t("ui.month", lang),
            values=list(range(1, 13)),
            labelExpr=_month_label_expr(lang),
            labelAngle=0,
            domain=True,
            domainWidth=2.5,
            domainColor="#374151",
            tickWidth=2,
            tickSize=6,
            tickColor="#9CA3AF",
            labelPadding=8,
            labelColor="#6B7280",
            titleColor="#374151",
        )
    )

    y_axis = alt.Y(
        "Hours:Q",
        scale=alt.Scale(domain=[0, 24]),
        axis=alt.Axis(
            title=t("ui.achieved_operating_hours_per_day", lang),
            domain=True,
            domainWidth=2,
            domainColor="#9CA3AF",
            tickWidth=2,
            tickSize=6,
            tickColor="#9CA3AF",
            grid=True,
            labelPadding=6,
            labelColor="#6B7280",
            titleColor="#374151",
        ),
    )

    green_rect = alt.Chart(green_df).mark_rect(
        color="#16a34a",
        opacity=0.15
    ).encode(
        x=alt.X(
            "MonthStart:Q",
            scale=alt.Scale(domain=[0.5, 12.5]),
            axis=alt.Axis(
                title=t("ui.month", lang),
                values=list(range(1, 13)),
                labelExpr=_month_label_expr(lang),
                labelAngle=0,
                domain=True,
                domainWidth=2.5,
                domainColor="#374151",
                tickWidth=2,
                tickSize=6,
                tickColor="#9CA3AF",
                labelPadding=8,
                labelColor="#6B7280",
                titleColor="#374151",
            )
        ),
        x2="MonthEnd:Q",
        y=alt.Y(
            "RequiredHours:Q",
            scale=alt.Scale(domain=[0, 24]),
            title=t("ui.achieved_operating_hours_per_day", lang)
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
            title=t("ui.selected_devices", lang),
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="top-right"),
        ),
        tooltip=[
            alt.Tooltip("Device:N", title=t("ui.device", lang)),
            alt.Tooltip("MonthLabel:N", title=t("ui.month", lang)),
            alt.Tooltip("RequiredHours:Q", title=t("ui.required_hours", lang), format=".1f"),
            alt.Tooltip("Hours:Q", title=t("ui.achieved_hours", lang), format=".1f"),
            alt.Tooltip("Gap:Q", title=t("ui.gap_vs_requirement", lang), format="+.1f"),
            alt.Tooltip("BatteryReserve:Q", title=t("ui.battery_reserve", lang), format=".1f"),
            alt.Tooltip("Meaning:N", title=t("ui.interpretation", lang)),
        ],
    )

    req_df = pd.DataFrame({
        "MonthIndex": list(range(1, 13)),
        "Required": [required_hours] * 12,
    })

    req_line = alt.Chart(req_df).mark_line(
        color="#1f4fbf",
        strokeDash=[6, 4],
        strokeWidth=3.5
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        tooltip=[
            alt.Tooltip("Required:Q", title=t("ui.required_hours", lang), format=".1f")
        ],
    )

    zero_df = pd.DataFrame({
        "MonthIndex": [0.5, 12.5],
        "Zero": [0, 0],
    })

    zero_line = alt.Chart(zero_df).mark_line(
        color="#374151",
        strokeWidth=2.5
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Zero:Q", scale=alt.Scale(domain=[0, 24])),
    )

    req_connector_df = pd.DataFrame({
        "x": [0.58, 0.58],
        "y": [0, required_hours],
    })

    req_connector = alt.Chart(req_connector_df).mark_line(
        color="#1f4fbf",
        strokeWidth=2.2
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 24])),
    )

    req_label_df = pd.DataFrame({
        "MonthIndex": [0.9],
        "Required": [required_hours],
        "Text": [t("ui.required_operation", lang)],
    })

    req_label = alt.Chart(req_label_df).mark_text(
        align="left",
        dx=8,
        dy=-8,
        fontSize=12,
        fontWeight="bold",
        color="#1f4fbf"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    req_value_label_df = pd.DataFrame({
        "MonthIndex": [10.8],
        "Required": [required_hours],
        "Text": [f"{required_hours:.1f} {t('ui.hours_per_day_unit', lang)}"],
    })

    req_value_label = alt.Chart(req_value_label_df).mark_text(
        align="right",
        dx=0,
        dy=-8,
        fontSize=11,
        color="#1f4fbf",
        fontWeight="bold",
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    req_icon_df = pd.DataFrame({
        "MonthIndex": [0.72],
        "Required": [required_hours],
        "Icon": ["✈"],
    })

    req_icon = alt.Chart(req_icon_df).mark_text(
        align="center",
        baseline="middle",
        dx=0,
        dy=-18,
        fontSize=15,
        color="#1f4fbf"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Required:Q", scale=alt.Scale(domain=[0, 24])),
        text="Icon:N",
    )

    zero_label_df = pd.DataFrame({
        "MonthIndex": [0.8],
        "Zero": [0],
        "Text": [t("ui.zero_hours_per_day", lang)],
    })

    zero_label = alt.Chart(zero_label_df).mark_text(
        align="left",
        dx=8,
        dy=12,
        fontSize=11,
        color="#374151"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
        y=alt.Y("Zero:Q", scale=alt.Scale(domain=[0, 24])),
        text="Text:N",
    )

    chart_note_df = pd.DataFrame({
        "MonthIndex": [6.5],
        "Hours": [23.2],
        "Text": [t("ui.required_line_note", lang)],
    })

    chart_note = alt.Chart(chart_note_df).mark_text(
        align="center",
        fontSize=11,
        color="#344054"
    ).encode(
        x=alt.X("MonthIndex:Q", scale=alt.Scale(domain=[0.5, 12.5])),
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
        + req_value_label
        + zero_label
        + chart_note
    ).properties(
        height=500
    ).interactive().configure_axis(
        labelFontSize=12,
        titleFontSize=13,
        gridColor="#E5E7EB",
        gridOpacity=0.8,
        domainColor="#9CA3AF",
        domainWidth=1.5,
        tickColor="#9CA3AF",
        labelColor="#6B7280",
        titleColor="#374151",
    ).configure_view(
        stroke="#D0D5DD",
        strokeWidth=1.2,
        clip=False
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        f"""
        <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:0.95rem;color:#475467;">
            <div><span style="display:inline-block;width:14px;height:14px;background:#16a34a;opacity:0.7;border-radius:3px;margin-right:6px;"></span>{t("ui.requirement_met", lang)}</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#f59e0b;opacity:0.7;border-radius:3px;margin-right:6px;"></span>{t("ui.near_threshold_shortfall", lang)}</div>
            <div><span style="display:inline-block;width:14px;height:14px;background:#dc2626;opacity:0.7;border-radius:3px;margin-right:6px;"></span>{t("ui.below_requirement", lang)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        t("ui.hover_profile_explainer", lang)
    )
    _render_operating_profile_detail_table(chart_df, visible_devices, required_hours)
