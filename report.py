# report.py
import io
import os
from datetime import datetime

import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
    KeepTogether,
)

from utils import build_map_image, add_round_corners_and_shadow


# -----------------------------
# Brand / visual system
# -----------------------------
NAVY = colors.HexColor("#0F1F3D")
NAVY_2 = colors.HexColor("#16315F")
GOLD = colors.HexColor("#E7C65A")
LIGHT_BG = colors.HexColor("#F5F7FA")
MID_BG = colors.HexColor("#EEF2F7")
BORDER = colors.HexColor("#D6DCE5")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#667085")
PASS = colors.HexColor("#0F8A5F")
FAIL = colors.HexColor("#C0392B")
WHITE = colors.white

PAGE_W, PAGE_H = A4
LEFT = 16 * mm
RIGHT = 16 * mm
TOP = 18 * mm
BOTTOM = 14 * mm


# -----------------------------
# Helpers
# -----------------------------
def fmt(x, digits=1):
    try:
        return f"{float(x):.{digits}f}".rstrip("0").rstrip(".")
    except Exception:
        return str(x)


def month_names():
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _airport_label(loc, airport_label):
    return (airport_label or "").strip() or loc.get("label", "Unnamed location")


def _status_text(overall):
    return "TECHNICALLY FEASIBLE" if overall == "PASS" else "NOT TECHNICALLY FEASIBLE"


def _short_conclusion(overall, worst_name, worst_gap, required_hrs):
    if overall == "PASS":
        return (
            f"The analysed solar AGL configuration meets the required operating profile of "
            f"{fmt(required_hrs)} hours/day throughout the year. "
            f"The weakest case remains above the requirement by {fmt(abs(worst_gap), 2)} hours/day "
            f"({worst_name})."
        )
    return (
        f"The analysed solar AGL configuration does not meet the required operating profile of "
        f"{fmt(required_hrs)} hours/day throughout the year. "
        f"The weakest case falls short by {fmt(abs(worst_gap), 2)} hours/day "
        f"({worst_name}). Additional PV, battery capacity or reduced load is recommended."
    )


def _best_and_worst_month(results):
    all_points = []
    months = month_names()
    for device_name, r in results.items():
        for i, h in enumerate(r["hours"]):
            all_points.append((months[i], float(h), device_name))
    worst = min(all_points, key=lambda x: x[1]) if all_points else ("-", 0, "-")
    best = max(all_points, key=lambda x: x[1]) if all_points else ("-", 0, "-")
    return best, worst


def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "title",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=NAVY,
        spaceAfter=4,
        alignment=TA_LEFT,
    )

    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=MUTED,
        spaceAfter=0,
        alignment=TA_LEFT,
    )

    styles["section"] = ParagraphStyle(
        "section",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=NAVY,
        spaceAfter=7,
        spaceBefore=2,
    )

    styles["h2"] = ParagraphStyle(
        "h2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=TEXT,
        spaceAfter=5,
    )

    styles["body"] = ParagraphStyle(
        "body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        textColor=TEXT,
    )

    styles["small"] = ParagraphStyle(
        "small",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=MUTED,
    )

    styles["metric_value"] = ParagraphStyle(
        "metric_value",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=NAVY,
        alignment=TA_CENTER,
    )

    styles["metric_label"] = ParagraphStyle(
        "metric_label",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=MUTED,
        alignment=TA_CENTER,
    )

    styles["table_head"] = ParagraphStyle(
        "table_head",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10,
        textColor=WHITE,
        alignment=TA_CENTER,
    )

    styles["table_cell"] = ParagraphStyle(
        "table_cell",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=7.9,
        leading=10,
        textColor=TEXT,
    )

    styles["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=MUTED,
        alignment=TA_RIGHT,
    )

    return styles


# -----------------------------
# Header / footer
# -----------------------------
def draw_header_footer(canvas, doc):
    canvas.saveState()

    logo_path = "sala_logo.png"

    # header line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(LEFT, PAGE_H - 12 * mm, PAGE_W - RIGHT, PAGE_H - 12 * mm)

    # logo
    if os.path.exists(logo_path):
        try:
            canvas.drawImage(
                logo_path,
                LEFT,
                PAGE_H - 16 * mm,
                width=12 * mm,
                height=12 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # header title
    canvas.setFont("Helvetica-Bold", 8.8)
    canvas.setFillColor(NAVY)
    canvas.drawString(LEFT + 16 * mm, PAGE_H - 11.2 * mm, "SALA Standardized Feasibility Study for Solar AGL")

    # footer line
    canvas.setStrokeColor(BORDER)
    canvas.line(LEFT, BOTTOM - 1.5 * mm, PAGE_W - RIGHT, BOTTOM - 1.5 * mm)

    # footer text
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - RIGHT, BOTTOM - 6 * mm, f"Page {doc.page}")
    canvas.drawString(LEFT, BOTTOM - 6 * mm, "Prepared using PVGIS-based off-grid assessment methodology")

    canvas.restoreState()


