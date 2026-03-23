# report/report.py

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from datetime import datetime
import os

PAGE_W, PAGE_H = A4

# -----------------------------
# OPTIONAL ASSETS
# -----------------------------

SALA_LOGO = "sala_logo.png" if os.path.exists("sala_logo.png") else None
EU_LOGO = "logo_en.gif" if os.path.exists("logo_en.gif") else None

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
    words = str(text).split()
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
    return draw_text(c, x, y, text, size=size, color=color, font="Helvetica-Bold", max_width=max_width, leading=size*1.12)

def draw_small_caps(c, x, y, text, size=10, color=MUTED):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, str(text).upper())

def draw_label_value(c, x, y, label, value, label_w=120, value_size=11):
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(MUTED)
    c.drawString(x, y, str(label))
    c.setFont("Helvetica", value_size)
    c.setFillColor(TEXT)
    c.drawString(x + label_w, y, str(value))

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

    draw_round_rect(c, x, y, w, h, r=14, fill_color=bg, stroke_color=border, line_width=1.2)
    draw_small_caps(c, x + 18, y + h - 24, title, size=9, color=MUTED)
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(main)
    c.drawString(x + 18, y + h - 62, str(value))
    if subtitle:
        draw_text(c, x + 18, y + 18, subtitle, size=10.5, color=MUTED, font="Helvetica", max_width=w - 36)

def draw_fake_map(c, x, y, w, h, airport_name, coordinates):
    # clean placeholder map-like block, since PDF cannot reuse live folium map directly
    draw_round_rect(c, x, y, w, h, r=12, fill_color=WHITE, stroke_color=LINE)

    # background zones
    c.setFillColor(HexColor("#F4F7F5"))
    c.roundRect(x + 1, y + 1, w - 2, h - 2, 11, stroke=0, fill=1)

    c.setStrokeColor(HexColor("#D9E2E7"))
    c.setLineWidth(0.8)

    # abstract roads / contours
    c.line(x + 20, y + 40, x + w - 30, y + h - 35)
    c.line(x + 35, y + h - 20, x + w - 20, y + 70)
    c.line(x + 10, y + h/2, x + w - 15, y + h/2 + 20)
    c.line(x + 25, y + 25, x + 80, y + h - 30)

    c.setDash(2, 2)
    c.line(x + 45, y + 10, x + 110, y + h - 10)
    c.line(x + w - 80, y + 18, x + w - 30, y + h - 20)
    c.setDash()

    # study point
    px = x + w * 0.50
    py = y + h * 0.47
    c.setFillColor(HexColor("#C24D3A"))
    c.circle(px, py, 6, stroke=0, fill=1)

    # caption-like labels
    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#98A2B3"))
    c.drawString(x + 30, y + h * 0.52, airport_name[:18].upper())

    c.setFont("Helvetica", 9.2)
    c.setFillColor(MUTED)
    c.drawString(x + 12, y + 10, coordinates)

# -----------------------------
# DATA BUILDING
# -----------------------------

def _annual_empty_battery_stats(results: dict):
    pcts = []
    for _, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is not None:
            try:
                pcts.append(float(pct))
            except Exception:
                pass

    if not pcts:
        return None, None

    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100.0)
    return worst_days, worst_pct

def _count_device_statuses(results: dict):
    total = len(results)
    passed = 0
    for _, r in results.items():
        if r.get("status") == "PASS":
            passed += 1
    failed = total - passed
    return total, passed, failed

def _overall_state(results: dict):
    total, passed, failed = _count_device_statuses(results)
    if total == 0:
        return "unknown"
    if passed == total:
        return "all_pass"
    if failed == total:
        return "none_pass"
    return "mixed"

