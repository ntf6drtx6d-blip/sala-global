# report/report.py

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

import os
from datetime import datetime

PAGE_W, PAGE_H = A4

SALA_LOGO = "sala_logo.png"
EU_LOGO = "logo_en.gif"

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
        c.drawString(x, y, str(text))
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
            if line:
                c.drawString(x, yy, line)
                yy -= leading
            line = w

    if line:
        c.drawString(x, yy, line)

    return yy


def draw_text_center(c, x_center, y, text, size=11, color=TEXT, font="Helvetica"):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawCentredString(x_center, y, str(text))


def draw_title(c, x, y, text, size=28, color=NAVY, max_width=None, leading=None):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)

    if max_width is None:
        c.drawString(x, y, str(text))
        return y

    return draw_text(
        c,
        x,
        y,
        text,
        size=size,
        color=color,
        font="Helvetica-Bold",
        max_width=max_width,
        leading=leading or size * 1.08,
    )


def draw_small_caps(c, x, y, text, size=10, color=MUTED):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, str(text).upper())


def draw_label_value(c, x, y, label, value, label_w=110, value_size=10.8):
    c.setFont("Helvetica-Bold", 9.2)
    c.setFillColor(MUTED)
    c.drawString(x, y, str(label).upper())

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


def draw_fake_map(c, x, y, w, h, airport_name):
    draw_round_rect(c, x, y, w, h, r=12, fill_color=WHITE, stroke_color=LINE)
    c.setFillColor(HexColor("#F4F7F5"))
    c.roundRect(x + 1, y + 1, w - 2, h - 2, 11, stroke=0, fill=1)

    c.setStrokeColor(HexColor("#D8E1E6"))
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
    c.setFillColor(HexColor("#C24D3A"))
    c.circle(px, py, 6, stroke=0, fill=1)

    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#98A2B3"))
    label = str(airport_name).upper()[:20]
    c.drawString(x + 24, y + h * 0.60, label)


def kpi_card(c, x, y, w, h, title, value, subtitle="", accent="red"):
    if accent == "red":
        bg, border, main = RED_BG, RED_BORDER, RED
    elif accent == "blue":
        bg, border, main = BLUE_SOFT, BLUE_BORDER, BLUE
    elif accent == "green":
        bg, border, main = GREEN_BG, GREEN_BORDER, GREEN
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
            size=9.4,
            color=MUTED,
            font="Helvetica",
            max_width=w - 32,
            leading=11.5,
        )


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


def _build_data(loc, required_hours, results, overall, document_no, revision_no, airport_label, report_date):
    airport_name = airport_label or loc.get("label", "Study point")
    country = loc.get("country", "") or ""
    coordinates = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

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
        accent = "green"
    elif state == "mixed":
        conclusion_title = "The selected system partially meets the required operating profile."
        conclusion_text = "At least one selected device remains below the required operating profile."
        interpretation = (
            "The selected configuration is not fully compliant because at least one device remains below "
            "requirement under worst-case solar conditions."
        )
        recommendation = "Review the non-compliant device configuration before deployment."
        accent = "gold"
    else:
        conclusion_title = "The selected system does not meet the required operating profile."
        conclusion_text = "The selected configuration does not support the required operating profile year-round."
        interpretation = (
            "The system does not sustain the required operating profile under worst-case solar conditions. "
            "The result indicates insufficient energy recovery over the annual cycle, resulting in prolonged "
            "periods of blackout exposure."
        )
        recommendation = "System redesign is required to achieve the defined operating profile."
        accent = "red"

    revision_text = f"Rev {int(revision_no):02d} – Issued for Review" if revision_no else "Rev 01 – Issued for Review"

    return {
        "report_id": document_no or "SALA-SFS-2026-000134",
        "revision": revision_text,
        "date": report_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        "status": "Issued for Review",
        "prepared_under": "Prepared under SALA-SAGL-100 methodology",
        "accent": accent,
    }


# -----------------------------
# PAGE 1 - COVER V2
# -----------------------------

