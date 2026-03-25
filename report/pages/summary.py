from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm

from ..styles import (
    TITLE, BODY, SMALL, BOLD, BIG,
    LINE, WHITE, SOFT_BG,
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


def _safe(value, default="—"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _risk_is_pass(data):
    risk = str(data.get("worst_blackout_risk", "")).strip().lower()
    return risk.startswith("0 ")


def _overall_is_pass(data):
    if "accent" in data:
        return data.get("accent") == "green"
    return _risk_is_pass(data)


def _image_or_placeholder(path, width, height, label):
    """
    Renders image if path exists in data, otherwise shows styled placeholder.
    """
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


def _build_left_card(data):
    airport_name = _safe(data.get("airport_name"))
    coords = _safe(data.get("coordinates"))
    map_note = _safe(
        data.get("map_note"),
        "Verified airport location used for the feasibility study."
    )

    map_block = _image_or_placeholder(
        data.get("map_image_path"),
        LEFT_COL - 28,
        MAP_HEIGHT,
        "Map preview"
    )

    left_card = Table(
        [[
            Paragraph("Study point", SMALL),
            Paragraph(f"<b>{airport_name}</b>", BODY),
            Spacer(1, 6),
            map_block,
            Spacer(1, 6),
            Paragraph(coords, SMALL),
            Paragraph(map_note, SMALL),
        ]]],
        colWidths=[LEFT_COL],
    )
    left_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return left_card


def _build_conclusion(data):
    pass_state = _overall_is_pass(data)
    conclusion_bg = GREEN_SOFT if pass_state else RED_SOFT
    conclusion_border = GREEN_BORDER if pass_state else RED_BORDER

    title = _safe(
        data.get("overall_conclusion_title"),
        "System meets the required operating profile." if pass_state
        else "System does not meet the required operating profile."
    )
    text = _safe(
        data.get("overall_conclusion_text"),
        "The selected operating profile is supported year-round." if pass_state
        else "The selected operating profile is not fully supported year-round."
    )

    conclusion = Table(
        [[
            Paragraph("Overall conclusion", SMALL),
            Paragraph(title, BOLD),
            Paragraph(text, BODY),
        ]]],
        colWidths=[RIGHT_COL],
    )
    conclusion.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), conclusion_bg),
        ("BOX", (0, 0), (-1, -1), 1, conclusion_border),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return conclusion


def _build_kpis(data):
    kpi_gap = 12
    kpi_col = (RIGHT_COL - kpi_gap) / 2

    required_operation = _safe(data.get("required_operation"))
    custom_operation = _safe(data.get("custom_operation"), "")

    kpi1_rows = [
        Paragraph("Daily operating requirement checked", SMALL),
        Paragraph(required_operation, BIG),
    ]
    if custom_operation and custom_operation != "—":
        kpi1_rows.append(Paragraph(f"Custom operation<br/>{custom_operation}", SMALL))
    else:
        kpi1_rows.append(Paragraph(
            "This is the daily operating requirement used as the acceptance threshold in the study.",
            SMALL
        ))

    kpi1 = Table([[x] for x in kpi1_rows], colWidths=[kpi_col])
    kpi1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    risk_pass = _risk_is_pass(data)
    kpi2_bg = GREEN_SOFT if risk_pass else RED_SOFT
    kpi2_border = GREEN_BORDER if risk_pass else RED_BORDER

    blackout_value = _safe(data.get("worst_blackout_risk")).replace(" days/year", "<br/>days/year")
    blackout_pct = _safe(
        data.get("worst_blackout_pct"),
        "Annual blackout exposure found in the checked device set."
    )

    kpi2 = Table(
        [[
            Paragraph("Worst blackout risk", SMALL),
            Paragraph(blackout_value, BIG),
            Paragraph(blackout_pct, SMALL),
        ]]],
        colWidths=[kpi_col],
    )
    kpi2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), kpi2_bg),
        ("BOX", (0, 0), (-1, -1), 1, kpi2_border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    kpis = Table(
        [[kpi1, kpi2]],
        colWidths=[kpi_col, kpi_col],
    )
    kpis.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return kpis


def _build_performance_strip(data):
    """
    Extra strip to include 'pass / hours / reserve' feel from page 2 of the app.
    """
    device_name = _safe(data.get("device_name"))
    worst_month_hours = _safe(data.get("achievable_worst_month"))
    battery_reserve = _safe(data.get("battery_reserve"))
    requirement_status = _safe(data.get("requirement_status"), "Meets requirement")

    strip_col_gap = 10
    strip_col = (RIGHT_COL - 2 * strip_col_gap) / 3

    c1 = Table([[
        Paragraph("Selected device", SMALL),
        Paragraph(device_name, BOLD),
    ]], colWidths=[strip_col])

    c2 = Table([[
        Paragraph("Achievable (worst month)", SMALL),
        Paragraph(worst_month_hours, BOLD),
    ]], colWidths=[strip_col])

    c3 = Table([[
        Paragraph("Battery-only reserve", SMALL),
        Paragraph(battery_reserve, BOLD),
    ]], colWidths=[strip_col])

    for c in (c1, c2, c3):
        c.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))

    title = Table([[
        Paragraph("Device-level performance", SMALL),
        Paragraph(requirement_status, BOLD),
    ]], colWidths=[RIGHT_COL])
    title.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    row = Table(
        [[c1, c2, c3]],
        colWidths=[strip_col, strip_col, strip_col],
    )
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    block = Table(
        [[title], [Spacer(1, 6)], [row]],
        colWidths=[RIGHT_COL],
        rowHeights=[None, 6, None]
    )
    block.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return block