def _build_report_data(loc, required_hours, results, overall, document_no="", revision_no=1, airport_label="", report_date=""):
    airport_name = airport_label or loc.get("label", "Study point")
    country = loc.get("country", "") or ""
    coordinates = f"{loc.get('lat', 0):.6f}, {loc.get('lon', 0):.6f}"

    worst_days, worst_pct = _annual_empty_battery_stats(results)
    state = _overall_state(results)

    if state == "all_pass":
        conclusion_title = "The selected system meets the required operating profile."
        conclusion_text = "The selected configuration supports the required operating profile year-round."
        interpretation = (
            "The system demonstrates sufficient energy autonomy and operational resilience "
            "to support continuous airfield operations under the defined profile."
        )
        recommendation = "Proceed with solar AGL deployment under the defined configuration."
        status_color = "green"
    elif state == "none_pass":
        conclusion_title = "The selected system does not meet the required operating profile."
        conclusion_text = "The selected configuration does not support the required operating profile year-round."
        interpretation = (
            "The system does not sustain the required operating profile under worst-case solar conditions. "
            "The result indicates insufficient energy recovery over the annual cycle, resulting in prolonged "
            "periods of blackout exposure."
        )
        recommendation = "System redesign is required to achieve the defined operating profile."
        status_color = "red"
    else:
        conclusion_title = "The selected system partially meets the required operating profile."
        conclusion_text = "At least one selected device remains below the required operating profile."
        interpretation = (
            "The selected configuration is not fully compliant because at least one device remains below "
            "requirement under worst-case solar conditions."
        )
        recommendation = "Review the non-compliant device configuration before deployment."
        status_color = "gold"

    if not document_no:
        year = datetime.now().strftime("%Y")
        document_no = f"SALA-SFS-{year}-000134"

    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    return {
        "report_id": document_no,
        "revision": f"Rev {int(revision_no):02d} – Issued for Review",
        "date": report_date,
        "airport_name": airport_name,
        "country": country,
        "coordinates": coordinates,
        "required_operation": f"{float(required_hours):.0f} hrs/day",
        "worst_blackout_risk": f"{worst_days} days/year" if worst_days is not None else "N/A",
        "worst_blackout_pct": f"{worst_pct:.1f}% of the year" if worst_pct is not None else "",
        "overall_conclusion_title": conclusion_title,
        "overall_conclusion_text": conclusion_text,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "methodology_note": (
            "This assessment is based on long-term solar irradiation data and hourly off-grid simulation "
            "methodology consistent with PVGIS (European Commission Joint Research Centre)."
        ),
        "status": "SALA Approved Style",
        "status_color": status_color,
        "prepared_under": "Prepared under SALA-SAGL-100 methodology",
    }

# -----------------------------
# PAGE 1
# -----------------------------

def _draw_cover_page(c, data):
    margin = 48
    top = PAGE_H - 42

    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(margin, top, PAGE_W - margin, top)

    if SALA_LOGO:
        draw_logo(c, SALA_LOGO, margin, PAGE_H - 105, w=76)

    if EU_LOGO:
        draw_logo(c, EU_LOGO, PAGE_W - margin - 102, PAGE_H - 102, w=102)

    draw_small_caps(c, margin, PAGE_H - 140, "SALA Standardized Feasibility Study", size=11, color=BLUE)
    draw_title(
        c,
        margin,
        PAGE_H - 178,
        "Solar Airfield Lighting System",
        size=27,
        color=NAVY,
        max_width=PAGE_W - 2 * margin - 30
    )

    # identity plate
    plate_x = margin
    plate_y = PAGE_H - 338
    plate_w = PAGE_W - 2 * margin
    plate_h = 118
    draw_round_rect(c, plate_x, plate_y, plate_w, plate_h, r=16, fill_color=SOFT_BG, stroke_color=LINE)

    draw_label_value(c, plate_x + 24, plate_y + 84, "Report ID", data["report_id"], label_w=100, value_size=11)
    draw_label_value(c, plate_x + 24, plate_y + 62, "Date", data["date"], label_w=100, value_size=11)
    draw_label_value(c, plate_x + 24, plate_y + 40, "Revision", data["revision"], label_w=100, value_size=11)

    draw_label_value(c, plate_x + 310, plate_y + 84, "Airport", data["airport_name"], label_w=75, value_size=11)
    draw_label_value(c, plate_x + 310, plate_y + 62, "Location", data["country"], label_w=75, value_size=11)
    draw_label_value(c, plate_x + 310, plate_y + 40, "Coordinates", data["coordinates"], label_w=75, value_size=11)

    badge_w = 172
    badge_h = 28
    badge_x = plate_x + plate_w - badge_w - 22
    badge_y = plate_y + 76
    draw_round_rect(c, badge_x, badge_y, badge_w, badge_h, r=14, fill_color=BLUE_SOFT, stroke_color=BLUE_BORDER)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(badge_x + badge_w / 2, badge_y + 9, data["status"])

    # methodology block
    box_y = PAGE_H - 510
    box_h = 148
    draw_round_rect(c, margin, box_y, plate_w, box_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, margin + 24, box_y + box_h - 24, "Methodology basis", size=10, color=MUTED)
    draw_title(c, margin + 24, box_y + box_h - 56, data["prepared_under"], size=18, color=NAVY, max_width=plate_w - 48)
    draw_text(
        c,
        margin + 24,
        box_y + box_h - 90,
        "This report presents the feasibility outcome for the selected solar airfield lighting configuration based on long-term solar irradiation data and off-grid performance simulation.",
        size=11,
        color=TEXT,
        max_width=plate_w - 48,
        leading=15
    )

    # trust strip
    strip_y = 118
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

    c.setStrokeColor(LINE)
    c.line(margin, 58, PAGE_W - margin, 58)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 42, f"{data['report_id']}  |  {data['revision']}")
    c.drawRightString(PAGE_W - margin, 42, "Page 1")

# -----------------------------
# PAGE 2
# -----------------------------

