# sala_report_first_two_pages.py
# First two pages of SALA report
# Visual direction: web UI style, but more consultant-grade / report-grade

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
import os

PAGE_W, PAGE_H = A4

# -----------------------------
# CONFIG / SAMPLE DATA
# -----------------------------

DATA = {
    "report_id": "SALA-SFS-2026-000134",
    "revision": "Rev 01 – Issued for Review",
    "date": "23 March 2026",
    "airport_name": "radom airport",
    "country": "Poland",
    "coordinates": "51.388745, 21.214478",
    "required_operation": "12 hrs/day",
    "worst_blackout_risk": "249 days/year",
    "worst_blackout_pct": "68.1% of the year",
    "overall_conclusion_title": "The selected device does not meet the required operating profile.",
    "overall_conclusion_text": "The selected device does not support the selected operating profile year-round.",
    "interpretation": (
        "The system does not sustain the required operating profile under worst-case solar conditions. "
        "The result indicates insufficient energy recovery over the annual cycle, resulting in prolonged "
        "periods of blackout exposure."
    ),
    "recommendation": "System redesign is required to achieve the defined operating profile.",
    "methodology_note": (
        "This assessment is based on long-term solar irradiation data and hourly off-grid simulation "
        "methodology consistent with PVGIS (European Commission Joint Research Centre)."
    ),
    "status": "SALA Approved Style",
    "prepared_under": "Prepared under SALA-SAGL-100 methodology",
}

# Optional assets
SALA_LOGO = "/mnt/data/sala_logo.png" if os.path.exists("/mnt/data/sala_logo.png") else None
EC_LOGO = "/mnt/data/ec_logo.png" if os.path.exists("/mnt/data/ec_logo.png") else None

# Optional cropped map screenshot from current summary render
MAP_IMAGE = None
for p in [
    "/mnt/data/current_report_render/page-1.png",
    "/mnt/data/sala_first_two_pages_render/page-2.png",
    "/mnt/data/sala_first_two_pages_render3/page-2.png",
]:
    if os.path.exists(p):
        MAP_IMAGE = p
        break

# -----------------------------
# COLORS
# -----------------------------

NAVY = HexColor("#0F172A")
TEXT = HexColor("#344054")
MUTED = HexColor("#667085")
LINE = HexColor("#DDE3EA")
SOFT_BG = HexColor("#F8FAFC")

RED = HexColor("#B42318")
RED_BG = HexColor("#FEF3F2")
RED_BORDER = HexColor("#F7C7C1")

BLUE = HexColor("#1F4FBF")
BLUE_SOFT = HexColor("#EEF4FF")
BLUE_BORDER = HexColor("#D6E4FF")

GREEN = HexColor("#067647")
GREEN_BG = HexColor("#ECFDF3")
GREEN_BORDER = HexColor("#ABEFC6")

GOLD = HexColor("#B54708")
GOLD_BG = HexColor("#FFF7DB")
GOLD_BORDER = HexColor("#F5C451")

WHITE = white

# -----------------------------
# HELPERS
# -----------------------------

def draw_round_rect(c, x, y, w, h, r=14, fill_color=WHITE, stroke_color=LINE, stroke=1, fill=1, line_width=1):
    c.setLineWidth(line_width)
    c.setStrokeColor(stroke_color)
    c.setFillColor(fill_color)
    c.roundRect(x, y, w, h, r, stroke=stroke, fill=fill)

def draw_text(c, x, y, text, size=11, color=TEXT, font="Helvetica", max_width=None, leading=None):
    c.setFillColor(color)
    c.setFont(font, size)
    if max_width is None:
        c.drawString(x, y, text)
        return y
    if leading is None:
        leading = size * 1.35
    words = text.split()
    line = ""
    yy = y
    for w in words:
        candidate = (line + " " + w).strip()
        if stringWidth(candidate, font, size) <= max_width:
            line = candidate
        else:
            c.drawString(x, yy, line)
            yy -= leading
            line = w
    if line:
        c.drawString(x, yy, line)
    return yy

