from .theme import (
    PAGE_H,
    MARGIN,
    TOP_RULE_Y,
    LINE,
    WHITE,
    MUTED,
    NAVY,
    BLUE,
    TEXT,
    RED_BG,
    RED_BORDER,
    RED,
    GREEN_BG,
    GREEN_BORDER,
    GREEN,
    GOLD_BG,
    GOLD_BORDER,
    GOLD,
    SOFT_BG,
)
from .helpers import draw_round_rect, draw_small_caps, draw_title, draw_text
from .blocks import draw_footer, kpi_card, draw_fake_map


def draw_summary_page(c, data):
    page_w = c._pagesize[0]
    # Top rule
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, TOP_RULE_Y, page_w - MARGIN, TOP_RULE_Y)

    # Header
    draw_small_caps(c, MARGIN, PAGE_H - 70, "Management summary", size=10, color=BLUE)
    draw_title(c, MARGIN, PAGE_H - 104, "Feasibility result", size=27, color=NAVY)

    gap = 18

    # Left column - context
    left_x = MARGIN
    left_y = 208
    left_w = 228
    left_h = 470

    draw_round_rect(
        c,
        left_x,
        left_y,
        left_w,
        left_h,
        r=16,
        fill_color=WHITE,
        stroke_color=LINE,
    )

    draw_small_caps(c, left_x + 16, left_y + left_h - 22, "Airport / study point", size=8.5, color=MUTED)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(left_x + 16, left_y + left_h - 50, data["airport_name"])

    draw_fake_map(c, left_x + 12, left_y + 108, left_w - 24, 300, data["airport_name"])

    draw_text(
        c,
        left_x + 16,
        left_y + 76,
        data["coordinates"],
        size=10,
        color=TEXT,
        max_width=left_w - 32,
    )

    draw_text(
        c,
        left_x + 16,
        left_y + 56,
        "Study location used for PVGIS simulation.",
        size=9,
        color=MUTED,
        max_width=left_w - 32,
        leading=11,
    )

    # Right column
    rx = left_x + left_w + gap
    rw = page_w - MARGIN - rx

    if data["accent"] == "green":
        concl_bg, concl_border, concl_main = GREEN_BG, GREEN_BORDER, GREEN
        risk_accent = "green"
    elif data["accent"] == "gold":
        concl_bg, concl_border, concl_main = GOLD_BG, GOLD_BORDER, GOLD
        risk_accent = "red"
    else:
        concl_bg, concl_border, concl_main = RED_BG, RED_BORDER, RED
        risk_accent = "red"

    # Conclusion card - main hero block
    conclusion_x = rx
    conclusion_y = 548
    conclusion_w = rw
    conclusion_h = 126

    draw_round_rect(
        c,
        conclusion_x,
        conclusion_y,
        conclusion_w,
        conclusion_h,
        r=16,
        fill_color=concl_bg,
        stroke_color=concl_border,
        line_width=1.15,
    )

    draw_small_caps(c, conclusion_x + 16, conclusion_y + conclusion_h - 22, "Overall conclusion", size=8.5, color=MUTED)

    draw_title(
        c,
        conclusion_x + 16,
        conclusion_y + conclusion_h - 50,
        data["overall_conclusion_title"],
        size=15.5,
        color=concl_main,
        max_width=conclusion_w - 32,
        leading=17.5,
    )

    draw_text(
        c,
        conclusion_x + 16,
        conclusion_y + 18,
        data["overall_conclusion_text"],
        size=10,
        color=TEXT,
        max_width=conclusion_w - 32,
        leading=12,
    )

    # KPI row
    kpi_y = 390
    kpi_h = 128
    kpi_w = (rw - gap) / 2

    kpi_card(
        c,
        rx,
        kpi_y,
        kpi_w,
        kpi_h,
        "Required operation",
        data["required_operation"],
        "Applied to all devices",
        accent="blue",
    )

    kpi_card(
        c,
        rx + kpi_w + gap,
        kpi_y,
        kpi_w,
        kpi_h,
        "Worst blackout risk",
        data["worst_blackout_risk"],
        data["worst_blackout_pct"],
        accent=risk_accent,
    )

    # Interpretation - cleaner, lighter
    interp_y_top = 350
    draw_small_caps(c, rx, interp_y_top, "Interpretation", size=8.5, color=MUTED)
    draw_text(
        c,
        rx,
        interp_y_top - 22,
        data["interpretation"],
        size=10.2,
        color=TEXT,
        max_width=rw,
        leading=13,
    )

    # Recommendation - strong decision bar
    rec_x = rx
    rec_y = 156
    rec_w = rw
    rec_h = 54

    draw_round_rect(
        c,
        rec_x,
        rec_y,
        rec_w,
        rec_h,
        r=12,
        fill_color=SOFT_BG,
        stroke_color=LINE,
    )

    draw_small_caps(c, rec_x + 16, rec_y + 33, "Recommended action", size=8.5, color=MUTED)
    draw_text(
        c,
        rec_x + 16,
        rec_y + 15,
        data["recommendation"],
        size=10.8,
        color=NAVY,
        font="Helvetica-Bold",
        max_width=rec_w - 32,
        leading=12,
    )

    # Methodology strip
    strip_x = MARGIN
    strip_y = 74
    strip_w = page_w - 2 * MARGIN
    strip_h = 40

    draw_round_rect(
        c,
        strip_x,
        strip_y,
        strip_w,
        strip_h,
        r=10,
        fill_color=WHITE,
        stroke_color=LINE,
    )

    draw_text(
        c,
        strip_x + 12,
        strip_y + 14,
        data["methodology_note"],
        size=9,
        color=MUTED,
        max_width=strip_w - 24,
        leading=10.5,
    )

    draw_footer(c, MARGIN, data["report_id"], data["revision"], 2)
