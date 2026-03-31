import tempfile
from pathlib import Path
import matplotlib.pyplot as plt

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SERIES_COLORS = ["#1F4FBF", "#16A34A", "#D97706", "#C73E1D", "#6B7280", "#7C3AED", "#0891B2"]


def _base_fig(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor("white")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94A3B8")
    ax.spines["bottom"].set_color("#94A3B8")
    ax.tick_params(colors="#475467", labelsize=9)
    return fig, ax


def generate_blackout_chart(devices):
    chart_devices = [d for d in devices if d["annual_blackout_days"] > 0]
    if not chart_devices:
        return None

    n_dev = len(chart_devices)
    x = list(range(12))
    total_group_width = 0.78
    bar_w = total_group_width / max(n_dev, 1)

    fig, ax = _base_fig((8.3, 3.6))

    for i, d in enumerate(chart_devices):
        monthly = list(d["monthly_blackout_days"])
        offset = -total_group_width / 2 + (i + 0.5) * bar_w
        positions = [p + offset for p in x]
        bars = ax.bar(
            positions,
            monthly,
            width=bar_w * 0.92,
            label=f"{d['name']} ({d['annual_blackout_days']})",
            color=SERIES_COLORS[i % len(SERIES_COLORS)],
            edgecolor="white",
            linewidth=0.5,
        )
        # label annual total near final bar if there is any annual total
        if d["annual_blackout_days"] > 0:
            ax.text(
                positions[-1],
                monthly[-1] + 0.4,
                str(d["annual_blackout_days"]),
                ha="center",
                va="bottom",
                fontsize=8,
                color="#1F2937",
            )

    ax.set_title("Days with 0% battery depletion", fontsize=12, loc="left", pad=12, color="#1F2937", fontweight="bold")
    ax.text(
        0.0,
        1.02,
        "Monthly number of days when battery is expected to reach 0%.",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#667085",
        va="bottom",
    )
    ax.set_ylabel("Days")
    ax.set_xticks(x)
    ax.set_xticklabels(MONTHS)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    ymax = max(max(d["monthly_blackout_days"]) for d in chart_devices) if chart_devices else 1
    ax.set_ylim(0, max(3, ymax + 3))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.tight_layout()
    fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return tmp.name


def generate_profile_chart(devices, required_hours):
    fig, ax = _base_fig((8.3, 4.0))

    for i, d in enumerate(devices):
        y = list(d["monthly_operating_hours"])
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        ax.plot(MONTHS, y, label=d["name"], color=color, linewidth=2.3, marker="o", markersize=4)

    ax.axhline(required_hours, color="#111827", linewidth=2.0, linestyle="--")
    ax.axhline(0, color="#94A3B8", linewidth=1.2)

    ax.set_title("Annual operating profile", fontsize=12, loc="left", pad=12, color="#1F2937", fontweight="bold")
    ax.text(
        0.0,
        1.02,
        "Achievable daily operation compared to required operating profile.",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#667085",
        va="bottom",
    )
    ax.set_ylabel("Hours/day")
    ymax = max(max(d["monthly_operating_hours"]) for d in devices) if devices else required_hours
    ax.set_ylim(0, max(required_hours + 2, ymax + 2))
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.tight_layout()
    fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return tmp.name