def _draw_summary_page(c, data):
    margin = 48
    top = PAGE_H - 42

    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(margin, top, PAGE_W - margin, top)

    draw_small_caps(c, margin, PAGE_H - 74, "Management summary", size=11, color=BLUE)
    draw_title(c, margin, PAGE_H - 114, "Feasibility result", size=28, color=NAVY)

    # left map/context block
    left_x = margin
    left_y = 222
    left_w = 230
    left_h = 460
    draw_round_rect(c, left_x, left_y, left_w, left_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, left_x + 18, left_y + left_h - 24, "Airport / study point", size=9, color=MUTED)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_x + 18, left_y + left_h - 56, data["airport_name"])

    draw_fake_map(c, left_x + 14, left_y + 86, left_w - 28, 300, data["airport_name"], data["coordinates"])

    c.setFont("Helvetica", 10.5)
    c.setFillColor(MUTED)
    c.drawString(left_x + 18, left_y + 58, data["coordinates"])
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

    # right area
    rx = left_x + left_w + 24
    rw = PAGE_W - margin - rx

    # conclusion color
    if data["status_color"] == "green":
        concl_bg, concl_border, concl_main = GREEN_BG, GREEN_BORDER, GREEN
    elif data["status_color"] == "gold":
        concl_bg, concl_border, concl_main = GOLD_BG, GOLD_BORDER, GOLD
    else:
        concl_bg, concl_border, concl_main = RED_BG, RED_BORDER, RED

    conclusion_y = 555
    conclusion_h = 127
    draw_round_rect(c, rx, conclusion_y, rw, conclusion_h, r=16, fill_color=concl_bg, stroke_color=concl_border, line_width=1.2)

    draw_small_caps(c, rx + 18, conclusion_y + conclusion_h - 24, "Overall conclusion", size=9, color=MUTED)
    draw_title(
        c,
        rx + 18,
        conclusion_y + conclusion_h - 63,
        data["overall_conclusion_title"],
        size=22,
        color=concl_main,
        max_width=rw - 36
    )
    draw_text(
        c,
        rx + 18,
        conclusion_y + 24,
        data["overall_conclusion_text"],
        size=11,
        color=TEXT,
        max_width=rw - 36
    )

    # KPI cards - only two
    kpi_y = 378
    kpi_h = 145
    gap = 16
    kpi_w = (rw - gap) / 2

    kpi_card(
        c, rx, kpi_y, kpi_w, kpi_h,
        "Required operation",
        data["required_operation"],
        "Required operating profile applied to all selected devices.",
        accent="blue"
    )

    kpi_card(
        c, rx + kpi_w + gap, kpi_y, kpi_w, kpi_h,
        "Worst blackout risk",
        data["worst_blackout_risk"],
        data["worst_blackout_pct"],
        accent="red" if data["status_color"] != "green" else "green"
    )

    # interpretation
    interp_y = 210
    interp_h = 142
    draw_round_rect(c, rx, interp_y, rw, interp_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, rx + 18, interp_y + interp_h - 24, "Interpretation", size=9, color=MUTED)
    draw_text(
        c,
        rx + 18,
        interp_y + interp_h - 50,
        data["interpretation"],
        size=11,
        color=TEXT,
        max_width=rw - 36,
        leading=15
    )

    # recommendation
    rec_y = 132
    rec_h = 58
    draw_round_rect(c, rx, rec_y, rw, rec_h, r=14, fill_color=SOFT_BG, stroke_color=LINE)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(rx + 18, rec_y + 36, "Recommendation")
    c.setFont("Helvetica", 11)
    c.setFillColor(TEXT)
    draw_text(c, rx + 128, rec_y + 36, data["recommendation"], size=11, color=TEXT, max_width=rw - 146)

    # methodology note strip
    strip_y = 70
    strip_h = 42
    draw_round_rect(c, margin, strip_y, PAGE_W - 2 * margin, strip_h, r=12, fill_color=WHITE, stroke_color=LINE)
    c.setFont("Helvetica", 9.8)
    c.setFillColor(MUTED)
    draw_text(c, margin + 16, strip_y + 15, data["methodology_note"], size=9.8, color=MUTED, max_width=PAGE_W - 2*margin - 32, leading=12)

    c.setStrokeColor(LINE)
    c.line(margin, 48, PAGE_W - margin, 48)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 32, f"{data['report_id']}  |  {data['revision']}")
    c.drawRightString(PAGE_W - margin, 32, "Page 2")

# -----------------------------
# PUBLIC API
# -----------------------------

def make_pdf(
    out_path,
    loc,
    required_hours,
    results,
    overall,
    project_name="",
    revision_no=1,
    document_no="",
    airport_label="",
    report_date="",
    reviewer=None,
):
    data = _build_report_data(
        loc=loc,
        required_hours=required_hours,
        results=results,
        overall=overall,
        document_no=document_no,
        revision_no=revision_no if revision_no else 1,
        airport_label=airport_label,
        report_date=report_date,
    )

    c = canvas.Canvas(out_path, pagesize=A4)
    _draw_cover_page(c, data)
    c.showPage()
    _draw_summary_page(c, data)
    c.showPage()
    c.save()
