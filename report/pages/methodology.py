from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from ..styles import TITLE, CARD_TITLE, BODY, SMALL, FOOTER, PRIMARY_SOFT, WHITE, BORDER, PAGE_WIDTH


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


def build_methodology(data):
    story = [Paragraph("Methodology", TITLE), Spacer(1, 14)]

    story.append(_card([
        Paragraph("Methodological basis", CARD_TITLE),
        Spacer(1, 4),
        Paragraph("This report is prepared using PVGIS developed by the Joint Research Centre (JRC), European Commission.", BODY),
        Spacer(1, 4),
        Paragraph(f"Dataset used by the simulation engine: {data['pvgis_dataset']}", BODY),
    ], PAGE_WIDTH, bg=PRIMARY_SOFT))
    story.append(Spacer(1, 10))

    rows = [
        [Paragraph("Daily operation in hours", SMALL), Paragraph("Required daily lighting use expected by the airport.", BODY)],
        [Paragraph("Battery autonomy", SMALL), Paragraph("Backup duration using stored energy only. It is not, by itself, proof of annual feasibility.", BODY)],
        [Paragraph("Days with 0% battery depletion", SMALL), Paragraph("Number of days when battery is expected to reach 0% and required operation may not be sustained.", BODY)],
        [Paragraph("Acceptance rule", SMALL), Paragraph("A configuration is acceptable only if the required operating profile is maintained without battery depletion causing operational blackout.", BODY)],
    ]
    tbl = Table(rows, colWidths=[155, 360])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), PRIMARY_SOFT),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))

    story.append(_card([
        Paragraph("Interpretation", CARD_TITLE),
        Spacer(1, 4),
        Paragraph("Solar AGL is assessed as an energy system defined by generation, storage, and consumption. The report evaluates whether the selected configuration can sustain the required operating profile under annual location-specific solar conditions.", BODY)
    ], PAGE_WIDTH))

    story.append(Spacer(1, 18))
    footer = Table([[Paragraph(data["footer_note"], FOOTER), Paragraph("Page 5", FOOTER)]], colWidths=[430, 85])
    footer.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.7, BORDER), ("TOPPADDING", (0, 0), (-1, -1), 6), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(footer)
    return story
