from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib import colors

from ..styles import (
    TITLE, BODY, SMALL, BOLD, BIG,
    LINE, WHITE,
    BLUE_SOFT, BLUE_BORDER,
    GREEN_SOFT, GREEN_BORDER,
    RED_SOFT, RED_BORDER,
)


PAGE_WIDTH = 510


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _status_style(accent):
    if accent == "green":
        return GREEN_SOFT, GREEN_BORDER, "System meets operational requirement"
    if accent == "red":
        return RED_SOFT, RED_BORDER, "System does not meet operational requirement"
    return BLUE_SOFT, BLUE_BORDER, "System partially meets operational requirement"


def _stacked(items, width, style=None):
    table = Table([[item] for item in items], colWidths=[width])
    if style:
        table.setStyle(TableStyle(style))
    return table


def build_cover(data):
    story = []

    airport_name = _safe(data.get("airport_name"))
    report_date = _safe(data.get("date"))
    report_id = _safe(data.get("report_id"))
    revision = _safe(data.get("revision"))
    country = _safe(data.get("country"))
    prepared_under = _safe(data.get("prepared_under"))
    methodology_note = _safe(data.get("methodology_note"))
    accent = data.get("accent", "blue")

    status_bg, status_border, status_text = _status_style(accent)

    story.append(Spacer(1, 36))

    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Solar AGL", TITLE))
    story.append(Spacer(1, 30))

    intro = _stacked(
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
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ],
    )
    story.append(intro)
    story.append(Spacer(1, 16))

    meta_left = _stacked(
        [
            Paragraph("Document number", SMALL),
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

    meta_right = _stacked(
        [
            Paragraph("Report date", SMALL),
            Paragraph(report_date, BOLD),
            Spacer(1, 8),
            Paragraph("Prepared under", SMALL),
            Paragraph(prepared_under, BOLD),
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

    meta = Table([[meta_left, meta_right]], colWidths=[248, 248])
    meta.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 16))

    status_block = _stacked(
        [
            Paragraph("Study result", SMALL),
            Paragraph(status_text, BIG),
            Paragraph(
                "This report presents the outcome of the standardized solar feasibility study "
                "for the selected airfield lighting operating profile.",
                BODY,
            ),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("BOX", (0, 0), (-1, -1), 1, status_border),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ],
    )
    story.append(status_block)
    story.append(Spacer(1, 16))

    methodology_block = _stacked(
        [
            Paragraph("Methodology basis", SMALL),
            Paragraph("PVGIS-based off-grid simulation", BOLD),
            Paragraph(
                "European Commission, Joint Research Centre",
                BODY,
            ),
            Spacer(1, 6),
            Paragraph(methodology_note, BODY),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ],
    )
    story.append(methodology_block)

    story.append(PageBreak())
    return story
