from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from ..styles import (
    TITLE_EYEBROW,
    SECTION_TITLE,
    CARD_LABEL,
    BODY,
    BODY_SMALL,
    BODY_BOLD,
    BIG_VALUE,
    CONCLUSION_TITLE,
    RECOMMENDATION,
    NAVY,
    TEXT,
    MUTED,
    LINE,
    WHITE,
    SOFT_BG,
    BLUE_SOFT,
    BLUE_BORDER,
    RED_SOFT,
    RED_BORDER,
    GREEN_SOFT,
    GREEN_BORDER,
    GOLD_SOFT,
    GOLD_BORDER,
)

def _accent_box(accent):
    if accent == "green":
        return GREEN_SOFT, GREEN_BORDER
    if accent == "gold":
        return GOLD_SOFT, GOLD_BORDER
    return RED_SOFT, RED_BORDER


def build_summary(data):
    story = []

    story.append(Paragraph("Management summary", TITLE_EYEBROW))
    story.append(Paragraph("Feasibility result", SECTION_TITLE))
    story.append(Spacer(1, 12))

    # left context card
    map_placeholder = Table(
        [[Paragraph("MAP PLACEHOLDER", BODY_SMALL)]],
        colWidths=[190],
        rowHeights=[210],
    )
    map_placeholder.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F5")),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    left_card = Table(
        [[
            Paragraph("AIRPORT / STUDY POINT", CARD_LABEL),
            Paragraph(data["airport_name"], BODY_BOLD),
            map_placeholder,
            Paragraph(data["coordinates"], BODY),
            Paragraph("Study location used for PVGIS simulation.", BODY_SMALL),
        ]],
        colWidths=[210],
    )
    left_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    bg, border = _accent_box(data["accent"])

    conclusion_card = Table(
        [[
            Paragraph("OVERALL CONCLUSION", CARD_LABEL),
            Paragraph(data["overall_conclusion_title"], CONCLUSION_TITLE),
            Paragraph(data["overall_conclusion_text"], BODY),
        ]],
        colWidths=[250],
    )
    conclusion_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    # KPI row
    kpi1 = Table(
        [[
            Paragraph("REQUIRED OPERATION", CARD_LABEL),
            Paragraph(data["required_operation"], BIG_VALUE),
            Paragraph("Applied to all devices", BODY_SMALL),
        ]],
        colWidths=[118],
    )
    kpi1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    kpi2_bg, kpi2_border = _accent_box("green" if data["worst_blackout_risk"].startswith("0 ") else "red")

    kpi2 = Table(
        [[
            Paragraph("WORST BLACKOUT RISK", CARD_LABEL),
            Paragraph(data["worst_blackout_risk"], BIG_VALUE),
            Paragraph(data["worst_blackout_pct"], BODY_SMALL),
        ]],
        colWidths=[118],
    )
    kpi2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), kpi2_bg),
        ("BOX", (0, 0), (-1, -1), 1, kpi2_border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    kpi_row = Table([[kpi1, kpi2]], colWidths=[122, 122])
    kpi_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    interpretation = Table(
        [[
            Paragraph("INTERPRETATION", CARD_LABEL),
            Paragraph(data["interpretation"], BODY),
        ]],
        colWidths=[250],
    )
    interpretation.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    recommendation = Table(
        [[
            Paragraph("RECOMMENDED ACTION", CARD_LABEL),
            Paragraph(data["recommendation"], RECOMMENDATION),
        ]],
        colWidths=[250],
    )
    recommendation.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    right_stack = [
        conclusion_card,
        Spacer(1, 14),
        kpi_row,
        Spacer(1, 14),
        interpretation,
        Spacer(1, 16),
        recommendation,
    ]

    main_grid = Table(
        [[left_card, right_stack]],
        colWidths=[220, 250],
    )
    main_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(main_grid)
    story.append(Spacer(1, 16))

    methodology_strip = Table(
        [[Paragraph(data["methodology_note"], BODY_SMALL)]],
        colWidths=[470],
    )
    methodology_strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(methodology_strip)
    story.append(PageBreak())

    return story