def build_doc(filename):
    frame = Frame(LEFT, BOTTOM + 4 * mm, PAGE_W - LEFT - RIGHT, PAGE_H - TOP - BOTTOM - 10 * mm, id="normal")
    template = PageTemplate(id="main", frames=[frame], onPage=draw_header_footer)
    doc = BaseDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP + 8 * mm,
        bottomMargin=BOTTOM + 8 * mm,
        pageTemplates=[template],
    )
    return doc


# -----------------------------
# Visual building blocks
# -----------------------------
def metric_card(value, label, width, styles):
    t = Table(
        [
            [Paragraph(value, styles["metric_value"])],
            [Paragraph(label, styles["metric_label"])],
        ],
        colWidths=[width],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def info_table(rows, widths, styles):
    data = []
    for label, value in rows:
        data.append([
            Paragraph(f"<b>{label}</b>", styles["body"]),
            Paragraph(str(value), styles["body"])
        ])
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), MID_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def summary_status_band(overall, worst_name, styles):
    color = PASS if overall == "PASS" else FAIL
    text = (
        f"<b>OVERALL: {overall}</b> &nbsp;&nbsp;&nbsp; {_status_text(overall)}"
        f"&nbsp;&nbsp;&nbsp; • &nbsp;&nbsp;&nbsp; Weakest case: {worst_name}"
    )
    t = Table([[Paragraph(text, ParagraphStyle(
        "status_band",
        parent=styles["body"],
        fontName="Helvetica-Bold",
        fontSize=10.2,
        leading=13,
        textColor=WHITE,
        alignment=TA_LEFT,
    ))]], colWidths=[PAGE_W - LEFT - RIGHT])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def build_modern_chart(required_hrs, results, airport_label):
    months = month_names()

    plt.figure(figsize=(10.5, 4.9))

    # device lines
    for device_name, r in results.items():
        plt.plot(
            months,
            r["hours"],
            linewidth=2.3,
            marker="o",
            markersize=4.6,
            label=device_name,
        )

    # requirement line
    plt.axhline(
        y=required_hrs,
        linestyle=(0, (6, 4)),
        linewidth=2.0,
        label=f"Required hrs ({fmt(required_hrs)})",
    )

    plt.title(f"Solar Autonomy (Guaranteed Operating Hours) – {airport_label}", fontsize=12, pad=12)
    plt.ylabel("hrs/day", fontsize=9)
    plt.grid(axis="y", alpha=0.22)
    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.gca().spines["left"].set_color("#B6C0CC")
    plt.gca().spines["bottom"].set_color("#B6C0CC")
    plt.xticks(fontsize=8.5)
    plt.yticks(fontsize=8.5)
    plt.legend(loc="upper right", fontsize=8, frameon=False)
    plt.tight_layout()

    bio = io.BytesIO()
    plt.savefig(bio, format="png", dpi=220, bbox_inches="tight")
    plt.close()
    bio.seek(0)
    return bio


