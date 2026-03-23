from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from ..styles import (
    TITLE, BODY, SMALL, BOLD, BIG,
    LINE, WHITE, SOFT_BG,
    BLUE_SOFT, BLUE_BORDER,
    RED_SOFT, RED_BORDER,
    GREEN_SOFT, GREEN_BORDER,
)


PAGE_WIDTH = 510
LEFT_COL = 220
RIGHT_COL = PAGE_WIDTH - LEFT_COL - 16


def _risk_is_pass(data):
    risk = str(data.get("worst_blackout_risk", ""))
    return risk.startswith("0 ")


def _map_placeholder():
    t = Table(
        [[Paragraph("Map preview", SMALL)]],
        colWidths=[LEFT_COL - 24],
        rowHeights=[210],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F5")),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def build_summary(data):
    story = []

    story.append(Paragraph("Management Summary", SMALL))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 14))

    # LEFT BLOCK
    left_card = Table(
        [[
            Paragraph("Airport / Study Point", SMALL),
            Paragraph(f"<b>{data['airport_name']}</b>", BODY),
            _map_placeholder(),
            Paragraph("Study location used for solar resource assessment.", SMALL),
        ]],
        colWidths=[LEFT_COL],
    )
    left_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    # CONCLUSION
    pass_state = data.get("accent") == "green"
    conclusion_bg = GREEN_SOFT if pass_state else RED_SOFT
    conclusion_border = GREEN_BORDER if pass_state else RED_BORDER

    conclusion = Table(
        [[
            Paragraph("Overall conclusion", SMALL),
            Paragraph(data["overall_conclusion_title"], BOLD),
            Paragraph(data["overall_conclusion_text"], BODY),
        ]],
        colWidths=[RIGHT_COL],
    )
    conclusion.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), conclusion_bg),
        ("BOX", (0, 0), (-1, -1), 1, conclusion_border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    # KPI 1
    kpi1 = Table(
        [[
            Paragraph("Daily operating requirement checked", SMALL),
            Paragraph(data["required_operation"], BIG),
            Paragraph(
                "This is the daily operating requirement used as the acceptance threshold in the study.",
                SMALL
            ),
        ]],
        colWidths=[(RIGHT_COL - 12) / 2],
    )
    kpi1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    # KPI 2
    risk_pass = _risk_is_pass(data)
    kpi2_bg = GREEN_SOFT if risk_pass else RED_SOFT
    kpi2_border = GREEN_BORDER if risk_pass else RED_BORDER

    kpi2 = Table(
        [[
            Paragraph("Worst blackout risk", SMALL),
            Paragraph(data["worst_blackout_risk"], BIG),
            Paragraph(data["worst_blackout_pct"] or "Lowest annual risk found in the checked device set.", SMALL),
        ]],
        colWidths=[(RIGHT_COL - 12) / 2],
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
        colWidths=[RIGHT_COL / 2 - 6, RIGHT_COL / 2 - 6],
    )
    kpis.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    interpretation = Table(
        [[
            Paragraph("Interpretation", SMALL),
            Paragraph(data["interpretation"], BODY),
        ]],
        colWidths=[RIGHT_COL],
    )
    interpretation.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    action = Table(
        [[
            Paragraph("Recommended action", SMALL),
            Paragraph(data["recommendation"], BOLD),
        ]],
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

    right_stack = [
        conclusion,
        Spacer(1, 14),
        kpis,
        Spacer(1, 14),
        interpretation,
        Spacer(1, 14),
        action,
    ]

    main_grid = Table(
        [[left_card, right_stack]],
        colWidths=[LEFT_COL, RIGHT_COL],
    )
    main_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(main_grid)
    story.append(Spacer(1, 14))

    footer_strip = Table(
        [[Paragraph(data["methodology_note"], SMALL)]],
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

    story.append(PageBreak())
    return story
