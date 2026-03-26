import os
import tempfile
import requests
import matplotlib.pyplot as plt


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def generate_static_map(lat, lon, zoom=11, size=(700, 500)):
    url = (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lon}&zoom={zoom}"
        f"&size={size[0]}x{size[1]}"
        f"&markers={lat},{lon},red-pushpin"
    )

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        r = requests.get(url, timeout=4, headers={"User-Agent": "SALA-Feasibility-Study/1.0"})
        r.raise_for_status()

        with open(tmp.name, "wb") as f:
            f.write(r.content)

        return tmp.name
    except Exception:
        return generate_fallback_map(lat, lon)


def generate_fallback_map(lat, lon):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title("Study point")
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.grid(True, alpha=0.25)
    ax.scatter([0], [0], s=180, marker="o")
    ax.annotate(
        f"Lat {float(lat):.4f}\nLon {float(lon):.4f}",
        xy=(0, 0),
        xytext=(0.15, 0.2),
        textcoords="data",
    )
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
    plt.close(fig)

    return tmp.name


def generate_monthly_chart(result):
    data = result.get("empty_battery_days_by_month")

    if not isinstance(data, (list, tuple)) or len(data) != 12:
        return None

    values = [float(x) for x in data]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    bars = ax.bar(MONTHS, values, color="#DCE8DF", edgecolor="#DCE8DF")

    for i, v in enumerate(values):
        if v <= 0:
            bars[i].set_color("#EEF4FF")
            bars[i].set_edgecolor("#D6E4FF")
        elif v <= 3:
            bars[i].set_color("#FFF7DB")
            bars[i].set_edgecolor("#F5C451")
        else:
            bars[i].set_color("#FEF3F2")
            bars[i].set_edgecolor("#F7C7C1")

    ax.axhline(0, linewidth=1, color="#344054")
    ax.set_title("Monthly empty-battery days", loc="left", pad=12, fontsize=16, fontweight="bold")
    ax.text(
        0.0,
        1.03,
        "Expected days per month with battery at 0%.",
        transform=ax.transAxes,
        fontsize=10,
        va="bottom",
        color="#5B7083",
    )
    ax.set_ylabel("Days")
    ax.set_xlabel("Month")
    ax.set_ylim(0, 31)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.5)
    ax.spines["bottom"].set_linewidth(1.2)
    fig.tight_layout()
    fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return tmp.name


def generate_annual_profile_chart(result, required_hours):
    achieved = result.get("hours")

    if not isinstance(achieved, (list, tuple)) or len(achieved) != 12:
        return None

    achieved = [float(x) for x in achieved]
    required_hours = float(required_hours)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    fig, ax = plt.subplots(figsize=(7.8, 3.8))

    ax.bar(MONTHS, achieved, alpha=0.18, width=0.9, color="#16A34A")
    ax.plot(MONTHS, achieved, marker="o", linewidth=2.4, color="#5B7AA6")
    ax.axhline(required_hours, linestyle="--", linewidth=2.2, color="#111827")
    ax.axhline(0, linewidth=1, color="#475467")
    ax.plot([-0.45, -0.45], [0, required_hours], linewidth=2.2, color="#111827")
    ax.text(
        -0.62,
        required_hours,
        f"{required_hours:.1f} hrs/day\nrequired",
        va="center",
        ha="right",
        fontsize=10,
        fontweight="bold",
        color="#111827",
    )
    ax.text(
        -0.62,
        required_hours + 0.45,
        "✈",
        va="center",
        ha="right",
        fontsize=12,
        color="#111827",
    )

    ymax = max(max(achieved), required_hours) + 2
    ax.set_title("Annual operating profile", loc="left", pad=12, fontsize=16, fontweight="bold")
    ax.text(
        0.0,
        1.03,
        "Bars = achieved solar-supported operation | Dashed line = required airport operation",
        transform=ax.transAxes,
        fontsize=10,
        va="bottom",
        color="#5B7083",
    )
    ax.set_ylabel("Operating hours/day")
    ax.set_xlabel("Month")
    ax.set_ylim(0, ymax)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(2)
    ax.spines["bottom"].set_linewidth(1.5)
    fig.tight_layout()
    fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
    plt.close(fig)

    return tmp.name


def generate_all_assets(loc, results, required_hours):
    lat = loc.get("lat")
    lon = loc.get("lon")

    if not results:
        return None, None, None

    worst = max(
        results.values(),
        key=lambda r: float(r.get("overall_empty_battery_pct", 0) or 0)
    )

    try:
        map_path = generate_static_map(lat, lon)
    except Exception:
        map_path = generate_fallback_map(lat, lon)

    try:
        monthly = generate_monthly_chart(worst)
    except Exception:
        monthly = None

    try:
        annual = generate_annual_profile_chart(worst, required_hours)
    except Exception:
        annual = None

    return map_path, monthly, annual
