from reportlab.platypus import PageBreak, Paragraph, Spacer

from ..layout import (
    HALF_WIDTH,
    card,
    kpi_card,
    kpi_row,
    page_footer,
    page_title,
    quiet_table,
    summary_strip,
    two_col,
)
from ..styles import BODY, BODY_BOLD, CARD_TITLE, SMALL, SPACE_3


def _nobr(text: str) -> str:
    return str(text).replace(" ", "&nbsp;")


def _summary_label(data):
    if data["devices_pass_count"] == data["devices_total"]:
        return "PASS"
    if data["devices_fail_count"] == 0:
        return "RISK"
    return "FAIL"


def build_summary(data):
    story = [page_title("Feasibility Result"), Spacer(1, SPACE_3)]

    conclusion = card(
        [
            Paragraph("Overall conclusion", CARD_TITLE),
            Spacer(1, 8),
            Paragraph(data["overall_result_title"], BODY_BOLD),
            Spacer(1, 6),
            Paragraph(data["overall_result_text"], BODY),
        ],
        HALF_WIDTH,
        padding=14,
    )

    device_rows = [
        [d["name"], str(d["annual_blackout_days"]), d["result_label"]]
        for d in data["devices"]
    ]
    device_table = quiet_table(
        device_rows,
        widths=[HALF_WIDTH * 0.50, HALF_WIDTH * 0.24, HALF_WIDTH * 0.26],
        header=["Device", "Blackout days", "Result"],
    )
    device_summary = card(
        [
            Paragraph("Device feasibility summary", CARD_TITLE),
            Spacer(1, 8),
            device_table,
        ],
        HALF_WIDTH,
        padding=14,
    )

    story.append(two_col(conclusion, device_summary))
    story.append(Spacer(1, 10))

    kpi_cards = [
        kpi_card(
            "Required operating profile",
            _nobr(data["required_operation"]),
            "Defined compliance target",
            width=(515 - 16) / 3.0,
        ),
        kpi_card(
            "Blackout days / year",
            _nobr(str(data["max_blackout_days"])),
            "Worst annual depletion result",
            width=(515 - 16) / 3.0,
            label=_summary_label(data),
        ),
        kpi_card(
            "Devices meeting requirement",
            _nobr(f"{data['devices_pass_count']} of {data['devices_total']}"),
            "Fleet-level compliance result",
            width=(515 - 16) / 3.0,
        ),
    ]
    story.append(kpi_row(kpi_cards))
    story.append(Spacer(1, 10))

    summary_text = f"{data['devices_pass_count']} of {data['devices_total']} devices meet requirement."
    story.append(summary_strip(summary_text, _summary_label(data)))
    story.append(Spacer(1, 18))

    story.append(page_footer(data["footer_note"], "Page 2"))
    story.append(PageBreak())
    return story
