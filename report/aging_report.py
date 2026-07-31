# report/aging_report.py
#
# Phase-1 Battery Aging page - data builder, chart, and a standalone
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

    return {
        "avg_site_temp_c": aging["avg_site_temp_c"],
        "summary_rows": summary_rows,
        "comparison_chart_html": _capacity_trajectory_chart(trajectories),
    }


def _capacity_trajectory_chart(trajectories) -> str:
    """Capacity retained (%) vs. age, one line per device. Kept on a
    shared, naturally bounded 0-100% axis deliberately - unlike blackout
    days/year, capacity retention is always comparable across devices
    regardless of how severely any one of them fails, so this stays
    readable even when devices differ wildly in severity."""
    fig, ax = plt.subplots(figsize=(6.8, 2.8))

    for idx, traj in enumerate(trajectories):
        color = DEVICE_LINE_COLORS[idx % len(DEVICE_LINE_COLORS)]
        ax.plot(
            traj["ages"], traj["capacities"],
            label=traj["name"], color=color,
            linewidth=2.2, marker="o", markersize=4, solid_capstyle="round",
        )

    ax.axhline(80, color="#94a3b8", linestyle=(0, (3, 2)), linewidth=1.3, label="80% (conventional end-of-life)")

    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Capacity retained (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(left=0)
    ax.grid(axis="y", color="#dbe3ef", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower left", frameon=False, fontsize=8, ncol=2, bbox_to_anchor=(0, 1.02))
    fig.tight_layout(rect=[0, 0, 1, 0.88])

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
