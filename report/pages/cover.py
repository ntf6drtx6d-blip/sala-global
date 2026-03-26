import os
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from ..styles import TITLE, BODY, SMALL, BOLD, LINE, WHITE, NAVY, BLUE_SOFT, BLUE_BORDER

PAGE_WIDTH = 510
ASSET_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets"))


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _logo(path, width, height):
    try:
        img = Image(path)
        img._restrictSize(width, height)
        return img
    except Exception:
        return Paragraph("", BODY)


def build_cover(data):
    story = []

    sala_logo = _logo(os.path.join(ASSET_DIR, "sala_logo.png"), 80, 40)
    ec_logo = _logo(os.path.join(ASSET_DIR, "jrc_logo.jpg"), 110, 38)

    top = Table([[sala_logo, Paragraph("<b>SALA Standardized Feasibility Study for Solar AGL</b>", SMALL), ec_logo]],
                colWidths=[70, 330, 110])
    top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, LINE),
    ]))
    story.append(top)
    story.append(Spacer(1, 60))

    center_logo = _logo(os.path.join(ASSET_DIR, "sala_logo.png"), 90, 90)
    story.append(Table([[center_logo]], colWidths=[PAGE_WIDTH], style=TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER")])))
    story.append(Spacer(1, 24))
    story.append(Paragraph("SALA Standardized Feasibility Study for<br/>Solar AGL", TITLE))
    story.append(Spacer(1, 10))
    story.append(Paragraph(_safe(data.get("airport_name")), BODY))
    story.append(Spacer(1, 28))

    meta_rows = [
        [Paragraph("<b>Project / Location</b>", SMALL), Paragraph(_safe(data.get("airport_name")), BODY)],
        [Paragraph("<b>Coordinates</b>", SMALL), Paragraph(_safe(data.get("coordinates")), BODY)],
        [Paragraph("<b>Generated</b>", SMALL), Paragraph(_safe(data.get("date")), BODY)],
        [Paragraph("<b>Required operating profile</b>", SMALL), Paragraph(_safe(data.get("required_operation")), BODY)],
        [Paragraph("<b>Assessment basis</b>", SMALL), Paragraph("PVGIS off-grid autonomy and annual worst-month evaluation", BODY)],
        [Paragraph("<b>Prepared for</b>", SMALL), Paragraph(_safe(data.get("prepared_by")), BODY)],
    ]
    meta = Table(meta_rows, colWidths=[140, 330])
    meta.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.7, LINE),
        ("BACKGROUND", (0,0), (0,-1), BLUE_SOFT),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(meta)
    story.append(Spacer(1, 36))

    conclusion = Table([[
        Paragraph(
            f"<b>{_safe(data.get('cover_verdict', 'NOT TECHNICALLY FEASIBLE'))}</b><br/>"
            f"{_safe(data.get('cover_statement'))}",
            BODY
        )
    ]], colWidths=[PAGE_WIDTH])
    conclusion.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("TEXTCOLOR", (0,0), (-1,-1), WHITE),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(conclusion)
    story.append(Spacer(1, 80))

    footer = Table([[Paragraph("Prepared using PVGIS-based off-grid assessment methodology", SMALL),
                     Paragraph("Page 1", SMALL)]], colWidths=[420, 90])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,-1), 0.7, LINE),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(footer)
    story.append(PageBreak())
    return story
