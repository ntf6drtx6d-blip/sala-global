from reportlab.platypus import PageBreak, Paragraph, Spacer

from ..layout import (
    HALF_WIDTH,
    card,
    label_value_block,
    page_footer,
    page_title,
    badge,
    header_row,
    keep_block,
    two_col,
)
from ..styles import BODY_BOLD, CARD_TITLE, SPACE_3


def _device_block(d):
    header = header_row(
        Paragraph(d["name"], BODY_BOLD),
        badge(d["result_label"]),
        widths=[421, 84],
    )

    decision_rows = [
        ("Outcome", d["result_label"]),
        ("Annual blackout days", str(d["annual_blackout_days"])),
        ("Interpretation", d["interpretation_text"]),
    ]
    decision = card(
        [
            Paragraph("Decision summary", CARD_TITLE),
            Spacer(1, 8),
            label_value_block(decision_rows, HALF_WIDTH),
        ],
        HALF_WIDTH,
        padding=14,
    )

    battery_rows = [
        ("Technology", d["battery_type"]),
        ("Capacity", f"{d['total_battery_wh']:.0f} Wh total / {d['usable_battery_wh']:.0f} Wh usable"),
        ("Cut-off", f"{d['cutoff_pct']:.0f}%"),
    ]
    compliance_rows = [
        ("FAA reference", d["faa_reference"]),
        ("FAA 3 sun-hours check", "Compliant" if d["faa_3sunhours_compliant"] else "Not compliant"),
        ("FAA 8-hour battery check", "Compliant" if d["faa_8h_compliant"] else "Not compliant"),
    ]
    technical = card(
        [
            Paragraph("Technical basis", CARD_TITLE),
            Spacer(1, 8),
            two_col(
                card([Paragraph("Battery", CARD_TITLE), Spacer(1, 6), label_value_block(battery_rows, HALF_WIDTH - 18)], HALF_WIDTH - 5, padding=10),
                card([Paragraph("Compliance / reference", CARD_TITLE), Spacer(1, 6), label_value_block(compliance_rows, HALF_WIDTH - 18)], HALF_WIDTH - 5, padding=10),
                left_width=HALF_WIDTH - 5,
                right_width=HALF_WIDTH - 5,
            ),
        ],
        515,
        padding=14,
    )

    return keep_block(
        card(
            [
                header,
                Spacer(1, 10),
                decision,
                Spacer(1, 10),
                technical,
            ],
            515,
            padding=14,
        ),
        Spacer(1, 12),
    )


def build_device_details(data):
    story = [page_title("Device Detail Page"), Spacer(1, SPACE_3)]
    for d in data["devices"]:
        story.append(_device_block(d))

    story.append(Spacer(1, 12))
    story.append(page_footer(data["footer_note"], "Page 4"))
    story.append(PageBreak())
    return story
