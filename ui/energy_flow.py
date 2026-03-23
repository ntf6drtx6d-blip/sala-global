import math
from typing import Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st


def _card(title: str, value: str, note: str, accent: str = "blue"):
    accent_map = {
        "blue": ("#eef4ff", "#d6e4ff", "#1f4fbf"),
        "green": ("#ecfdf3", "#abefc6", "#067647"),
        "red": ("#fef3f2", "#f7c7c1", "#b42318"),
        "gray": ("#f8fafc", "#dde3ea", "#344054"),
    }
    bg, border, color = accent_map.get(accent, accent_map["blue"])

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border:1px solid {border};
            border-radius:16px;
            padding:14px 16px;
            min-height:120px;
        ">
            <div style="
                font-size:12px;
                text-transform:uppercase;
                letter-spacing:0.03em;
                color:#667085;
                font-weight:700;
                margin-bottom:8px;
            ">{title}</div>
            <div style="
                font-size:30px;
                line-height:1.05;
                font-weight:800;
                color:{color};
                margin-bottom:8px;
            ">{value}</div>
            <div style="
                font-size:13px;
                line-height:1.35;
                color:#667085;
            ">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _battery_html(level_pct: float, hour: int, solar_input: float, load: float):
    level_pct = max(0, min(100, level_pct))
    sun = "☀️" if 6 <= hour <= 18 else "🌙"
    flow_text = "Panel → Battery" if solar_input > load else "Battery → Lamp"
    flow_color = "#067647" if solar_input > load else "#b42318"

    return f"""
    <div style="
        border:1px solid #dde3ea;
        border-radius:18px;
        padding:18px;
        background:#ffffff;
        min-height:330px;
    ">
        <div style="
            font-size:12px;
            text-transform:uppercase;
            letter-spacing:0.03em;
            color:#667085;
            font-weight:700;
            margin-bottom:10px;
        ">How one solar light works</div>

        <div style="
            font-size:15px;
            color:#344054;
            margin-bottom:18px;
        ">
            During daylight the solar panel recharges the battery. During operation the battery powers the light.
        </div>

        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            margin-bottom:18px;
            font-size:22px;
            font-weight:700;
            color:#0f172a;
        ">
            <div>{sun}</div>
            <div style="font-size:14px; color:{flow_color};">{flow_text}</div>
            <div>💡</div>
        </div>

        <div style="
            margin-bottom:10px;
            font-size:12px;
            text-transform:uppercase;
            letter-spacing:0.03em;
            color:#667085;
            font-weight:700;
        ">Battery level</div>

        <div style="
            width:100%;
            height:32px;
            border:1px solid #cbd5e1;
            border-radius:10px;
            background:#f8fafc;
            padding:3px;
            margin-bottom:10px;
        ">
            <div style="
                width:{level_pct}%;
                height:24px;
                border-radius:7px;
                background:{'#067647' if level_pct >= 35 else '#b54708' if level_pct >= 15 else '#b42318'};
            "></div>
        </div>

        <div style="
            font-size:24px;
            font-weight:800;
            color:#0f172a;
            margin-bottom:16px;
        ">{level_pct:.0f}%</div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div style="border:1px solid #dde3ea; border-radius:12px; padding:10px; background:#f8fafc;">
                <div style="font-size:11px; color:#667085; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Hour</div>
                <div style="font-size:18px; font-weight:700; color:#0f172a;">{hour:02d}:00</div>
            </div>
            <div style="border:1px solid #dde3ea; border-radius:12px; padding:10px; background:#f8fafc;">
                <div style="font-size:11px; color:#667085; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Solar input</div>
                <div style="font-size:18px; font-weight:700; color:#0f172a;">{solar_input:.1f} Wh</div>
            </div>
            <div style="border:1px solid #dde3ea; border-radius:12px; padding:10px; background:#f8fafc;">
                <div style="font-size:11px; color:#667085; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Load</div>
                <div style="font-size:18px; font-weight:700; color:#0f172a;">{load:.1f} Wh</div>
            </div>
            <div style="border:1px solid #dde3ea; border-radius:12px; padding:10px; background:#f8fafc;">
                <div style="font-size:11px; color:#667085; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Net flow</div>
                <div style="font-size:18px; font-weight:700; color:{flow_color};">{solar_input - load:+.1f} Wh</div>
            </div>
        </div>
    </div>
    """


