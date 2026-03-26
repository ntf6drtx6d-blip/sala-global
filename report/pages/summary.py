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


def _safe(value, default="-"):
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

    box = Table(
        [[Paragraph(label, SMALL)]],
        colWidths=[width],
        rowHeights=[height],
    )
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F5")),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return box


def _stacked_table(items, width, style=None, row_heights=None):
    table = Table(
        [[item] for item in items],
        colWidths=[width],
        rowHeights=row_heights,
    )
    if style:
        table.setStyle(TableStyle(style))
    return table


def _build_left_card(data):
    map_block = _image_or_placeholder(
        data.get("map_image_path"),
        LEFT_COL - 28,
        MAP_HEIGHT,
        "Map preview"
    )

    table = _stacked_table(
        [
            Paragraph("Study point", SMALL),
            Paragraph(f"<b>{_safe(data.get('airport_name'))}</b>", BODY),
            Spacer(1, 6),
            map_block,
            Spacer(1, 6),
            Paragraph(_safe(data.get("coordinates")), SMALL),
        ],
        LEFT_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )
    return table


def _build_conclusion(data):
    pass_state = _overall_is_pass(data)

    bg = GREEN_SOFT if pass_state else RED_SOFT
    border = GREEN_BORDER if pass_state else RED_BORDER

    table = _stacked_table(
        [
            Paragraph("Overall conclusion", SMALL),
            Paragraph(_safe(data.get("overall_conclusion_title")), BOLD),
            Paragraph(_safe(data.get("overall_conclusion_text")), BODY),
        ],
        RIGHT_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 1, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )
    return table


def _build_kpis(data):
    kpi_col = int((RIGHT_COL - 12) / 2)

    kpi1 = _stacked_table(
        [
            Paragraph("Daily requirement", SMALL),
            Paragraph(_safe(data.get("required_operation")), BIG),
        ],
        kpi_col,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
            ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ],
    )

    kpi2 = _stacked_table(
        [
            Paragraph("Worst blackout risk", SMALL),
            Paragraph(_safe(data.get("worst_blackout_risk")), BIG),
            Paragraph(_safe(data.get("worst_blackout_pct"), ""), SMALL),
        ],
        kpi_col,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ],
    )

    wrapper = Table(
        [[kpi1, kpi2]],
        colWidths=[kpi_col, kpi_col],
    )
    wrapper.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return wrapper


def _build_performance(data):
    device_name = _safe(data.get("device_name"))
    worst_month = _safe(data.get("achievable_worst_month"))
    reserve = _safe(data.get("battery_reserve"))

    table = _stacked_table(
        [
            Paragraph("Selected device", SMALL),
            Paragraph(device_name, BOLD),
            Paragraph(f"Worst month performance: {worst_month}", SMALL),
            Paragraph(f"Battery-only reserve: {reserve}", SMALL),
        ],
        RIGHT_COL,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )
    return table


def _build_chart(title, image_path):
    chart = _image_or_placeholder(
        image_path,
        FULL_CHART_WIDTH - 24,
        CHART_HEIGHT,
        "Chart"
    )

    table = _stacked_table(
        [
            Paragraph(title, BOLD),
            Spacer(1, 6),
            chart,
        ],
        FULL_CHART_WIDTH,
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
    return table


def build_summary(data):
    story = []

    story.append(Paragraph("Management Summary", SMALL))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 16))

    left = _build_left_card(data)

    right = _stacked_table(
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
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )

    main = Table(
        [[left, right]],
        colWidths=[LEFT_COL, RIGHT_COL],
    )
    main.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("RIGHTPADDING", (0, 0), (0, 0), GAP),
    ]))

    story.append(main)
    story.append(Spacer(1, 16))

    story.append(_build_chart("Monthly empty-battery days", data.get("monthly_chart_path")))
    story.append(Spacer(1, 12))
    story.append(_build_chart("Annual operating profile", data.get("annual_profile_chart_path")))

    return story
