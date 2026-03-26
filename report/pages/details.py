from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from ..styles import SECTION, BODY, SMALL, BOLD, LINE, WHITE, BLUE_SOFT, BLUE_BORDER

PAGE_WIDTH = 510


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _stack(items, width, style=None):
    t = Table([[x] for x in items], colWidths=[width])
    if style:
        t.setStyle(TableStyle(style))
    return t


def build_details(data):
    story = []

    story.append(Paragraph("Detailed findings", SECTION))
    story.append(Spacer(1, 12))

    left = _stack(
        [
            Paragraph("Primary decision point", SMALL),
            Paragraph("Can the selected system support the required operating profile year-round?", BOLD),
            Spacer(1, 6),
            Paragraph(
                f"Overall conclusion: {_safe(data.get('overall_conclusion_title'))}",
                BODY,
            ),
            Paragraph(
                f"Required operation: {_safe(data.get('required_operation'))}",
                BODY,
            ),
            Paragraph(
                f"Worst blackout risk: {_safe(data.get('worst_blackout_risk'))} ({_safe(data.get('worst_blackout_pct'))})",
                BODY,
            ),
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
            Paragraph("Configuration assessed", SMALL),
            Paragraph(_safe(data.get("device_name")), BOLD),
            Paragraph(f"Engine: {_safe(data.get('engine_name'))}", BODY),
            Paragraph(f"Worst month: {_safe(data.get('worst_month_name'))}", BODY),
            Paragraph(f"Worst month performance: {_safe(data.get('worst_month_hours'))}", BODY),
            Paragraph(f"Battery-only reserve: {_safe(data.get('battery_reserve'))}", BODY),
        ],
        248,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
            ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ],
    )

    top = Table([[left, right]], colWidths=[248, 248])
    top.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(top)
    story.append(Spacer(1, 14))

    key_points = _stack(
        [
            Paragraph("Key interpretation", SMALL),
            Paragraph(_safe(data.get("executive_summary")), BOLD),
            Spacer(1, 6),
            Paragraph(
                "This page is intended to help the reader move from raw performance outputs to an operational decision. "
                "If the required line is never breached and blackout exposure remains at 0 days/year, the configuration may be considered feasible for the defined profile.",
                BODY,
            ),
            Spacer(1, 4),
            Paragraph(
                "If annual blackout exposure is non-zero or the achieved operating profile falls below requirement in one or more months, the configuration should be reviewed or redesigned.",
                BODY,
            ),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ],
    )
    story.append(key_points)
    story.append(PageBreak())
    return story
