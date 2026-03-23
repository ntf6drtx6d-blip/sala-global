import os

from .theme import (
    PAGE_H,
    MARGIN,
    TOP_RULE_Y,
    LINE,
    WHITE,
    SOFT_BG,
    NAVY,
    TEXT,
    MUTED,
    BLUE,
    BLUE_SOFT,
    BLUE_BORDER,
    SALA_LOGO,
    EU_LOGO,
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
    # Top rule
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, TOP_RULE_Y, page_w - MARGIN, TOP_RULE_Y)

    # Logos
    if os.path.exists(SALA_LOGO):
        draw_logo(c, SALA_LOGO, MARGIN, PAGE_H - 92, w=68)

    if os.path.exists(EU_LOGO):
        draw_logo(c, EU_LOGO, page_w - MARGIN - 86, PAGE_H - 88, w=86)

    # Eyebrow
    draw_small_caps(
        c,
        MARGIN,
        PAGE_H - 126,
        "SALA Standardized Feasibility Study",
        size=10,
        color=BLUE,
    )

    # Main title block
    draw_title(
        c,
        MARGIN,
        PAGE_H - 158,
        "Solar Airfield Lighting System",
        size=26,
        color=NAVY,
        max_width=330,
        leading=28,
    )

    # Subtitle / positioning statement
    draw_text(
        c,
        MARGIN,
        PAGE_H - 195,
        "Formal engineering-style feasibility assessment for solar airfield lighting deployment.",
        size=10.5,
        color=TEXT,
        max_width=345,
        leading=13,
    )

    # Right info block
    info_x = page_w - MARGIN - 245
    info_y = PAGE_H - 228
    info_w = 245
    info_h = 126

    draw_round_rect(
        c,
        info_x,
        info_y,
        info_w,
        info_h,
        r=16,
        fill_color=BLUE_SOFT,
        stroke_color=BLUE_BORDER,
    )

    draw_small_caps(c, info_x + 16, info_y + 96, "Document status", size=8.5, color=MUTED)

    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(BLUE)
    c.drawString(info_x + 16, info_y + 72, data["status"])

    draw_small_caps(c, info_x + 16, info_y + 48, "Methodology", size=8.5, color=MUTED)
    draw_text(
        c,
        info_x + 16,
        info_y + 28,
        "SALA-SAGL-100",
        size=10,
        color=TEXT,
        max_width=info_w - 32,
    )

    # Main document plate
    plate_x = MARGIN
    plate_y = PAGE_H - 370
    plate_w = page_w - 2 * MARGIN
    plate_h = 150

    draw_round_rect(
        c,
        plate_x,
        plate_y,
        plate_w,
        plate_h,
        r=18,
        fill_color=SOFT_BG,
        stroke_color=LINE,
    )

    # Grid lines
    c.setStrokeColor("#E7ECF2")
    c.setLineWidth(1)
    c.line(plate_x + plate_w / 2, plate_y + 20, plate_x + plate_w / 2, plate_y + plate_h - 20)
    c.line(plate_x + 18, plate_y + 96, plate_x + plate_w - 18, plate_y + 96)
    c.line(plate_x + 18, plate_y + 52, plate_x + plate_w - 18, plate_y + 52)

    # Left column
    draw_label_value(c, plate_x + 20, plate_y + 116, "Report ID", data["report_id"], label_w=86, value_size=10.5)
    draw_label_value(c, plate_x + 20, plate_y + 72, "Revision", data["revision"], label_w=86, value_size=10.5)
    draw_label_value(c, plate_x + 20, plate_y + 28, "Date", data["date"], label_w=86, value_size=10.5)

    # Right column
    draw_label_value(c, plate_x + plate_w / 2 + 20, plate_y + 116, "Airport", data["airport_name"], label_w=78, value_size=10.5)
    draw_label_value(c, plate_x + plate_w / 2 + 20, plate_y + 72, "Location", data["country"] or "N/A", label_w=78, value_size=10.5)
    draw_label_value(c, plate_x + plate_w / 2 + 20, plate_y + 28, "Coordinates", data["coordinates"], label_w=78, value_size=10.5)

    # Methodology basis block
    meth_x = MARGIN
    meth_y = PAGE_H - 555
    meth_w = page_w - 2 * MARGIN
    meth_h = 112

    draw_round_rect(
        c,
        meth_x,
        meth_y,
        meth_w,
        meth_h,
        r=16,
        fill_color=WHITE,
        stroke_color=LINE,
    )

    draw_small_caps(c, meth_x + 18, meth_y + 84, "Methodology basis", size=8.8, color=MUTED)
    draw_text(
        c,
        meth_x + 18,
        meth_y + 58,
        "Prepared under SALA-SAGL-100 methodology",
        size=14.5,
        color=NAVY,
        font="Helvetica-Bold",
        max_width=meth_w - 36,
        leading=17,
    )
    draw_text(
        c,
        meth_x + 18,
        meth_y + 32,
        "This report presents the feasibility outcome for the selected solar airfield lighting configuration based on long-term solar irradiation data and off-grid performance simulation.",
        size=10,
        color=TEXT,
        max_width=meth_w - 36,
        leading=12.5,
    )

    # Bottom strip
    strip_x = MARGIN
    strip_y = 118
    strip_w = page_w - 2 * MARGIN
    strip_h = 70

    draw_round_rect(
        c,
        strip_x,
        strip_y,
        strip_w,
        strip_h,
        r=14,
        fill_color=WHITE,
        stroke_color=LINE,
    )

    draw_small_caps(c, strip_x + 18, strip_y + 45, "Document basis", size=8.2, color=MUTED)
    draw_text(
        c,
        strip_x + 18,
        strip_y + 23,
        "Prepared as a formal engineering-style study under SALA-approved report structure, with document identity, revision control and project-specific registration.",
        size=9.6,
        color=TEXT,
        max_width=strip_w - 36,
        leading=11.5,
    )

    draw_footer(c, MARGIN, data["report_id"], data["revision"], 1)