def _draw_cover_page(c, data):
    margin = 46
    top = PAGE_H - 40

    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(margin, top, PAGE_W - margin, top)

    if os.path.exists(SALA_LOGO):
        draw_logo(c, SALA_LOGO, margin, PAGE_H - 92, w=72)

    if os.path.exists(EU_LOGO):
        draw_logo(c, EU_LOGO, PAGE_W - margin - 98, PAGE_H - 90, w=98)

    # document eyebrow
    draw_small_caps(c, margin, PAGE_H - 128, "SALA Standardized Feasibility Study", size=10.5, color=BLUE)

    # strong title block
    draw_title(
        c,
        margin,
        PAGE_H - 162,
        "Solar Airfield Lighting\nSystem",
        size=30,
        color=NAVY,
        max_width=320,
        leading=32,
    )

    # right-side quick status block
    right_x = PAGE_W - margin - 215
    right_y = PAGE_H - 190
    draw_round_rect(c, right_x, right_y, 215, 88, r=14, fill_color=BLUE_SOFT, stroke_color=BLUE_BORDER)
    draw_small_caps(c, right_x + 16, right_y + 62, "Document status", size=8.6, color=MUTED)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(BLUE)
    c.drawString(right_x + 16, right_y + 38, data["status"])
    c.setFont("Helvetica", 10)
    c.setFillColor(TEXT)
    c.drawString(right_x + 16, right_y + 18, data["prepared_under"])

    # project identity plate
    plate_x = margin
    plate_y = PAGE_H - 330
    plate_w = PAGE_W - 2 * margin
    plate_h = 134
    draw_round_rect(c, plate_x, plate_y, plate_w, plate_h, r=16, fill_color=SOFT_BG, stroke_color=LINE)

    # inner divider lines
    c.setStrokeColor(HexColor("#E5EAF1"))
    c.setLineWidth(1)
    c.line(plate_x + plate_w / 2, plate_y + 18, plate_x + plate_w / 2, plate_y + plate_h - 18)
    c.line(plate_x + 20, plate_y + 72, plate_x + plate_w - 20, plate_y + 72)

    # upper row
    draw_label_value(c, plate_x + 22, plate_y + 96, "Report ID", data["report_id"], label_w=88, value_size=10.5)
    draw_label_value(c, plate_x + 22, plate_y + 52, "Revision", data["revision"], label_w=88, value_size=10.5)

    draw_label_value(c, plate_x + plate_w / 2 + 22, plate_y + 96, "Airport", data["airport_name"], label_w=72, value_size=10.5)
    draw_label_value(c, plate_x + plate_w / 2 + 22, plate_y + 52, "Location", data["country"] or "-", label_w=72, value_size=10.5)

    # lower strip
    draw_label_value(c, plate_x + 22, plate_y + 22, "Date", data["date"], label_w=88, value_size=10.5)
    draw_label_value(c, plate_x + plate_w / 2 + 22, plate_y + 22, "Coordinates", data["coordinates"], label_w=72, value_size=10.5)

    # methodology basis block
    meth_y = PAGE_H - 500
    meth_h = 122
    draw_round_rect(c, margin, meth_y, plate_w, meth_h, r=16, fill_color=WHITE, stroke_color=LINE)

    draw_small_caps(c, margin + 22, meth_y + 94, "Methodology basis", size=9.2, color=MUTED)
    draw_title(c, margin + 22, meth_y + 64, data["prepared_under"], size=18, color=NAVY, max_width=plate_w - 44)
    draw_text(
        c,
        margin + 22,
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
    draw_round_rect(c, margin, strip_y, plate_w, strip_h, r=14, fill_color=WHITE, stroke_color=LINE)
    draw_small_caps(c, margin + 20, strip_y + 50, "Document basis", size=8.5, color=MUTED)
    draw_text(
        c,
        margin + 20,
        strip_y + 26,
        "Prepared as a formal engineering-style study under SALA-approved report structure, with document identity, revision control and project-specific registration.",
        size=10,
        color=TEXT,
        max_width=plate_w - 40,
        leading=12.5,
    )

    # footer
    c.setStrokeColor(LINE)
    c.line(margin, 58, PAGE_W - margin, 58)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 42, f"{data['report_id']}  |  {data['revision']}")
    c.drawRightString(PAGE_W - margin, 42, "Page 1")


# -----------------------------
# PAGE 2 - SUMMARY V2
# -----------------------------

def _draw_summary_page(c, data):
    margin = 46
    top = PAGE_H - 40

    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(margin, top, PAGE_W - margin, top)

    draw_small_caps(c, margin, PAGE_H - 72, "Management summary", size=10.5, color=BLUE)
    draw_title(c, margin, PAGE_H - 108, "Feasibility result", size=28, color=NAVY)

    # left context block
    left_x = margin
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
    c.setFont("Helvetica", 10.3)
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

    # right content
    rx = left_x + left_w + 24
    rw = PAGE_W - margin - rx

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
        conclusion_y + conclusion_h - 54,
        data["overall_conclusion_title"],
        size=18.5,
        color=concl_main,
        max_width=rw - 32,
        leading=21,
    )

    draw_text(
        c,
        rx + 16,
        conclusion_y + 18,
        data["overall_conclusion_text"],
        size=10.6,
        color=TEXT,
        max_width=rw - 32,
        leading=13,
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
        "Applied to all selected devices.",
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

    # recommendation bar
    rec_y = 154
    rec_h = 52
    draw_round_rect(c, rx, rec_y, rw, rec_h, r=14, fill_color=SOFT_BG, stroke_color=LINE)
    draw_small_caps(c, rx + 16, rec_y + 31, "Recommendation", size=8.5, color=MUTED)
    draw_text(
        c,
        rx + 118,
        rec_y + 31,
        data["recommendation"],
        size=10.8,
        color=TEXT,
        max_width=rw - 134,
        leading=12.5,
    )

    # methodology strip
    strip_y = 74
    strip_h = 42
    draw_round_rect(c, margin, strip_y, PAGE_W - 2 * margin, strip_h, r=12, fill_color=WHITE, stroke_color=LINE)
    draw_text(
        c,
        margin + 14,
        strip_y + 15,
        data["methodology_note"],
        size=9.4,
        color=MUTED,
        max_width=PAGE_W - 2 * margin - 28,
        leading=11,
    )

    # footer
    c.setStrokeColor(LINE)
    c.line(margin, 50, PAGE_W - margin, 50)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(margin, 34, f"{data['report_id']}  |  {data['revision']}")
    c.drawRightString(PAGE_W - margin, 34, "Page 2")


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
    revision_no=0,
    document_no="",
    airport_label="",
    report_date="",
    reviewer=None,
):
    data = _build_data(
        loc=loc,
        required_hours=required_hours,
        results=results,
        overall=overall,
        document_no=document_no,
        revision_no=revision_no,
        airport_label=airport_label,
        report_date=report_date,
    )

    c = canvas.Canvas(out_path, pagesize=A4)
    _draw_cover_page(c, data)
    c.showPage()
    _draw_summary_page(c, data)
    c.showPage()
    c.save()
