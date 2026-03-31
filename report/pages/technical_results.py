from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from ..styles import TITLE, CARD_TITLE, SMALL, FOOTER, WHITE, BORDER, PAGE_WIDTH, SPACE_3
from ..assets.charts import generate_blackout_chart, generate_profile_chart


def _card(items, width, bg=WHITE, border=BORDER, padding=10):
    t = Table([[i] for i in items], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return t


def build_technical(data):
    story = []
    story.append(Paragraph("Technical Results", TITLE))
    story.append(Spacer(1, SPACE_3))

    if data["show_blackout_chart"]:
        blackout_path = generate_blackout_chart(data["devices"])
        img = Image(blackout_path)
        img._restrictSize(495, 230)
        story.append(_card([Paragraph("Days with 0% battery depletion", CARD_TITLE), Spacer(1, 6), img], PAGE_WIDTH))
        story.append(Spacer(1, 12))
    else:
        story.append(_card([Paragraph("Days with 0% battery depletion", CARD_TITLE),
                            Spacer(1, 4),
                            Paragraph("No battery depletion is expected for any evaluated device.", SMALL)], PAGE_WIDTH))
        story.append(Spacer(1, 12))

    profile_path = generate_profile_chart(data["devices"], data["required_hours"])
    pimg = Image(profile_path)
    pimg._restrictSize(495, 260)
    story.append(_card([Paragraph("Annual operating profile", CARD_TITLE), Spacer(1, 6), pimg], PAGE_WIDTH))

    story.append(Spacer(1, 185))
    footer = Table([[Paragraph(data["footer_note"], FOOTER), Paragraph("Page 3", FOOTER)]], colWidths=[430, 85])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.7, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(footer)
    story.append(PageBreak())
    return story
