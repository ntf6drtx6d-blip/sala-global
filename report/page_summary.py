from .theme import (
    PAGE_H, MARGIN, TOP_RULE_Y, LINE, WHITE, MUTED, NAVY, BLUE, TEXT,
    RED_BG, RED_BORDER, RED,
    GREEN_BG, GREEN_BORDER, GREEN,
    GOLD_BG, GOLD_BORDER, GOLD,
)
from .helpers import draw_round_rect, draw_small_caps, draw_title, draw_text
from .blocks import draw_footer, kpi_card, draw_fake_map


def draw_summary_page(c, data):
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, TOP_RULE_Y, c._pagesize[0] - MARGIN, TOP_RULE_Y)

    draw_small_caps(c, MARGIN, PAGE_H - 72, "Management summary", size=10.5, color=BLUE)
    draw_title(c, MARGIN, PAGE_H - 108, "Feasibility result", size=28, color=NAVY)

    # left context block
    left_x = MARGIN
    left_y = 214
    left_w = 228
    left_h = 470

    draw_round_rect(c, left_x, left_y, left_w, left_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, left_x + 16, left_y + left_h - 22, "Airport / study point", size=8.5, color=MUTED)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 15.5)
    c.drawString(left_x + 16, left_y + left_h - 50, data["airport_name"])

    draw_fake_map(c, left_x + 14, left_y + 104, left_w - 28, 292, data["airport_name"])

    c.setFillColor(TEXT)
    c.setFont("Helvetica", 10.0)
    c.drawString(left_x + 16, left_y + 72, data["coordinates"])

    draw_text(
        c,
        left_x + 16,
        left_y + 50,
        "Study location used for solar irradiation modelling (PVGIS-based simulation).",
        size=9.2,
        color=MUTED,
        max_width=left_w - 32,
        leading=11.5,
    )

    # right side
    rx = left_x + left_w + 24
    rw = c._pagesize[0] - MARGIN - rx

    if data["accent"] == "green":
        concl_bg, concl_border, concl_main = GREEN_BG, GREEN_BORDER, GREEN
        risk_accent = "green"
    elif data["accent"] == "gold":
        concl_bg, concl_border, concl_main = GOLD_BG, GOLD_BORDER, GOLD
        risk_accent = "red"
    else:
        concl_bg, concl_border, concl_main = RED_BG, RED_BORDER, RED
        risk_accent = "red"

    # conclusion
    conclusion_y = 550
    conclusion_h = 132

    draw_round_rect(c, rx, conclusion_y, rw, conclusion_h, r=16, fill_color=concl_bg, stroke_color=concl_border, line_width=1.15)
    draw_small_caps(c, rx + 16, conclusion_y + conclusion_h - 22, "Overall conclusion", size=8.5, color=MUTED)

    draw_title(
        c,
        rx + 16,
        conclusion_y + conclusion_h - 52,
        data["overall_conclusion_title"],
        size=16.2,
        color=concl_main,
        max_width=rw - 32,
        leading=18.2,
    )

    draw_text(
        c,
        rx + 16,
        conclusion_y + 18,
        data["overall_conclusion_text"],
        size=10.0,
        color=TEXT,
        max_width=rw - 32,
        leading=12,
    )

    # KPI row
    kpi_y = 382
    kpi_h = 138
    gap = 14
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

    # interpretation
    interp_y = 228
    interp_h = 126

    draw_round_rect(c, rx, interp_y, rw, interp_h, r=16, fill_color=WHITE, stroke_color=LINE)
    draw_small_caps(c, rx + 16, interp_y + interp_h - 22, "Interpretation", size=8.5, color=MUTED)

    draw_text(
        c,
        rx + 16,
        interp_y + interp_h - 48,
        data["interpretation"],
        size=10.5,
        color=TEXT,
        max_width=rw - 32,
        leading=13.2,
    )

    # recommendation
    rec_y = 154
    rec_h = 52

    draw_round_rect(c, rx, rec_y, rw, rec_h, r=14, fill_color="#F8FAFC", stroke_color=LINE)
    draw_small_caps(c, rx + 16, rec_y + 31, "Recommendation", size=8.5, color=MUTED)

    draw_text(
        c,
        rx + 118,
        rec_y + 31,
        data["recommendation"],
        size=10.2,
        color=TEXT,
        max_width=rw - 134,
        leading=11.5,
    )

    # methodology strip
    strip_y = 74
    strip_h = 42

    draw_round_rect(c, MARGIN, strip_y, c._pagesize[0] - 2 * MARGIN, strip_h, r=12, fill_color=WHITE, stroke_color=LINE)

    draw_text(
        c,
        MARGIN + 14,
        strip_y + 15,
        data["methodology_note"],
        size=9.4,
        color=MUTED,
        max_width=c._pagesize[0] - 2 * MARGIN - 28,
        leading=11,
    )

    draw_footer(c, MARGIN, data["report_id"], data["revision"], 2)
