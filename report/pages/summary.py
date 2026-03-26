from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib import colors

from ..styles import (
    TITLE, SECTION, BODY, SMALL, BOLD, BIG,
    LINE, WHITE, BLUE_SOFT, BLUE_BORDER,
    RED_SOFT, RED_BORDER, GREEN_SOFT, GREEN_BORDER, GOLD_SOFT, GOLD_BORDER
)

PAGE_WIDTH = 510
LEFT_COL = 210
GAP = 16
RIGHT_COL = PAGE_WIDTH - LEFT_COL - GAP
MAP_HEIGHT = 200
CHART_HEIGHT = 120
CHART_COL = int((PAGE_WIDTH - 12) / 2)


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _conclusion_colors(accent):
    if accent == "green":
        return GREEN_SOFT, GREEN_BORDER
    if accent == "gold":
        return GOLD_SOFT, GOLD_BORDER
    return RED_SOFT, RED_BORDER


def _image_or_placeholder(path, width, height, label):
    if path:
        try:
            img = Image(path)
            img._restrictSize(width, height)
            return img
        except Exception:
            pass

    box = Table([[Paragraph(label, SMALL)]], colWidths=[width], rowHeights=[height])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F5")),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return box


def _stack(items, width, style=None):
    t = Table([[x] for x in items], colWidths=[width])
    if style:
        t.setStyle(TableStyle(style))
    return t


def _build_left_card(data):
    map_block = _image_or_placeholder(
        data.get("map_image_path"),
        LEFT_COL - 24,
        MAP_HEIGHT,
        "Map preview"
    )

    return _stack(
        [
            Paragraph("Study point", SMALL),
            Paragraph(f"<b>{_safe(data.get('airport_name'))}</b>", BOLD),
            Spacer(1, 6),
            map_block,
            Spacer(1, 6),
            Paragraph(_safe(data.get("coordinates")), SMALL),
        ],
        LEFT_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )


def _build_conclusion(data):
    bg, border = _conclusion_colors(data.get("accent"))

    return _stack(
        [
            Paragraph("Overall conclusion", SMALL),
            Paragraph(_safe(data.get("overall_conclusion_title")), BOLD),
            Paragraph(_safe(data.get("overall_conclusion_text")), BODY),
            Spacer(1, 4),
            Paragraph(_safe(data.get("executive_summary")), BODY),
        ],
        RIGHT_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 1, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ],
    )


def _build_kpis(data):
    kpi_col = int((RIGHT_COL - 10) / 2)

    left = _stack(
        [
            Paragraph("Daily requirement", SMALL),
            Paragraph(_safe(data.get("required_operation")), BIG),
        ],
        kpi_col,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
            ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ],
    )

    right = _stack(
        [
            Paragraph("Worst blackout risk", SMALL),
            Paragraph(_safe(data.get("worst_blackout_risk")), BIG),
            Paragraph(_safe(data.get("worst_blackout_pct")), SMALL),
        ],
        kpi_col,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ],
    )

    t = Table([[left, right]], colWidths=[kpi_col, kpi_col])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _build_performance(data):
    return _stack(
        [
            Paragraph("Selected device", SMALL),
            Paragraph(_safe(data.get("device_name")), BOLD),
            Paragraph(f"Engine: {_safe(data.get('engine_name'))}", SMALL),
            Paragraph(f"Worst month: {_safe(data.get('worst_month_name'))}", SMALL),
            Paragraph(f"Worst month performance: {_safe(data.get('worst_month_hours'))}", SMALL),
            Paragraph(f"Battery-only reserve: {_safe(data.get('battery_reserve'))}", SMALL),
        ],
        RIGHT_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ],
    )


def _build_chart(title, image_path):
    chart = _image_or_placeholder(image_path, CHART_COL - 24, CHART_HEIGHT, "Chart")
    return _stack(
        [
            Paragraph(title, BOLD),
            Spacer(1, 5),
            chart,
        ],
        CHART_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ],
    )


def build_summary(data):
    story = []

    story.append(Paragraph("Management Summary", SMALL))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 14))

    left = _build_left_card(data)

    right = _stack(
        [
            _build_conclusion(data),
            Spacer(1, 8),
            _build_kpis(data),
            Spacer(1, 8),
            _build_performance(data),
        ],
        RIGHT_COL,
        style=[
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ],
    )

    top = Table([[left, right]], colWidths=[LEFT_COL, RIGHT_COL])
    top.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("RIGHTPADDING", (0, 0), (0, 0), GAP),
    ]))
    story.append(top)
    story.append(Spacer(1, 12))

    c1 = _build_chart("Monthly empty-battery days", data.get("monthly_chart_path"))
    c2 = _build_chart("Annual operating profile", data.get("annual_profile_chart_path"))

    charts = Table([[c1, c2]], colWidths=[CHART_COL, CHART_COL])
    charts.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(charts)
    story.append(PageBreak())
    return story
