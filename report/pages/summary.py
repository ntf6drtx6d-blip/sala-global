print("SUMMARY FILE LOADING")

from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.lib import colors

from ..styles import (
    TITLE, BODY, SMALL, BOLD, BIG,
    LINE, WHITE,
    BLUE_SOFT, BLUE_BORDER,
    RED_SOFT, RED_BORDER,
    GREEN_SOFT, GREEN_BORDER,
)


PAGE_WIDTH = 510
LEFT_COL = 240
GAP = 18
RIGHT_COL = PAGE_WIDTH - LEFT_COL - GAP

MAP_HEIGHT = 250
CHART_HEIGHT = 165
FULL_CHART_WIDTH = PAGE_WIDTH


# -------------------------
# HELPERS
# -------------------------
def _safe(value, default="—"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _overall_is_pass(data):
    return data.get("accent") == "green"


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


# -------------------------
# LEFT CARD
# -------------------------
def _build_left_card(data):
    map_block = _image_or_placeholder(
        data.get("map_image_path"),
        LEFT_COL - 28,
        MAP_HEIGHT,
        "Map preview"
    )

    table = Table(
        [[
            Paragraph("Study point", SMALL),
            Paragraph(f"<b>{_safe(data.get('airport_name'))}</b>", BODY),
            Spacer(1, 6),
            map_block,
            Spacer(1, 6),
            Paragraph(_safe(data.get("coordinates")), SMALL),
        ]],
        colWidths=[LEFT_COL],
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))

    return table


# -------------------------
# CONCLUSION
# -------------------------
def _build_conclusion(data):
    pass_state = _overall_is_pass(data)

    bg = GREEN_SOFT if pass_state else RED_SOFT
    border = GREEN_BORDER if pass_state else RED_BORDER

    table = Table(
        [[
            Paragraph("Overall conclusion", SMALL),
            Paragraph(_safe(data.get("overall_conclusion_title")), BOLD),
            Paragraph(_safe(data.get("overall_conclusion_text")), BODY),
        ]],
        colWidths=[RIGHT_COL],
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))

    return table


# -------------------------
# KPIs
# -------------------------
def _build_kpis(data):
    kpi_col = RIGHT_COL / 2 - 6

    kpi1 = Table(
        [[
            Paragraph("Daily requirement", SMALL),
            Paragraph(_safe(data.get("required_operation")), BIG),
        ]]],
        colWidths=[kpi_col],
    )

    kpi1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    kpi2 = Table(
        [[
            Paragraph("Worst blackout risk", SMALL),
            Paragraph(_safe(data.get("worst_blackout_risk")), BIG),
        ]]],
        colWidths=[kpi_col],
    )

    kpi2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    wrapper = Table([[kpi1, kpi2]], colWidths=[kpi_col, kpi_col])

    wrapper.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    return wrapper


# -------------------------
# PERFORMANCE STRIP
# -------------------------
def _build_performance(data):
    table = Table(
        [[
            Paragraph("Device", SMALL),
            Paragraph(_safe(data.get("device_name")), BOLD),
            Paragraph(_safe(data.get("achievable_worst_month")), SMALL),
            Paragraph(_safe(data.get("battery_reserve")), SMALL),
        ]]],
        colWidths=[RIGHT_COL],
    )

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    return table


# -------------------------
# CHART BLOCK
# -------------------------
def _build_chart(title, image_path):
    chart = _image_or_placeholder(
        image_path,
        FULL_CHART_WIDTH - 24,
        CHART_HEIGHT,
        "Chart"
    )

    table = Table(
        [[
            Paragraph(title, BOLD),
            Spacer(1, 6),
            chart
        ]],
        colWidths=[FULL_CHART_WIDTH],
    )

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    return table


# -------------------------
# MAIN
# -------------------------
def build_summary(data):
    story = []

    story.append(Paragraph("Management Summary", SMALL))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 16))

    left = _build_left_card(data)

    right = Table(
        [
            [_build_conclusion(data)],
            [Spacer(1, 8)],
            [_build_kpis(data)],
            [Spacer(1, 8)],
            [_build_performance(data)],
        ],
        colWidths=[RIGHT_COL],
    )

    right.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    main = Table([[left, right]], colWidths=[LEFT_COL, RIGHT_COL])

    main.setStyle(TableStyle([
        ("RIGHTPADDING", (0, 0), (0, 0), GAP),
    ]))

    story.append(main)
    story.append(Spacer(1, 16))

    story.append(_build_chart("Monthly empty-battery days", data.get("monthly_chart_path")))
    story.append(Spacer(1, 12))
    story.append(_build_chart("Annual operating profile", data.get("annual_profile_chart_path")))

    story.append(PageBreak())

    return story