def _build_interpretation(data):
    interpretation = Table(
        [[
            Paragraph("Interpretation", SMALL),
            Paragraph(_safe(data.get("interpretation")), BODY),
        ]]],
        colWidths=[RIGHT_COL],
    )
    interpretation.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return interpretation


def _build_action(data):
    action = Table(
        [[
            Paragraph("Recommended action", SMALL),
            Paragraph(_safe(data.get("recommendation")), BOLD),
        ]]],
        colWidths=[RIGHT_COL],
    )
    action.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return action


def _build_chart_block(title, subtitle, image_path, placeholder_label):
    chart = _image_or_placeholder(
        image_path,
        FULL_CHART_WIDTH - 24,
        CHART_HEIGHT,
        placeholder_label
    )

    card = Table(
        [[
            Paragraph(title, BOLD),
            Paragraph(subtitle, SMALL),
            Spacer(1, 8),
            chart,
        ]]],
        colWidths=[FULL_CHART_WIDTH],
    )
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return card


def build_summary(data):
    story = []

    story.append(Paragraph("Management Summary", SMALL))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 16))

    left_card = _build_left_card(data)
    conclusion = _build_conclusion(data)
    kpis = _build_kpis(data)
    performance = _build_performance_strip(data)
    interpretation = _build_interpretation(data)
    action = _build_action(data)

    right_column = Table(
        [
            [conclusion],
            [Spacer(1, 0)],
            [kpis],
            [Spacer(1, 0)],
            [performance],
            [Spacer(1, 0)],
            [interpretation],
            [Spacer(1, 0)],
            [action],
        ],
        colWidths=[RIGHT_COL],
        rowHeights=[None, 12, None, 12, None, 12, None, 12, None],
    )
    right_column.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    main_grid = Table(
        [[left_card, right_column]],
        colWidths=[LEFT_COL, RIGHT_COL],
    )
    main_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), GAP),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(main_grid)
    story.append(Spacer(1, 16))

    footer_strip = Table(
        [[Paragraph(_safe(data.get("methodology_note")), SMALL)]],
        colWidths=[PAGE_WIDTH],
    )
    footer_strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(footer_strip)

    story.append(Spacer(1, 18))

    monthly_chart = _build_chart_block(
        "Monthly empty-battery days",
        "Shows in which months the battery is expected to reach 0%, and for how many days.",
        data.get("monthly_chart_path"),
        "Monthly empty-battery days chart"
    )
    story.append(monthly_chart)

    story.append(Spacer(1, 14))

    annual_chart = _build_chart_block(
        "Annual operating profile",
        "12-month solar performance from January to December.",
        data.get("annual_profile_chart_path"),
        "Annual operating profile chart"
    )
    story.append(annual_chart)

    story.append(PageBreak())
    return story
