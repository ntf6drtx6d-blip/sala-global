import os
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from ..styles import (
    TITLE, BODY, SMALL, BOLD, BIG, HERO, LINE, WHITE,
    GREEN_SOFT, GREEN_BORDER, RED_SOFT, RED_BORDER,
    BLUE_SOFT, BLUE_BORDER
)

PAGE_WIDTH = 510
ASSET_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets"))


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _status_style(accent):
    if accent == "green":
        return GREEN_SOFT, GREEN_BORDER, "Feasibility confirmed"
    if accent == "red":
        return RED_SOFT, RED_BORDER, "Feasibility not confirmed"
    return BLUE_SOFT, BLUE_BORDER, "Feasibility requires review"


def _stack(items, width, style=None):
    t = Table([[x] for x in items], colWidths=[width])
    if style:
        t.setStyle(TableStyle(style))
    return t


def _logo(path, width, height):
    try:
        img = Image(path)
        img._restrictSize(width, height)
        return img
    except Exception:
        return Paragraph("", BODY)


def build_cover(data):
    story = []

    airport_name = _safe(data.get("airport_name"))
    report_date = _safe(data.get("date"))
    report_id = _safe(data.get("report_id"))
    revision = _safe(data.get("revision"))
    country = _safe(data.get("country"))
    prepared_under = _safe(data.get("prepared_under"))
    methodology_note = _safe(data.get("methodology_note"))
    prepared_by = _safe(data.get("prepared_by"))
    accent = data.get("accent", "blue")

    status_bg, status_border, status_text = _status_style(accent)

    sala_logo = _logo(os.path.join(ASSET_DIR, "sala_logo.png"), 90, 45)
    jrc_logo = _logo(os.path.join(ASSET_DIR, "jrc_logo.jpg"), 130, 45)

    logos = Table([[sala_logo, "", jrc_logo]], colWidths=[90, 290, 130])
    logos.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(logos)
    story.append(Spacer(1, 18))
    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Solar AGL", HERO))
    story.append(Spacer(1, 22))

    intro = _stack(
        [
            Paragraph("Project location", SMALL),
            Paragraph(f"<b>{airport_name}</b>", BIG),
            Paragraph(country, BODY),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ],
    )
    story.append(intro)
    story.append(Spacer(1, 14))

    left = _stack(
        [
            Paragraph("Unique identification number", SMALL),
            Paragraph(report_id, BOLD),
            Spacer(1, 8),
            Paragraph("Revision", SMALL),
            Paragraph(revision, BOLD),
        ],
        248,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ],
    )

    right = _stack(
        [
            Paragraph("Date of report", SMALL),
            Paragraph(report_date, BOLD),
            Spacer(1, 8),
            Paragraph("Ordered by", SMALL),
            Paragraph(prepared_by, BOLD),
        ],
        248,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ],
    )

    meta = Table([[left, right]], colWidths=[248, 248])
    meta.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(meta)
    story.append(Spacer(1, 14))

    result = _stack(
        [
            Paragraph("Study result", SMALL),
            Paragraph(status_text, BIG),
            Paragraph(
                "This report summarizes whether the selected solar airfield lighting configuration can support the required operating profile year-round.",
                BODY,
            ),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("BOX", (0, 0), (-1, -1), 1, status_border),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ],
    )
    story.append(result)
    story.append(Spacer(1, 14))

    methodology = _stack(
        [
            Paragraph("Methodology basis", SMALL),
            Paragraph("Prepared using PVGIS developed by the Joint Research Centre (JRC), European Commission.", BOLD),
            Spacer(1, 4),
            Paragraph(methodology_note, BODY),
            Spacer(1, 6),
            Paragraph(f"Prepared under: {prepared_under}", BODY),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ],
    )
    story.append(methodology)

    story.append(PageBreak())
    return story
