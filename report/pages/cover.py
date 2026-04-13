from pathlib import Path
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, PageBreak

from ..styles import (
    TITLE, BODY, SMALL, SMALL_BOLD, BODY_BOLD, FOOTER,
    PRIMARY_SOFT, GREEN, GREEN_SOFT, AMBER, AMBER_SOFT, RED, RED_SOFT,
    BORDER, WHITE, PAGE_WIDTH, SPACE_2, SPACE_3
)
from ..assets.maps import generate_static_map

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def _status_palette(label: str):
    if label == "PASS":
        return GREEN_SOFT, GREEN
    if label == "NEAR THRESHOLD":
        return AMBER_SOFT, AMBER
    return RED_SOFT, RED


def _safe_img(path: Path, width: int, height: int):
    if path.exists():
        img = Image(str(path))
        img._restrictSize(width, height)
        return img
    return Paragraph("", BODY)


def build_cover(data):
    story = []

    sala_logo = _safe_img(ASSET_DIR / "sala_logo.png", 75, 34)
    jrc_logo = _safe_img(ASSET_DIR / "jrc_logo.jpg", 105, 34)

    header = Table([[sala_logo, Paragraph("SALA Standardized Feasibility Study for Solar AGL", SMALL_BOLD), jrc_logo]],
                   colWidths=[82, 328, 105])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, BORDER),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Solar Airfield Lighting<br/>Feasibility Study", TITLE))
    story.append(Spacer(1, SPACE_2))
    story.append(Paragraph(data["methodology_note"], BODY))
    story.append(Spacer(1, 14))

    map_path = generate_static_map(data["lat"], data["lon"], width=700, height=380, zoom=9)
    map_img = Image(map_path)
    map_img._restrictSize(205, 118)

    meta_rows = [
        [Paragraph("<b>Project / Airport</b>", SMALL), Paragraph(data["airport_name"], BODY)],
        [Paragraph("<b>Coordinates</b>", SMALL), Paragraph(data["coordinates"], BODY)],
        [Paragraph("<b>Required operating profile</b>", SMALL), Paragraph(data["required_operation"], BODY)],
        [Paragraph("<b>Prepared for</b>", SMALL), Paragraph(data["prepared_for"], BODY)],
        [Paragraph("<b>Date</b>", SMALL), Paragraph(data["date"], BODY)],
        [Paragraph("<b>Document ID</b>", SMALL), Paragraph(data["report_id"], BODY)],
    ]
    meta = Table(meta_rows, colWidths=[130, 180])
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), PRIMARY_SOFT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    top = Table([[map_img, meta]], colWidths=[205, 310])
    top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(top)
    story.append(Spacer(1, 14))

    fill, line = _status_palette(data["cover_verdict"])
    verdict = Table([[(Paragraph(f"<b>{data['cover_verdict']}</b>", BODY_BOLD)), Paragraph(data["cover_statement"], BODY)]], colWidths=[110, 405])
    verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 1.0, line),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(verdict)
    story.append(Spacer(1, 18))

    footer = Table([[Paragraph(data["footer_note"], FOOTER), Paragraph("Page 1", FOOTER)]], colWidths=[430, 85])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.7, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(footer)
    story.append(PageBreak())
    return story
