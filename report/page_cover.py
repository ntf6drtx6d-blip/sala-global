import os

from .theme import (
    PAGE_H, MARGIN, TOP_RULE_Y, LINE, SOFT_BG, WHITE,
    BLUE, BLUE_SOFT, BLUE_BORDER, NAVY, TEXT, MUTED,
    SALA_LOGO, EU_LOGO,
)
from .helpers import (
    draw_logo,
    draw_small_caps,
    draw_title,
    draw_round_rect,
    draw_label_value,
    draw_text,
)
from .blocks import draw_footer


def draw_cover_page(c, data):
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, TOP_RULE_Y, c._pagesize[0] - MARGIN, TOP_RULE_Y)

    if os.path.exists(SALA_LOGO):
        draw_logo(c, SALA_LOGO, MARGIN, PAGE_H - 92, w=72)

    if os.path.exists(EU_LOGO):
        draw_logo(c, EU_LOGO, c._pagesize[0] - MARGIN - 98, PAGE_H - 90, w=98)

    draw_small_caps(c, MARGIN, PAGE_H - 128, "SALA Standardized Feasibility Study", size=10.5, color=BLUE)

    draw_title(
        c,
        MARGIN,
        PAGE_H - 162,
        "Solar Airfield Lighting\nSystem",
        size=30,
        color=NAVY,
        max_width=320,
        leading=32,
    )

    # right identity / status block
    right_x = c._pagesize[0] - MARGIN - 215
    right_y = PAGE_H - 190
    draw_round_rect(c, right_x, right_y, 215, 88, r=14, fill_color=BLUE_SOFT, stroke_color=BLUE_BORDER)
    draw_small_caps(c, right_x + 16, right_y + 62, "Document status", size=8.6, color=MUTED)

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(BLUE)
    c.drawString(right_x + 16, right_y + 38, data["status"])

    c.setFont("Helvetica", 10)
    c.setFillColor(TEXT)
    c.drawString(right_x + 16, right_y + 18, data["prepared_under"])

    # report plate
    plate_x = MARGIN
    plate_y = PAGE_H - 330
    plate_w = c._pagesize[0] - 2 * MARGIN
    plate_h = 134

    draw_round_rect(c, plate_x, plate_y, plate_w, plate_h, r=16, fill_color=SOFT_BG, stroke_color=LINE)

    c.setStrokeColor("#E5EAF1")
    c.setLineWidth(1)
    c.line(plate_x + plate_w / 2, plate_y + 18, plate_x + plate_w / 2, plate_y + plate_h - 18)
    c.line(plate_x + 20, plate_y + 72, plate_x + plate_w - 20, plate_y + 72)

    draw_label_value(c, plate_x + 22, plate_y + 96, "Report ID", data["report_id"], label_w=88, value_size=10.5)
    draw_label_value(c, plate_x + 22, plate_y + 52, "Revision", data["revision"], label_w=88, value_size=10.5)

    draw_label_value(c, plate_x + plate_w / 2 + 22, plate_y + 96, "Airport", data["airport_name"], label_w=72, value_size=10.5)
    draw_label_value(c, plate_x + plate_w / 2 + 22, plate_y + 52, "Location", data["country"] or "-", label_w=72, value_size=10.5)

    draw_label_value(c, plate_x + 22, plate_y + 22, "Date", data["date"], label_w=88, value_size=10.5)
    draw_label_value(c, plate_x + plate_w / 2 + 22, plate_y + 22, "Coordinates", data["coordinates"], label_w=72, value_size=10.5)

    # methodology box
    meth_y = PAGE_H - 500
    meth_h = 122

    draw_round_rect(c, MARGIN, meth_y, plate_w, meth_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, MARGIN + 22, meth_y + 94, "Methodology basis", size=9.2, color=MUTED)
    draw_title(c, MARGIN + 22, meth_y + 64, data["prepared_under"], size=18, color=NAVY, max_width=plate_w - 44)

    draw_text(
        c,
        MARGIN + 22,
        meth_y + 34,
        "This report presents the feasibility outcome for the selected solar airfield lighting configuration based on long-term solar irradiation data and off-grid performance simulation.",
        size=10.5,
        color=TEXT,
        max_width=plate_w - 44,
        leading=13,
    )

    # trust strip
    strip_y = 118
    strip_h = 78

    draw_round_rect(c, MARGIN, strip_y, plate_w, strip_h, r=14, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, MARGIN + 20, strip_y + 50, "Document basis", size=8.5, color=MUTED)
    draw_text(
        c,
        MARGIN + 20,
        strip_y + 26,
        "Prepared as a formal engineering-style study under SALA-approved report structure, with document identity, revision control and project-specific registration.",
        size=10,
        color=TEXT,
        max_width=plate_w - 40,
        leading=12.5,
    )

    draw_footer(c, MARGIN, data["report_id"], data["revision"], 1)
