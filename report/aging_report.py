# report/aging_report.py
#
# Phase-1 Battery Aging page - data builder, charts, and a standalone
# renderer for review.
#
# NOT wired into report/report.py's default render_report_html() /
# build_report_data() flow, and report/templates/report.html does not
# include partials/_aging_page.html anywhere. This module exists to be
# reviewed and tested on its own; hooking it into the live report is a
# separate, deliberate step once the design is signed off.

from __future__ import annotations

from pathlib import Path

import jinja2
import matplotlib.pyplot as plt

from core.simulate import estimate_battery_aging_for_results
from report.html_builder import _chart_html_from_figure

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

DEVICE_LINE_COLORS = ["#0ea5e9", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#14b8a6", "#ec4899", "#84cc16"]
DEVICE_LINE_STYLES = ["-", "--", "-.", ":"]
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _checkpoint(checkpoints, age_years):
    for cp in checkpoints:
        if cp["age_years"] == age_years:
            return cp
    return None


def build_aging_page_data(loc, required_hrs, results, device_short_names: dict) -> dict:
    """
    device_short_names: {result_key: display_name}, matching the same
    per-device names already shown elsewhere in the report (see
    report/data_builder.py's _short_name), so this page's table is
    consistent with the rest of the document.
    """
    aging = estimate_battery_aging_for_results(loc, required_hrs, results)

    summary_rows = []
    trajectories = []
    fade_breakdowns = []
    for result_key, device_aging in aging["devices"].items():
        checkpoints = device_aging["checkpoints"]
        year0 = _checkpoint(checkpoints, 0)
        year5 = _checkpoint(checkpoints, 5)
        year10 = _checkpoint(checkpoints, 10)
        name = device_short_names.get(result_key, result_key)

        summary_rows.append({
            "name": name,
            "battery_type": device_aging["battery_type"],
            "dominant_fade_mechanism": device_aging["dominant_fade_mechanism"],
            "year0_status": year0["status"] if year0 else "N/A",
            "year5_status": year5["status"] if year5 else "N/A",
            "year10_status": year10["status"] if year10 else "N/A",
            "year0_blackout_days": year0["annual_blackout_days"] if year0 else 0,
            "year5_blackout_days": year5["annual_blackout_days"] if year5 else 0,
            "year10_blackout_days": year10["annual_blackout_days"] if year10 else 0,
            "year0_capacity_pct": year0["capacity_retention_pct"] if year0 else 100.0,
            "year5_capacity_pct": year5["capacity_retention_pct"] if year5 else 100.0,
            "year10_capacity_pct": year10["capacity_retention_pct"] if year10 else 100.0,
        })
        trajectories.append({
            "name": name,
            "ages": [cp["age_years"] for cp in checkpoints],
            "capacities": [cp["capacity_retention_pct"] for cp in checkpoints],
        })
        fade_breakdowns.append({
            "name": name,
            "calendar_share_pct": device_aging["calendar_fade_share_pct"],
            "cycle_share_pct": device_aging["cycle_fade_share_pct"],
        })

    return {
        "avg_site_temp_c": aging["avg_site_temp_c"],
        "monthly_temps_c": aging["monthly_temps_c"],
        "summary_rows": summary_rows,
        "temperature_chart_html": _monthly_temperature_chart(aging["monthly_temps_c"]),
        "capacity_chart_html": _capacity_trajectory_chart(trajectories),
        "fade_driver_chart_html": _fade_driver_pie_charts(fade_breakdowns),
    }


def _monthly_temperature_chart(monthly_temps_c) -> str:
    """Monthly average ambient temperature (PVGIS MRcalc, avtemp=1) across
    the year - gives the reader the seasonal context behind the single
    annual-average figure the calendar-aging formula actually uses."""
    fig, ax = plt.subplots(figsize=(7.4, 2.8))
    x = list(range(12))

    ax.plot(x, monthly_temps_c, color="#f97316", linewidth=2.6, marker="o", markersize=6, solid_capstyle="round")
    for xi, t in zip(x, monthly_temps_c):
        ax.annotate(f"{t:.0f}°", (xi, t), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9, color="#7c2d12")

    avg = sum(monthly_temps_c) / len(monthly_temps_c)
    ax.axhline(avg, color="#94a3b8", linestyle=(0, (3, 2)), linewidth=1.3)
    ax.annotate(f"Annual average: {avg:.1f}°C", (11, avg), textcoords="offset points", xytext=(-4, -16),
                ha="right", fontsize=9, color="#475467")

    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_LABELS, fontsize=10)
    ax.set_ylabel("Avg. temperature (°C)", fontsize=10)
    ax.tick_params(axis="y", labelsize=10)
    ax.grid(axis="y", color="#dbe3ef", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    margin = max(3.0, (max(monthly_temps_c) - min(monthly_temps_c)) * 0.25)
    ax.set_ylim(min(monthly_temps_c) - margin, max(monthly_temps_c) + margin)
    fig.tight_layout()

    return _chart_html_from_figure(fig)


def _capacity_trajectory_chart(trajectories) -> str:
    """Capacity retained (%) vs. age, one line per device. Kept on a
    shared, naturally bounded 0-100% axis deliberately - unlike blackout
    days/year, capacity retention is always comparable across devices
    regardless of how severely any one of them fails, so this stays
    readable even when devices differ wildly in severity."""
    fig, ax = plt.subplots(figsize=(7.4, 3.6))

    for idx, traj in enumerate(trajectories):
        color = DEVICE_LINE_COLORS[idx % len(DEVICE_LINE_COLORS)]
        style = DEVICE_LINE_STYLES[idx % len(DEVICE_LINE_STYLES)]
        ax.plot(
            traj["ages"], traj["capacities"],
            label=traj["name"], color=color, linestyle=style,
            linewidth=2.6, marker="o", markersize=6, solid_capstyle="round",
        )
        last_age, last_cap = traj["ages"][-1], traj["capacities"][-1]
        ax.annotate(
            f"{last_cap:.0f}%", (last_age, last_cap),
            textcoords="offset points", xytext=(8, 0),
            va="center", fontsize=9, fontweight="bold", color=color,
        )

    ax.axhline(80, color="#94a3b8", linestyle=(0, (3, 2)), linewidth=1.3)
    ax.annotate("80% - conventional end-of-life", (0.1, 81), fontsize=8.5, color="#667085")

    ax.set_xlabel("Age (years)", fontsize=10)
    ax.set_ylabel("Capacity retained (%)", fontsize=10)
    ax.set_yticks(range(0, 101, 20))
    ax.tick_params(labelsize=10)
    ax.set_ylim(0, 108)
    ax.set_xlim(-0.3, max((traj["ages"][-1] for traj in trajectories), default=10) + 1.2)
    ax.grid(axis="y", color="#dbe3ef", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower left", frameon=False, fontsize=9.5, ncol=1, bbox_to_anchor=(0, 1.02))
    fig.tight_layout(rect=[0, 0, 1, 0.82])

    return _chart_html_from_figure(fig)


def _fade_driver_pie_charts(fade_breakdowns) -> str:
    """One small pie per device: what share of its annual capacity fade
    comes from temperature (calendar aging) vs. daily cycling (cycle
    aging). A 2-slice pie is a natural fit for a single whole split into
    exactly two named causes, and small multiples keep it readable even
    with several devices."""
    n = max(1, len(fade_breakdowns))
    fig, axes = plt.subplots(1, n, figsize=(2.4 * n, 2.6))
    if n == 1:
        axes = [axes]

    colors = ["#f97316", "#2563eb"]  # temperature, cycling
    for ax, breakdown in zip(axes, fade_breakdowns):
        values = [breakdown["calendar_share_pct"], breakdown["cycle_share_pct"]]
        ax.pie(
            values,
            colors=colors,
            autopct=lambda p: f"{p:.0f}%" if p >= 8 else "",
            startangle=90,
            textprops={"fontsize": 9, "color": "white", "fontweight": "bold"},
            wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
        )
        ax.set_title(breakdown["name"], fontsize=8.5, wrap=True, pad=6)

    fig.legend(
        ["Temperature (calendar aging)", "Cycling (depth-of-discharge)"],
        loc="lower center", ncol=2, frameon=False, fontsize=9,
        bbox_to_anchor=(0.5, -0.04),
    )
    fig.tight_layout(rect=[0, 0.06, 1, 1])

    return _chart_html_from_figure(fig)


def render_aging_page_html_standalone(loc, required_hrs, results, device_short_names, footer_note: str = "") -> str:
    """Render just this page's HTML, for review/testing. Does not touch
    report.html or render_report_html() - loads the same template
    directory so styling matches, but renders only the aging partial."""
    aging_data = build_aging_page_data(loc, required_hrs, results, device_short_names)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("partials/_aging_page.html")
    return template.render(aging=aging_data, report={"footer_note": footer_note})