def build_device_summary_table(results, styles):
    rows = [[
        Paragraph("Device", styles["table_head"]),
        Paragraph("Engine", styles["table_head"]),
        Paragraph("PV", styles["table_head"]),
        Paragraph("Battery", styles["table_head"]),
        Paragraph("Tilt", styles["table_head"]),
        Paragraph("Azimuth", styles["table_head"]),
        Paragraph("Lowest-month difference (hrs)", styles["table_head"]),
        Paragraph("Status", styles["table_head"]),
        Paragraph("Fail months", styles["table_head"]),
        Paragraph("Power consumption (W)", styles["table_head"]),
    ]]

    for device_name, r in results.items():
        fail_txt = ", ".join(r["fail_months"]) if r["fail_months"] else "—"
        rows.append([
            Paragraph(device_name, styles["table_cell"]),
            Paragraph(str(r["engine"]), styles["table_cell"]),
            Paragraph(f"{fmt(r['pv'])} W", styles["table_cell"]),
            Paragraph(f"{fmt(r['batt'])} Wh", styles["table_cell"]),
            Paragraph(f"{fmt(r['tilt'])}°", styles["table_cell"]),
            Paragraph(f"{fmt(r['azim'])}°", styles["table_cell"]),
            Paragraph(f"{fmt(r['min_margin'], 2)} hrs", styles["table_cell"]),
            Paragraph(str(r["status"]), styles["table_cell"]),
            Paragraph(fail_txt, styles["table_cell"]),
            Paragraph(f"{fmt(r['power'], 2)}", styles["table_cell"]),
        ])

    widths = [39*mm, 20*mm, 13*mm, 16*mm, 11*mm, 12*mm, 25*mm, 12*mm, 28*mm, 18*mm]
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FAIL),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def build_monthly_table(required_hrs, results, styles):
    months = month_names()
    device_names = list(results.keys())

    head = [Paragraph("Month", styles["table_head"]), Paragraph("Required (hrs)", styles["table_head"])]
    for d in device_names:
        head.append(Paragraph(d, styles["table_head"]))

    rows = [head]

    for i, m in enumerate(months):
        row = [
            Paragraph(m, styles["table_cell"]),
            Paragraph(fmt(required_hrs), styles["table_cell"]),
        ]
        for d in device_names:
            row.append(Paragraph(fmt(results[d]["hours"][i], 1), styles["table_cell"]))
        rows.append(row)

    col_widths = [18*mm, 23*mm]
    device_col_w = max(28*mm, (PAGE_W - LEFT - RIGHT - sum(col_widths)) / max(1, len(device_names)))
    col_widths += [device_col_w] * len(device_names)

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MID_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# -----------------------------
# Main PDF builder
# -----------------------------
def make_pdf(
    out_path,
    loc,
    required_hrs,
    results,
    overall,
    worst_name,
    worst_gap,
    header_tilt_text,
    airport_label,
    date_for_header,
    az_override,
):
    styles = build_styles()
    airport = _airport_label(loc, airport_label)
    date_text = date_for_header or datetime.now().strftime("%Y-%m-%d %H:%M")

    best_month, worst_month = _best_and_worst_month(results)

    doc = build_doc(str(out_path))
    story = []

    # ---------------------------------
    # Cover page
    # ---------------------------------
    logo_path = "sala_logo.png"

    story.append(Spacer(1, 38 * mm))
    if os.path.exists(logo_path):
        try:
            story.append(RLImage(logo_path, width=28*mm, height=28*mm))
            story.append(Spacer(1, 10 * mm))
        except Exception:
            pass

    story.append(Paragraph("SALA Standardized Feasibility Study for Solar AGL", styles["title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(airport, styles["subtitle"]))
    story.append(Spacer(1, 18 * mm))

    cover_tbl = info_table([
        ("Project / Location", airport),
        ("Coordinates", f"{fmt(loc['lat'], 5)}, {fmt(loc['lon'], 5)}"),
        ("Generated", date_text),
        ("Required operating profile", f"{fmt(required_hrs)} hrs/day"),
        ("Assessment basis", "PVGIS off-grid autonomy and annual worst-month evaluation"),
        ("Prepared by", "SALA — Solar Airfield Lighting Association"),
    ], [46*mm, 120*mm], styles)

    story.append(cover_tbl)
    story.append(Spacer(1, 18 * mm))

    cover_conclusion = _short_conclusion(overall, worst_name, worst_gap, required_hrs)
    cover_box = Table([[Paragraph(
        f"<b>{_status_text(overall)}</b><br/>{cover_conclusion}",
        ParagraphStyle(
            "cover_conclusion",
            parent=styles["body"],
            fontName="Helvetica",
            fontSize=10.2,
            leading=14,
            textColor=WHITE,
            alignment=TA_LEFT,
        )
    )]], colWidths=[PAGE_W - LEFT - RIGHT])
    cover_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(cover_box)
    story.append(PageBreak())

    # ---------------------------------
    # Executive summary + project definition
    # ---------------------------------
    story.append(Paragraph("1. Executive Summary", styles["section"]))

    metric_w = (PAGE_W - LEFT - RIGHT - 3 * 4*mm) / 4
    metrics = Table([[
        metric_card(overall, "Overall result", metric_w, styles),
        metric_card(fmt(abs(worst_gap), 2) + " hrs", "Gap vs requirement", metric_w, styles),
        metric_card(worst_month[0], "Weakest month", metric_w, styles),
        metric_card(best_month[0], "Strongest month", metric_w, styles),
    ]], colWidths=[metric_w] * 4)
    metrics.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(metrics)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(
        _short_conclusion(overall, worst_name, worst_gap, required_hrs),
        styles["body"]
    ))
    story.append(Spacer(1, 5 * mm))

    left_rows = [
        ("Location", airport),
        ("Coordinates", f"{fmt(loc['lat'], 5)}, {fmt(loc['lon'], 5)}"),
        ("Required hrs", f"{fmt(required_hrs)} hrs/day"),
        ("Base tilt", str(header_tilt_text)),
        ("Azimuth mode", str(az_override) if az_override is not None else "Automatic"),
    ]

    right_rows = [
        ("Method", "PVGIS off-grid autonomy evaluation"),
        ("Logic", "Worst-month operating hours vs required hours/day"),
        ("Output", "PASS / FAIL by weakest month"),
        ("Interpretation", "Solar autonomy = guaranteed daily hours without blackout"),
        ("Prepared", date_text),
    ]

    map_img = build_map_image(loc["lat"], loc["lon"], zoom=6, px_width=1800, px_height=1000, pin_scale=2.2)
    map_img = add_round_corners_and_shadow(map_img, radius=16, shadow=10)

    left_block = Table([
        [RLImage(map_img, width=74*mm, height=48*mm)],
        [Spacer(1, 2*mm)],
        [info_table(left_rows, [28*mm, 42*mm], styles)],
    ], colWidths=[76*mm])

    right_block = info_table(right_rows, [30*mm, 70*mm], styles)

    top_tbl = Table([[left_block, right_block]], colWidths=[80*mm, 100*mm])
    top_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(top_tbl)
    story.append(Spacer(1, 5 * mm))

    story.append(summary_status_band(overall, worst_name, styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "The system is assessed using PVGIS-based off-grid simulations. "
        "The decision criterion is the lowest month of the year relative to the required daily operating profile.",
        styles["small"]
    ))
    story.append(PageBreak())

    # ---------------------------------
    # Technical results + graph
    # ---------------------------------
    story.append(Paragraph("2. Technical Results", styles["section"]))

    chart_png = build_modern_chart(required_hrs, results, airport)
    story.append(RLImage(chart_png, width=175*mm, height=82*mm))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "The chart above shows guaranteed daily operating hours by month for the selected configuration(s), "
        "compared against the required operating profile.",
        styles["small"]
    ))
    story.append(Spacer(1, 4 * mm))

    story.append(build_device_summary_table(results, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Lowest-month difference (hrs) = how many hours the weakest month is above or below the required daily operating profile. "
        "Positive values indicate surplus; negative values indicate deficit.",
        styles["small"]
    ))
    story.append(PageBreak())

    # ---------------------------------
    # Monthly detail
    # ---------------------------------
    story.append(Paragraph("3. Monthly Operating Profile", styles["section"]))
    story.append(build_monthly_table(required_hrs, results, styles))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("4. Methodology", styles["section"]))
    methodology_text = (
        "This study uses PVGIS as the external calculation engine for solar resource and off-grid performance assessment. "
        "PVGIS is developed by the Joint Research Centre (European Commission) and uses long-term solar radiation datasets "
        "such as SARAH and ERA5 / ERA5-Land. SALA does not replace PVGIS with an internal solar model. "
        "Instead, SALA sends the relevant input parameters to PVGIS, retrieves the resulting outputs, and organizes them "
        "into a device-level feasibility study. The assessment is based on annual worst-month performance versus required "
        "daily operating hours."
    )
    story.append(Paragraph(methodology_text, styles["body"]))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("5. Consultant Conclusion", styles["section"]))
    if overall == "PASS":
        conclusion_text = (
            f"The analysed configuration is technically feasible for the defined operating profile of "
            f"{fmt(required_hrs)} hours per day. Based on the PVGIS-derived annual assessment, no monthly energy deficit "
            f"has been identified under the selected system definition. The recommended next step is engineering validation "
            f"of installation details, shading conditions, and final hardware selection."
        )
    else:
        conclusion_text = (
            f"The analysed configuration is not technically feasible for the defined operating profile of "
            f"{fmt(required_hrs)} hours per day. Based on the PVGIS-derived annual assessment, the configuration experiences "
            f"energy deficit in one or more months. The recommended next step is to increase PV capacity, increase battery reserve, "
            f"reduce power demand, or revise the operating profile."
        )
    story.append(Paragraph(conclusion_text, styles["body"]))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(
        "This report is intended as a feasibility assessment document. Final design decisions should consider installation geometry, "
        "site-specific shading, maintenance assumptions, and operational constraints.",
        styles["small"]
    ))

    doc.build(story)