def _annual_reserve_chart(months: List[str], reserve_pct: List[float]) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=months,
            y=reserve_pct,
            mode="lines+markers",
            name="Battery reserve",
            line=dict(width=3),
        )
    )

    fig.add_hline(y=35, line_dash="dot", line_color="#94a3b8")
    fig.add_hline(y=15, line_dash="dot", line_color="#c2410c")
    fig.add_hline(y=0, line_dash="solid", line_color="#b42318")

    fig.update_layout(
        title="Battery reserve through the year",
        height=360,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Month",
        yaxis_title="Reserve (%)",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_yaxes(range=[min(-10, min(reserve_pct) - 5), max(100, max(reserve_pct) + 5)], gridcolor="#e5e7eb")
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig


def _monthly_balance_chart(months: List[str], generated: List[float], demand: List[float]) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Bar(x=months, y=generated, name="Generated energy"))
    fig.add_trace(go.Scatter(x=months, y=demand, mode="lines+markers", name="Required energy", line=dict(width=3)))

    fig.update_layout(
        title="Monthly generation vs operating demand",
        height=330,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Month",
        yaxis_title="Wh / month",
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_yaxes(gridcolor="#e5e7eb")
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig


def _worst_case_block(worst_month: str, lowest_reserve: float, blackout_risk: str):
    st.markdown(
        f"""
        <div style="
            border:1px solid #dde3ea;
            border-radius:16px;
            padding:16px 18px;
            background:#ffffff;
        ">
            <div style="
                font-size:12px;
                text-transform:uppercase;
                letter-spacing:0.03em;
                color:#667085;
                font-weight:700;
                margin-bottom:10px;
            ">Worst-case period</div>

            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
                <div>
                    <div style="font-size:12px; color:#667085; margin-bottom:6px;">Worst month</div>
                    <div style="font-size:22px; font-weight:800; color:#0f172a;">{worst_month}</div>
                </div>
                <div>
                    <div style="font-size:12px; color:#667085; margin-bottom:6px;">Lowest reserve</div>
                    <div style="font-size:22px; font-weight:800; color:#0f172a;">{lowest_reserve:.0f}%</div>
                </div>
                <div>
                    <div style="font-size:12px; color:#667085; margin-bottom:6px;">Blackout exposure</div>
                    <div style="font-size:22px; font-weight:800; color:#0f172a;">{blackout_risk}</div>
                </div>
            </div>

            <div style="
                margin-top:14px;
                font-size:14px;
                line-height:1.45;
                color:#667085;
            ">
                This is the period where solar generation is weakest relative to the checked daily operating requirement.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_demo_day(hour: int):
    # simple explain-mode only
    solar_profile = {
        0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0,
        6: 5, 7: 12, 8: 25, 9: 40, 10: 52, 11: 60,
        12: 64, 13: 62, 14: 54, 15: 40, 16: 24, 17: 10,
        18: 2, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0,
    }
    solar_input = float(solar_profile.get(hour, 0))
    load = 8.0 if hour >= 18 or hour <= 5 else 0.0

    # just visual demo logic, not engineering result
    phase = math.sin((hour / 24) * math.pi * 2 - math.pi / 2)
    level = 60 + phase * 22
    if load > solar_input:
        level -= 8
    return max(5, min(100, level)), solar_input, load


def render_energy_flow(
    selected_device_name: str,
    required_hours: float,
    overall_result: str,
    worst_blackout_risk: str,
    lowest_reserve_pct: float,
    months: List[str],
    reserve_pct: List[float],
    generated_monthly_wh: List[float],
    demand_monthly_wh: List[float],
    worst_month: str,
):
    st.markdown("## Energy Flow & Reserve")
    st.caption(
        "See how the selected solar AGL system charges, discharges and maintains reserve over time."
    )

    accent = "green" if str(overall_result).upper() == "PASS" else "red"
    risk_accent = "green" if str(worst_blackout_risk).startswith("0 ") else "red"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card(
            "Required daily operation",
            f"{required_hours:.0f} hrs/day",
            "Daily operating profile checked in the simulation.",
            "blue",
        )
    with c2:
        _card(
            "Worst blackout risk",
            worst_blackout_risk,
            "Highest annual blackout exposure in the selected configuration.",
            risk_accent,
        )
    with c3:
        _card(
            "Lowest battery reserve",
            f"{lowest_reserve_pct:.0f}%",
            "Lowest reserve reached during the year.",
            "gray" if lowest_reserve_pct > 15 else "red",
        )
    with c4:
        _card(
            "Annual result",
            str(overall_result).upper(),
            "Feasibility against the checked operating requirement.",
            accent,
        )

    st.markdown("")
    left, right = st.columns([1, 1.35], gap="large")

    with left:
        hour = st.slider("Hour of day", 0, 23, 14, 1)
        level, solar_input, load = _build_demo_day(hour)
        st.markdown(_battery_html(level, hour, solar_input, load), unsafe_allow_html=True)

    with right:
        fig = _annual_reserve_chart(months, reserve_pct)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("")
    _worst_case_block(
        worst_month=worst_month,
        lowest_reserve=lowest_reserve_pct,
        blackout_risk=worst_blackout_risk,
    )

    st.markdown("")
    fig2 = _monthly_balance_chart(months, generated_monthly_wh, demand_monthly_wh)
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("What does the checked daily operating requirement mean?"):
        st.write(
            "This is the number of operating hours per day that the system must sustain throughout the year. "
            "The feasibility check tests whether solar generation and battery recovery remain sufficient "
            "to support that requirement without unacceptable blackout exposure."
        )

    st.caption(f"Selected device: {selected_device_name}")
