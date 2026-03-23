from .theme import (
    PAGE_H, MARGIN, TOP_RULE_Y,
    LINE, WHITE, MUTED, NAVY, BLUE, TEXT,
    RED_BG, RED_BORDER, RED,
    GREEN_BG, GREEN_BORDER, GREEN,
    GOLD_BG, GOLD_BORDER, GOLD,
)
from .helpers import draw_round_rect, draw_small_caps, draw_title, draw_text
from .blocks import draw_footer, kpi_card, draw_fake_map


def draw_summary_page(c, data):
    page_w = c._pagesize[0]

    # top rule
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, TOP_RULE_Y, page_w - MARGIN, TOP_RULE_Y)

    draw_small_caps(c, MARGIN, PAGE_H - 70, "Management summary", size=10, color=BLUE)
    draw_title(c, MARGIN, PAGE_H - 105, "Feasibility result", size=28)

    # layout constants
    gap = 16

    # LEFT COLUMN (map)
    left_x = MARGIN
    left_w = 230
    left_y = 200
    left_h = 480

    draw_round_rect(c, left_x, left_y, left_w, left_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, left_x + 16, left_y + left_h - 22, "Airport / study point", size=8.5)

    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(NAVY)
    c.drawString(left_x + 16, left_y + left_h - 50, data["airport_name"])

    draw_fake_map(c, left_x + 12, left_y + 110, left_w - 24, 300, data["airport_name"])

    draw_text(
        c,
        left_x + 16,
        left_y + 80,
        data["coordinates"],
        size=10,
    )

    draw_text(
        c,
        left_x + 16,
        left_y + 60,
        "Study location used for PVGIS simulation.",
        size=9,
        color=MUTED,
    )

    # RIGHT COLUMN
    rx = left_x + left_w + gap
    rw = page_w - MARGIN - rx

    if data["accent"] == "green":
        bg, border, main = GREEN_BG, GREEN_BORDER, GREEN
        risk = "green"
    elif data["accent"] == "gold":
        bg, border, main = GOLD_BG, GOLD_BORDER, GOLD
        risk = "red"
    else:
        bg, border, main = RED_BG, RED_BORDER, RED
        risk = "red"

    y = PAGE_H - 150

    # CONCLUSION
    h = 120
    draw_round_rect(c, rx, y - h, rw, h, r=16, fill_color=bg, stroke_color=border)

    draw_small_caps(c, rx + 16, y - 22, "Overall conclusion", size=8.5)

    draw_title(
        c,
        rx + 16,
        y - 50,
        data["overall_conclusion_title"],
        size=16,
        max_width=rw - 32,
        leading=18,
    )

    draw_text(
        c,
        rx + 16,
        y - h + 20,
        data["overall_conclusion_text"],
        size=10,
        max_width=rw - 32,
    )

    y -= (h + gap)

    # KPI
    kpi_h = 130
    kpi_w = (rw - gap) / 2

    kpi_card(
        c,
        rx,
        y - kpi_h,
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
        y - kpi_h,
        kpi_w,
        kpi_h,
        "Worst blackout risk",
        data["worst_blackout_risk"],
        data["worst_blackout_pct"],
        accent=risk,
    )

    y -= (kpi_h + gap)

    # INTERPRETATION (no heavy box → cleaner)
    draw_small_caps(c, rx, y, "Interpretation", size=8.5)

    draw_text(
        c,
        rx,
        y - 20,
        data["interpretation"],
        size=10,
        max_width=rw,
    )

    y -= 80

    # RECOMMENDATION (clean bar)
    draw_round_rect(c, rx, y - 40, rw, 40, r=10, fill_color="#F8FAFC", stroke_color=LINE)

    draw_small_caps(c, rx + 16, y - 18, "Recommendation", size=8.5)

    draw_text(
        c,
        rx + 130,
        y - 18,
        data["recommendation"],
        size=10,
        max_width=rw - 140,
    )

    y -= 60

    # METHODOLOGY STRIP
    draw_round_rect(c, MARGIN, 70, page_w - 2 * MARGIN, 40, r=10, fill_color=WHITE, stroke_color=LINE)

    draw_text(
        c,
        MARGIN + 12,
        84,
        data["methodology_note"],
        size=9,
        color=MUTED,
        max_width=page_w - 2 * MARGIN - 24,
    )

    # footer
    draw_footer(c, MARGIN, data["report_id"], data["revision"], 2)    c.drawString(left_x + 16, left_y + 72, data["coordinates"])

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
