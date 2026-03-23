import os

from .theme import (
    PAGE_H, MARGIN, TOP_RULE_Y,
    LINE, WHITE, SOFT_BG,
    NAVY, TEXT, MUTED,
    BLUE, BLUE_SOFT, BLUE_BORDER,
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
    page_w = c._pagesize[0]

    # top rule
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, TOP_RULE_Y, page_w - MARGIN, TOP_RULE_Y)

    # logos
    if os.path.exists(SALA_LOGO):
        draw_logo(c, SALA_LOGO, MARGIN, PAGE_H - 92, w=70)

    if os.path.exists(EU_LOGO):
        draw_logo(c, EU_LOGO, page_w - MARGIN - 90, PAGE_H - 90, w=90)

    # title block (left)
    draw_small_caps(c, MARGIN, PAGE_H - 130, "SALA Standardized Feasibility Study", size=10, color=BLUE)

    draw_title(
        c,
        MARGIN,
        PAGE_H - 165,
        "Solar Airfield Lighting\nSystem",
        size=30,
        max_width=320,
        leading=32,
    )

    # right identity block (merged, not floating)
    right_x = page_w - MARGIN - 240
    right_y = PAGE_H - 220

    draw_round_rect(c, right_x, right_y, 240, 110, r=14, fill_color=BLUE_SOFT, stroke_color=BLUE_BORDER)

    draw_small_caps(c, right_x + 16, right_y + 80, "Document status", size=8.5, color=MUTED)

    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(BLUE)
    c.drawString(right_x + 16, right_y + 56, data["status"])

    draw_text(
        c,
        right_x + 16,
        right_y + 30,
        data["prepared_under"],
        size=10,
        color=TEXT,
        max_width=200,
    )

    # main identity plate (clean grid)
    plate_x = MARGIN
    plate_y = PAGE_H - 360
    plate_w = page_w - 2 * MARGIN
    plate_h = 140

    draw_round_rect(c, plate_x, plate_y, plate_w, plate_h, r=16, fill_color=SOFT_BG, stroke_color=LINE)

    # grid lines
    c.setStrokeColor("#E5EAF1")
    c.setLineWidth(1)

    c.line(plate_x + plate_w / 2, plate_y + 20, plate_x + plate_w / 2, plate_y + plate_h - 20)
    c.line(plate_x + 20, plate_y + 75, plate_x + plate_w - 20, plate_y + 75)

    # left column
    draw_label_value(c, plate_x + 20, plate_y + 100, "Report ID", data["report_id"], label_w=85)
    draw_label_value(c, plate_x + 20, plate_y + 55, "Revision", data["revision"], label_w=85)
    draw_label_value(c, plate_x + 20, plate_y + 25, "Date", data["date"], label_w=85)

    # right column
    draw_label_value(c, plate_x + plate_w / 2 + 20, plate_y + 100, "Airport", data["airport_name"], label_w=75)
    draw_label_value(c, plate_x + plate_w / 2 + 20, plate_y + 55, "Location", data["country"] or "-", label_w=75)
    draw_label_value(c, plate_x + plate_w / 2 + 20, plate_y + 25, "Coordinates", data["coordinates"], label_w=75)

    # methodology block (clean, full width)
    meth_y = PAGE_H - 530

    draw_round_rect(c, MARGIN, meth_y, plate_w, 120, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, MARGIN + 20, meth_y + 90, "Methodology basis", size=9, color=MUTED)

    draw_title(
        c,
        MARGIN + 20,
        meth_y + 60,
        data["prepared_under"],
        size=18,
        max_width=plate_w - 40,
    )

    draw_text(
        c,
        MARGIN + 20,
        meth_y + 30,
        "Feasibility based on long-term solar irradiation data and off-grid performance simulation.",
        size=10,
        max_width=plate_w - 40,
    )

    # footer
    draw_footer(c, MARGIN, data["report_id"], data["revision"], 1)
