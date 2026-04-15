from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from .styles import (
    BODY,
    BODY_BOLD,
    BORDER,
    CARD_TITLE,
    FOOTER,
    KPI_VALUE,
    LIGHT_BG,
    MUTED,
    PAGE_WIDTH,
    PRIMARY_SOFT,
    RED,
    RED_SOFT,
    GREEN,
    GREEN_SOFT,
    AMBER,
    AMBER_SOFT,
    SECTION,
    SMALL,
    SMALL_BOLD,
    TEXT,
    TITLE,
    WHITE,
)

PAGE_GAP = 10
CARD_PADDING = 12
CARD_RADIUS = 0
TWO_COL_GAP = 10
HALF_WIDTH = (PAGE_WIDTH - TWO_COL_GAP) / 2.0
THIRD_GAP = 8
THIRD_WIDTH = (PAGE_WIDTH - 2 * THIRD_GAP) / 3.0


def status_palette(label: str):
    normalized = str(label or "").upper()
    if "PASS" in normalized or "SUSTAINABLE" in normalized:
        return GREEN_SOFT, GREEN
    if "RISK" in normalized or "THRESHOLD" in normalized or "MIXED" in normalized:
        return AMBER_SOFT, AMBER
    return RED_SOFT, RED


def page_title(text: str):
    return Paragraph(text, TITLE)


def section_heading(text: str):
    return Paragraph(text, SECTION)


def _flatten(items):
    rows = []
    for item in items:
        if item is None:
            continue
        rows.append([item])
    return rows


def card(items, width, bg=WHITE, border=BORDER, padding=CARD_PADDING):
    t = Table(_flatten(items), colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def badge(label: str, width=84):
    fill, line = status_palette(label)
    t = Table([[Paragraph(f"<para align='center'><b>{label}</b></para>", SMALL_BOLD)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("TEXTCOLOR", (0, 0), (-1, -1), line),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def header_row(left, right, widths):
    t = Table([[left, right]], colWidths=list(widths))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def two_col(left, right, left_width=HALF_WIDTH, right_width=HALF_WIDTH):
    t = Table([[left, right]], colWidths=[left_width, right_width])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def kpi_card(title: str, value: str, subtitle: str, width: float, label: str | None = None):
    fill, line = status_palette(label or "")
    use_fill = fill if label else WHITE
    use_line = line if label else BORDER
    items = [
        Paragraph(title, SMALL_BOLD),
        Spacer(1, 4),
        Paragraph(value, KPI_VALUE),
    ]
    if subtitle:
        items.extend([Spacer(1, 4), Paragraph(subtitle, SMALL)])
    return card(items, width, bg=use_fill, border=use_line, padding=12)


def kpi_row(cards):
    widths = [THIRD_WIDTH] * len(cards)
    t = Table([cards], colWidths=widths)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def label_value_block(rows, width, shaded_label=True):
    data = []
    for label, value in rows:
        data.append([Paragraph(str(label), SMALL_BOLD), Paragraph(str(value), BODY)])
    t = Table(data, colWidths=[width * 0.34, width * 0.66])
    style = [
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if shaded_label:
        style.append(("BACKGROUND", (0, 0), (0, -1), LIGHT_BG))
    t.setStyle(TableStyle(style))
    return t


def quiet_table(rows, widths, header=None):
    data = []
    if header:
        data.append([Paragraph(cell, SMALL_BOLD) for cell in header])
    for row in rows:
        data.append([Paragraph(str(cell), BODY) for cell in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), PRIMARY_SOFT))
    t.setStyle(TableStyle(style))
    return t


def summary_strip(text: str, label: str | None = None):
    fill, line = status_palette(label or "")
    return card([Paragraph(text, BODY_BOLD)], PAGE_WIDTH, bg=fill if label else LIGHT_BG, border=line if label else BORDER, padding=10)


def page_footer(note: str, page_label: str):
    t = Table([[Paragraph(note, FOOTER), Paragraph(page_label, FOOTER)]], colWidths=[PAGE_WIDTH - 85, 85])
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.7, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def keep_block(*items):
    return KeepTogether(list(items))