def draw_title(c, x, y, text, size=28, color=NAVY, max_width=None):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    if max_width is None:
        c.drawString(x, y, text)
        return y
    return draw_text(c, x, y, text, size=size, color=color, font="Helvetica-Bold", max_width=max_width, leading=size*1.1)

def draw_small_caps(c, x, y, text, size=10, color=MUTED):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, text.upper())

def draw_label_value(c, x, y, label, value, label_w=120, value_size=11):
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(MUTED)
    c.drawString(x, y, label)
    c.setFont("Helvetica", value_size)
    c.setFillColor(TEXT)
    c.drawString(x + label_w, y, value)

def kpi_card(c, x, y, w, h, title, value, subtitle="", accent="red"):
    if accent == "red":
        bg, border, main = RED_BG, RED_BORDER, RED
    elif accent == "blue":
        bg, border, main = BLUE_SOFT, BLUE_BORDER, BLUE
    elif accent == "green":
        bg, border, main = GREEN_BG, GREEN_BORDER, GREEN
    else:
        bg, border, main = SOFT_BG, LINE, NAVY

    draw_round_rect(c, x, y, w, h, r=14, fill_color=bg, stroke_color=border, line_width=1.2)
    draw_small_caps(c, x + 18, y + h - 24, title, size=9, color=MUTED)
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(main)
    c.drawString(x + 18, y + h - 62, value)
    if subtitle:
        draw_text(c, x + 18, y + 18, subtitle, size=10.5, color=MUTED, font="Helvetica", max_width=w - 36)

def draw_logo(c, path, x, y, w=None, h=None):
    if not path or not os.path.exists(path):
        return
    img = ImageReader(path)
    iw, ih = img.getSize()
    if w and not h:
        h = w * ih / iw
    elif h and not w:
        w = h * iw / ih
    elif not w and not h:
        w, h = iw, ih
    c.drawImage(img, x, y, width=w, height=h, mask="auto")

def crop_and_draw_map(c, path, x, y, w, h):
    if not path or not os.path.exists(path):
        draw_round_rect(c, x, y, w, h, r=10, fill_color=SOFT_BG, stroke_color=LINE)
        draw_text(c, x + 20, y + h/2, "Map preview not available", size=12, color=MUTED)
        return

    from PIL import Image
    img = Image.open(path)
    iw, ih = img.size

    # crop left summary map block heuristically from screenshot
    # tuned for uploaded screenshots
    left = int(iw * 0.03)
    top = int(ih * 0.14)
    right = int(iw * 0.39)
    bottom = int(ih * 0.90)
    crop = img.crop((left, top, right, bottom))

    tmp = "/mnt/data/_tmp_summary_map.png"
    crop.save(tmp)

    draw_round_rect(c, x, y, w, h, r=12, fill_color=WHITE, stroke_color=LINE)
    c.drawImage(tmp, x + 1, y + 1, width=w - 2, height=h - 2, mask="auto")

# -----------------------------
# PAGE 1 - COVER
# -----------------------------

