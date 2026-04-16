from __future__ import annotations

import base64
import io
from pathlib import Path

import jinja2
import matplotlib.pyplot as plt

from .assets.maps import generate_static_map
from core.i18n import month_labels

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = BASE_DIR / "assets"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DEVICE_COLORS = ["#0ea5e9", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#14b8a6", "#ec4899", "#84cc16"]
PRINT_CHART_WIDTH = 680


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _data_uri(path: str | Path | None, mime: str | None = None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    suffix = p.suffix.lower()
    if mime is None:
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
        }.get(suffix, "application/octet-stream")
    raw = p.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _fmt_hours(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}"


def _fmt_pct_hours(pct: float | None, hours: float | None) -> str:
    if pct is None or hours is None:
        return "N/A"
    return f"{float(pct):.0f}% (approx. {float(hours):.1f} h)"


def _fmt_pct(pct: float | None) -> str:
    if pct is None:
        return "N/A"
    return f"{float(pct):.0f}%"


def _border_status_from_days(days: int) -> str:
    if int(days or 0) == 0:
        return "success"
    if int(days or 0) <= 5:
        return "warning"
    return "danger"


def _border_status_from_result(result: str) -> str:
    value = str(result).upper()
    if value == "PASS":
        return "success"
    if value == "NEAR THRESHOLD":
        return "warning"
    return "danger"


def _border_status_from_battery(device: dict, total_pct: float | None) -> str:
    if total_pct is None:
        return "neutral"
    cutoff = float(device.get("cutoff_pct", 0) or 0)
    gap = float(total_pct) - cutoff
    if gap >= 25:
        return "success"
    if gap >= 10:
        return "warning"
    return "danger"


def _device_interpretation(device: dict, report_i18n: dict[str, str]) -> str:
    if str(device.get("result_class", "FAIL")).upper() == "PASS":
        return {
            "en": "System maintains required operation throughout the year.",
            "es": "El sistema mantiene la operación requerida durante todo el año.",
            "fr": "Le système maintient le fonctionnement requis tout au long de l’année.",
        }.get(report_i18n.get("report.html_lang", "en"), "System maintains required operation throughout the year.")
    if str(device.get("result_class", "FAIL")).upper() == "NEAR THRESHOLD":
        return {
            "en": "System is near the compliance threshold.",
            "es": "El sistema está cerca del umbral de conformidad.",
            "fr": "Le système est proche du seuil de conformité.",
        }.get(report_i18n.get("report.html_lang", "en"), "System is near the compliance threshold.")
    return {
        "en": "System does not sustain required operation under annual worst-case conditions.",
        "es": "El sistema no sostiene la operación requerida en las condiciones anuales más desfavorables.",
        "fr": "Le système ne maintient pas le fonctionnement requis dans les conditions annuelles les plus défavorables.",
    }.get(report_i18n.get("report.html_lang", "en"), "System does not sustain required operation under annual worst-case conditions.")


def _device_kpis(device: dict, report_i18n: dict[str, str]) -> list[dict]:
    lowest_battery_pct = device.get("lowest_battery_state_pct")
    cutoff_pct = float(device.get("cutoff_pct", 0) or 0)
    battery_value = _fmt_pct(lowest_battery_pct)
    if lowest_battery_pct is not None and abs(float(lowest_battery_pct) - cutoff_pct) < 0.05:
        battery_value = f"{battery_value} (cut-off level)"
    return [
        {
            "title": report_i18n["ui.required_daily_operation"],
            "value": f"{_fmt_hours(device.get('required_hours'))} {report_i18n['ui.hours_per_day_unit']}",
            "helper": report_i18n["ui.checked_operating_requirement"],
            "status": "neutral",
        },
        {
            "title": report_i18n["ui.worst_blackout_risk"],
            "value": f"{int(device.get('worst_blackout_risk', 0) or 0)} {report_i18n['ui.days_per_year_unit']}",
            "helper": report_i18n["ui.annual_days_full_depletion"],
            "status": _border_status_from_days(int(device.get("worst_blackout_risk", 0) or 0)),
        },
        {
            "title": report_i18n["ui.lowest_battery_state"],
            "value": battery_value,
            "helper": report_i18n["ui.lowest_level_reached"].format(month=device.get("annual_lowest_month_label", device.get("weakest_month_label", "the weakest month"))),
            "status": _border_status_from_battery(device, device.get("lowest_battery_state_pct")),
        },
        {
            "title": report_i18n["ui.annual_result"],
            "value": str(device.get("result_kpi_label", device.get("result_label", "FAIL"))),
            "helper": report_i18n["ui.annual_classification"],
            "status": _border_status_from_result(device.get("result_class", "FAIL")),
        },
    ]


def _chart_html_from_figure(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f'<img class="chart-image" src="data:image/png;base64,{encoded}" alt="Chart" />'


def _device_chart(device: dict, include_js: bool, report_i18n: dict[str, str]) -> str:
    month_ticks = month_labels(report_i18n.get("report.html_lang", "en"))
    generated = [float(v) for v in device.get("generated_pct_per_day", [])]
    consumed = [float(v) for v in device.get("consumed_pct_per_day", [])]
    empty_days = [float(v) for v in device.get("empty_battery_days_chart", [])]
    show_empty_days = any(float(v) > 0 for v in empty_days)
    x = list(range(len(MONTHS)))
    fig, ax = plt.subplots(figsize=(6.8, 2.05))
    ax.set_facecolor("#f8fbff")
    ax.plot(x, generated, color="#16a34a", linewidth=2.0, marker="o", markersize=3.2, label=report_i18n["ui.generated"], solid_capstyle="round")
    ax.plot(x, consumed, color="#f97316", linewidth=2.0, marker="o", markersize=3.2, label=report_i18n["ui.consumed"], solid_capstyle="round")
    ax2 = None
    if show_empty_days:
        ax2 = ax.twinx()
        ax2.bar(x, empty_days, width=0.40, color="#93c5fd", alpha=0.7, edgecolor="#2563eb", linewidth=0.7, label=report_i18n["ui.monthly_0_battery_days"])
    ax.set_ylabel(report_i18n["ui.percent_battery_per_day"])
    ax.set_xlabel(report_i18n["ui.month"])
    ax.set_ylim(bottom=0)
    ax.set_xlim(-0.3, len(MONTHS) - 0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(month_ticks)
    ax.grid(axis="y", color="#dbe3ef", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94a3b8")
    ax.spines["bottom"].set_color("#94a3b8")
    if ax2 is not None:
        ax2.set_ylabel(report_i18n["ui.monthly_0_battery_days"], color="#2563eb")
        ax2.set_ylim(0, 30)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_color("#2563eb")
        ax2.tick_params(axis="y", labelsize=8, colors="#2563eb")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = (ax2.get_legend_handles_labels() if ax2 is not None else ([], []))
    ax.legend(lines + lines2, labels + labels2, loc="lower left", frameon=False, ncol=3, fontsize=8, bbox_to_anchor=(0, 1.02))
    ax.tick_params(axis="x", labelsize=8, rotation=0, colors="#475467")
    ax.tick_params(axis="y", labelsize=8, colors="#475467")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return _chart_html_from_figure(fig)


def _blackout_chart(data: dict, include_js: bool, report_i18n: dict[str, str]) -> str:
    month_ticks = month_labels(report_i18n.get("report.html_lang", "en"))
    devices = [d for d in data.get("devices", []) if int(d.get("annual_blackout_days", 0) or 0) > 0]
    fig, ax = plt.subplots(figsize=(6.8, 2.3))
    positions = list(range(len(MONTHS)))
    if devices:
        width = 0.8 / max(len(devices), 1)
        for idx, device in enumerate(devices):
            shifted = [p - 0.4 + width / 2 + idx * width for p in positions]
            ax.bar(
                shifted,
                device.get("monthly_blackout_days", [0] * 12),
                width=width,
                label=device.get("name", "Device"),
                color=DEVICE_COLORS[idx % len(DEVICE_COLORS)],
            )
    ax.set_xlim(-0.6, len(MONTHS) - 0.4)
    ax.set_xticks(positions)
    ax.set_xticklabels(month_ticks)
    ax.set_ylabel(report_i18n["ui.days"])
    ax.set_xlabel(report_i18n["ui.month"])
    ax.set_title(report_i18n["report.monthly_0_battery_days"], loc="left", fontsize=11, fontweight="bold")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#dbe3ef", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=2)
    ax.tick_params(axis="x", labelsize=8, rotation=0)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    return _chart_html_from_figure(fig)


def _profile_chart(data: dict, include_js: bool, report_i18n: dict[str, str]) -> str:
    month_ticks = month_labels(report_i18n.get("report.html_lang", "en"))
    fig, ax = plt.subplots(figsize=(6.8, 2.45))
    x = list(range(len(MONTHS)))
    required = float(data.get("required_hours", 0) or 0)
    ymax_candidates = [required + 2]
    for device in data.get("devices", []):
        ymax_candidates.extend(float(v) for v in device.get("monthly_operating_hours", [0] * 12))
    ymax = max(6.0, min(24.5, max(ymax_candidates) + 1.0))

    ax.set_facecolor("#f8fbff")
    ax.axhspan(required, ymax, color="#dcfce7", alpha=0.55, zorder=0)
    ax.axhspan(max(required - 0.5, 0), required, color="#fef3c7", alpha=0.55, zorder=0)
    ax.axhspan(0, max(required - 0.5, 0), color="#fee2e2", alpha=0.42, zorder=0)

    for idx, device in enumerate(data.get("devices", [])):
        ax.plot(
            x,
            device.get("monthly_operating_hours", [0] * 12),
            label=device.get("name", "Device"),
            color=DEVICE_COLORS[idx % len(DEVICE_COLORS)],
            linewidth=2.2,
            marker="o",
            markersize=3.4,
            solid_capstyle="round",
        )
    ax.axhline(required, color="#2563eb", linestyle=(0, (3, 2)), linewidth=1.8, label=report_i18n["ui.defined_compliance_target"])
    ax.set_ylabel(report_i18n["ui.operating_hours_per_day"])
    ax.set_xlabel(report_i18n["ui.month"])
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.3, len(MONTHS) - 0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(month_ticks)
    ax.grid(axis="y", color="#dbe3ef", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94a3b8")
    ax.spines["bottom"].set_color("#94a3b8")
    ax.legend(loc="lower left", frameon=False, fontsize=8, ncol=2, bbox_to_anchor=(0, 1.02))
    ax.tick_params(axis="x", labelsize=8, rotation=0, colors="#475467")
    ax.tick_params(axis="y", labelsize=8, colors="#475467")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return _chart_html_from_figure(fig)


def build_report_context(data: dict) -> dict:
    context = dict(data)
    context["logo_sala"] = _data_uri(ASSETS_DIR / "sala_logo.png")
    context["logo_jrc"] = _data_uri(ASSETS_DIR / "jrc_logo.jpg")
    context["logo_s4ga"] = _data_uri(ASSETS_DIR / "s4ga_wordmark.svg")
    context["logo_avlite"] = _data_uri(ASSETS_DIR / "avlite_wordmark.svg")
    context["map_image"] = _data_uri(generate_static_map(data["lat"], data["lon"], width=900, height=420, zoom=11))
    context["report_css"] = _read_text(STATIC_DIR / "report.css")
    context["print_css"] = _read_text(STATIC_DIR / "print.css")

    include_js = True
    context["blackout_chart_html"] = _blackout_chart(data, include_js, context["i18n"])
    include_js = False
    context["profile_chart_html"] = _profile_chart(data, include_js, context["i18n"])
    for idx, device in enumerate(context.get("devices", []), start=1):
        device["kpis"] = _device_kpis(device, context["i18n"])
        device["interpretation_line"] = _device_interpretation(device, context["i18n"])
        diffs = [abs(float(g) - float(c)) for g, c in zip(device.get("generated_pct_per_day", []), device.get("consumed_pct_per_day", []))]
        device["generated_consumed_close"] = bool(diffs) and max(diffs) <= 2.0
        device["compact_chart_mode"] = False
        device["annual_result_status"] = _border_status_from_result(device.get("result_class", "FAIL"))
        device["worst_blackout_status"] = _border_status_from_days(int(device.get("worst_blackout_risk", 0) or 0))
        device["chart_html"] = _device_chart(device, include_js, context["i18n"])
        device["page_number"] = 3 + idx
        include_js = False
    return context


def render_report_html(data: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.html")
    return template.render(report=build_report_context(data))
