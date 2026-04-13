from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from ..styles import TITLE, BODY, BODY_BOLD, SMALL, FOOTER, GREEN_SOFT, AMBER_SOFT, RED_SOFT, GREEN, AMBER, RED, WHITE, BORDER


def _status_palette(label: str):
    if label == "PASS":
        return GREEN_SOFT, GREEN
    if label == "NEAR THRESHOLD":
        return AMBER_SOFT, AMBER
    return RED_SOFT, RED


def _device_card(d):
    fill, line = _status_palette(d["result_class"])
    title = Table([[Paragraph(d["name"], BODY_BOLD), Paragraph(d["result_label"], BODY_BOLD)]], colWidths=[320, 145])
    title.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), fill),
        ("TEXTCOLOR", (1, 0), (1, 0), line),
        ("BOX", (1, 0), (1, 0), 0.8, line),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))

    metrics = Table([
        [Paragraph("Annual blackout days", SMALL), Paragraph(str(d["annual_blackout_days"]), BODY_BOLD)],
        [Paragraph("Interpretation", SMALL), Paragraph(d["interpretation_text"], BODY)],
    ], colWidths=[140, 325])
    metrics.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), WHITE),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))

    card = Table([[title], [Spacer(1, 6)], [metrics]], colWidths=[465])
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    return card


def build_device_details(data):
    story = [Paragraph("Device Detail Page", TITLE), Spacer(1, 14)]
    for d in data["devices"]:
        story.append(_device_card(d))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 18))
    footer = Table([[Paragraph(data["footer_note"], FOOTER), Paragraph("Page 4", FOOTER)]], colWidths=[430, 85])
    footer.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.7, BORDER), ("TOPPADDING", (0, 0), (-1, -1), 6), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(footer)
    story.append(PageBreak())
    return story
