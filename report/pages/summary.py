from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak

from ..styles import TITLE, BODY, SMALL, BOLD, BIG, BLUE_SOFT, BLUE_BORDER, RED_SOFT, RED_BORDER


def build_summary(data):
    story = []

    story.append(Paragraph("Management Summary", SMALL))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 16))

    conclusion = Table([
        [Paragraph(data["overall_conclusion_title"], BOLD)],
        [Paragraph(data["overall_conclusion_text"], BODY)],
    ], colWidths=[480])

    conclusion.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RED_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, RED_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    story.append(conclusion)
    story.append(Spacer(1, 20))

    kpi1 = Table([
        [Paragraph("Required operation", SMALL)],
        [Paragraph(data["required_operation"], BIG)],
    ], colWidths=[230])

    kpi1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    kpi2 = Table([
        [Paragraph("Worst blackout risk", SMALL)],
        [Paragraph(data["worst_blackout_risk"], BIG)],
        [Paragraph(data["worst_blackout_pct"], SMALL)],
    ], colWidths=[230])

    kpi2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RED_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, RED_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    kpis = Table([[kpi1, kpi2]], colWidths=[240, 240])
    kpis.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(kpis)
    story.append(Spacer(1, 20))

    story.append(Paragraph(data["interpretation"], BODY))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommendation:", BOLD))
    story.append(Paragraph(data["recommendation"], BODY))

    story.append(PageBreak())
    return story