def draw_cover_page(c):
    margin = 48
    top = PAGE_H - 44

    # Top line
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(margin, top, PAGE_W - margin, top)

    # Logos row
    if SALA_LOGO:
        draw_logo(c, SALA_LOGO, margin, PAGE_H - 110, w=78)
    if EC_LOGO:
        draw_logo(c, EC_LOGO, PAGE_W - margin - 95, PAGE_H - 105, w=95)

    # Title block
    title_x = margin
    title_y = PAGE_H - 155
    draw_small_caps(c, title_x, title_y, "SALA Standardized Feasibility Study", size=11, color=BLUE)
    draw_title(
        c,
        title_x,
        title_y - 38,
        "Solar Airfield Lighting System",
        size=27,
        color=NAVY,
        max_width=PAGE_W - 2 * margin - 40
    )

    # Report identity plate
    plate_x = margin
    plate_y = PAGE_H - 340
    plate_w = PAGE_W - 2 * margin
    plate_h = 118
    draw_round_rect(c, plate_x, plate_y, plate_w, plate_h, r=16, fill_color=SOFT_BG, stroke_color=LINE)

    draw_label_value(c, plate_x + 24, plate_y + 84, "Report ID", DATA["report_id"], label_w=100, value_size=11)
    draw_label_value(c, plate_x + 24, plate_y + 62, "Date", DATA["date"], label_w=100, value_size=11)
    draw_label_value(c, plate_x + 24, plate_y + 40, "Revision", DATA["revision"], label_w=100, value_size=11)

    draw_label_value(c, plate_x + 310, plate_y + 84, "Airport", DATA["airport_name"], label_w=75, value_size=11)
    draw_label_value(c, plate_x + 310, plate_y + 62, "Location", DATA["country"], label_w=75, value_size=11)
    draw_label_value(c, plate_x + 310, plate_y + 40, "Coordinates", DATA["coordinates"], label_w=75, value_size=11)

    # Status badge
    badge_w = 172
    badge_h = 28
    badge_x = plate_x + plate_w - badge_w - 22
    badge_y = plate_y + 76
    draw_round_rect(c, badge_x, badge_y, badge_w, badge_h, r=14, fill_color=BLUE_SOFT, stroke_color=BLUE_BORDER)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(badge_x + badge_w/2, badge_y + 9, DATA["status"])

    # Methodology block
    box_y = PAGE_H - 515
    box_h = 150
    draw_round_rect(c, margin, box_y, plate_w, box_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, margin + 24, box_y + box_h - 24, "Methodology basis", size=10, color=MUTED)
    draw_title(c, margin + 24, box_y + box_h - 58, "Prepared under SALA-SAGL-100 methodology", size=18, color=NAVY, max_width=plate_w - 48)
    draw_text(
        c,
        margin + 24,
        box_y + box_h - 92,
        "This report presents the feasibility outcome for the selected solar airfield lighting configuration based on long-term solar irradiation data and off-grid performance simulation.",
        size=11,
        color=TEXT,
        max_width=plate_w - 48,
        leading=15
    )

    # Trust strip
    strip_y = 120
    strip_h = 78
    draw_round_rect(c, margin, strip_y, plate_w, strip_h, r=14, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, margin + 22, strip_y + 52, "Document basis", size=9, color=MUTED)
    draw_text(
        c,
        margin + 22,
        strip_y + 28,
        "Prepared as a formal engineering-style study under SALA-approved report structure, with document identity, revision control and project-specific registration.",
        size=10.5,
        color=TEXT,
        max_width=plate_w - 44
    )

    # Footer
    c.setStrokeColor(LINE)
    c.line(margin, 58, PAGE_W - margin, 58)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 42, f"{DATA['report_id']}  |  {DATA['revision']}")
    c.drawRightString(PAGE_W - margin, 42, "Page 1")

# -----------------------------
# PAGE 2 - MANAGEMENT SUMMARY
# -----------------------------

