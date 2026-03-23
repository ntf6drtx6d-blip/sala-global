from .theme import (
    WHITE, LINE, SOFT_BG, MUTED, TEXT, NAVY,
    RED, RED_BG, RED_BORDER,
    BLUE, BLUE_SOFT, BLUE_BORDER,
    GREEN, GREEN_BG, GREEN_BORDER,
    GOLD, GOLD_BG, GOLD_BORDER,
)
from .helpers import draw_round_rect, draw_small_caps, draw_text


def draw_footer(c, margin, report_id, revision, page_no):
    c.setStrokeColor(LINE)
    c.line(margin, 50, c._pagesize[0] - margin, 50)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 34, f"{report_id}  |  {revision}")
    c.drawRightString(c._pagesize[0] - margin, 34, f"Page {page_no}")


def kpi_card(c, x, y, w, h, title, value, subtitle="", accent="red"):
    if accent == "red":
        bg, border, main = RED_BG, RED_BORDER, RED
    elif accent == "blue":
        bg, border, main = BLUE_SOFT, BLUE_BORDER, BLUE
    elif accent == "green":
        bg, border, main = GREEN_BG, GREEN_BORDER, GREEN
    elif accent == "gold":
        bg, border, main = GOLD_BG, GOLD_BORDER, GOLD
    else:
        bg, border, main = SOFT_BG, LINE, NAVY

    draw_round_rect(c, x, y, w, h, r=14, fill_color=bg, stroke_color=border, line_width=1.15)
    draw_small_caps(c, x + 16, y + h - 22, title, size=8.6, color=MUTED)

    c.setFont("Helvetica-Bold", 21)
    c.setFillColor(main)
    c.drawString(x + 16, y + h - 56, str(value))

    if subtitle:
        draw_text(
            c,
            x + 16,
            y + 18,
            subtitle,
            size=8.8,
            color=MUTED,
            font="Helvetica",
            max_width=w - 32,
            leading=10.5,
        )


def draw_fake_map(c, x, y, w, h, airport_name):
    draw_round_rect(c, x, y, w, h, r=12, fill_color=WHITE, stroke_color=LINE)

    c.setFillColor("#F4F7F5")
    c.roundRect(x + 1, y + 1, w - 2, h - 2, 11, stroke=0, fill=1)

    c.setStrokeColor("#D8E1E6")
    c.setLineWidth(0.8)
    c.line(x + 18, y + 24, x + w - 22, y + h - 26)
    c.line(x + 28, y + h - 18, x + w - 18, y + 54)
    c.line(x + 10, y + h * 0.56, x + w - 10, y + h * 0.53)
    c.line(x + 40, y + 16, x + 78, y + h - 18)

    c.setDash(2, 2)
    c.line(x + 60, y + 8, x + 118, y + h - 8)
    c.line(x + w - 85, y + 14, x + w - 24, y + h - 18)
    c.setDash()

    px = x + w * 0.54
    py = y + h * 0.47
    c.setFillColor("#C24D3A")
    c.circle(px, py, 6, stroke=0, fill=1)

    c.setFont("Helvetica", 11)
    c.setFillColor("#98A2B3")
    label = str(airport_name).upper()[:20]
    c.drawString(x + 24, y + h * 0.60, label)