def draw_summary_page(c):
    margin = 48
    top = PAGE_H - 44

    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(margin, top, PAGE_W - margin, top)

    # Title
    draw_small_caps(c, margin, PAGE_H - 74, "Management summary", size=11, color=BLUE)
    draw_title(c, margin, PAGE_H - 114, "Feasibility result", size=28, color=NAVY)

    # Left map block
    left_x = margin
    left_y = 222
    left_w = 230
    left_h = 460
    draw_round_rect(c, left_x, left_y, left_w, left_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, left_x + 18, left_y + left_h - 24, "Airport / study point", size=9, color=MUTED)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_x + 18, left_y + left_h - 56, DATA["airport_name"])

    crop_and_draw_map(c, MAP_IMAGE, left_x + 14, left_y + 86, left_w - 28, 300)

    c.setFont("Helvetica", 10.5)
    c.setFillColor(MUTED)
    c.drawString(left_x + 18, left_y + 58, DATA["coordinates"])
    draw_text(
        c,
        left_x + 18,
        left_y + 38,
        "Study location used for solar irradiation modelling (PVGIS-based simulation).",
        size=9.8,
        color=MUTED,
        max_width=left_w - 36,
        leading=13
    )

    # Right side
    rx = left_x + left_w + 24
    rw = PAGE_W - margin - rx

    # Conclusion card
    conclusion_y = 555
    conclusion_h = 127
    draw_round_rect(c, rx, conclusion_y, rw, conclusion_h, r=16, fill_color=RED_BG, stroke_color=RED_BORDER, line_width=1.2)

    draw_small_caps(c, rx + 18, conclusion_y + conclusion_h - 24, "Overall conclusion", size=9, color=MUTED)
    draw_title(
        c,
        rx + 18,
        conclusion_y + conclusion_h - 63,
        DATA["overall_conclusion_title"],
        size=22,
        color=RED,
        max_width=rw - 36
    )
    draw_text(
        c,
        rx + 18,
        conclusion_y + 24,
        DATA["overall_conclusion_text"],
        size=11,
        color=TEXT,
        max_width=rw - 36
    )

    # KPI cards (ONLY 2 as requested)
    kpi_y = 378
    kpi_h = 145
    gap = 16
    kpi_w = (rw - gap) / 2

    kpi_card(
        c, rx, kpi_y, kpi_w, kpi_h,
        "Required operation",
        DATA["required_operation"],
        "Required operating profile applied to all selected devices.",
        accent="blue"
    )

    kpi_card(
        c, rx + kpi_w + gap, kpi_y, kpi_w, kpi_h,
        "Worst blackout risk",
        DATA["worst_blackout_risk"],
        DATA["worst_blackout_pct"],
        accent="red"
    )

    # Interpretation block
    interp_y = 210
    interp_h = 142
    draw_round_rect(c, rx, interp_y, rw, interp_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, rx + 18, interp_y + interp_h - 24, "Interpretation", size=9, color=MUTED)
    draw_text(
        c,
        rx + 18,
        interp_y + interp_h - 50,
        DATA["interpretation"],
        size=11,
        color=TEXT,
        max_width=rw - 36,
        leading=15
    )

    # Recommendation
    rec_y = 132
    rec_h = 58
    draw_round_rect(c, rx, rec_y, rw, rec_h, r=14, fill_color=SOFT_BG, stroke_color=LINE)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(rx + 18, rec_y + 36, "Recommendation")
    c.setFont("Helvetica", 11)
    c.setFillColor(TEXT)
    c.drawString(rx + 130, rec_y + 36, DATA["recommendation"])

    # Trust strip
    strip_y = 70
    strip_h = 42
    draw_round_rect(c, margin, strip_y, PAGE_W - 2*margin, strip_h, r=12, fill_color=WHITE, stroke_color=LINE)
    c.setFont("Helvetica", 9.8)
    c.setFillColor(MUTED)
    c.drawString(margin + 16, strip_y + 15, DATA["methodology_note"])

    # Footer
    c.setStrokeColor(LINE)
    c.line(margin, 48, PAGE_W - margin, 48)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 32, f"{DATA['report_id']}  |  {DATA['revision']}")
    c.drawRightString(PAGE_W - margin, 32, "Page 2")

# -----------------------------
# BUILD PDF
# -----------------------------

def build_pdf(out_path):
    c = canvas.Canvas(out_path, pagesize=A4)
    draw_cover_page(c)
    c.showPage()
    draw_summary_page(c)
    c.showPage()
    c.save()


if __name__ == "__main__":
    out = "/mnt/data/sala_first_two_pages_demo.pdf"
    build_pdf(out)
    print(out)
