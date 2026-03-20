from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker


def make_pdf(
    filename,
    loc,
    required_hrs,
    results,
    overall,
    worst_name,
    worst_gap,
    slope,
    airport_label,
    date_str,
    chart_image_path=None
):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # ---------- COVER ----------
    story.append(Spacer(1, 80))

    story.append(Paragraph(
        "<b>SALA Standardized Feasibility Study</b>",
        styles["Title"]
    ))

    story.append(Spacer(1, 20))

    story.append(Paragraph(
        f"<b>Airport:</b> {airport_label}",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Date:</b> {date_str}",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Location:</b> {loc['lat']:.5f}, {loc['lon']:.5f}",
        styles["Normal"]
    ))

    story.append(Spacer(1, 40))

    story.append(Paragraph(
        "<b>Prepared by SALA</b><br/>Solar Airfield Lighting Association",
        styles["Normal"]
    ))

    story.append(PageBreak())

    # ---------- EXEC SUMMARY ----------
    story.append(Paragraph("<b>1. Executive Summary</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))

    status_color = "green" if overall == "PASS" else "red"

    story.append(Paragraph(
        f"<b>Overall result:</b> <font color='{status_color}'>{overall}</font>",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Worst-case device:</b> {worst_name}",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Margin vs requirement:</b> {round(worst_gap,2)} hours",
        styles["Normal"]
    ))

    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "The analysis confirms whether the selected solar AGL configuration "
        "can operate continuously year-round under defined operating conditions.",
        styles["Normal"]
    ))

    story.append(PageBreak())

    # ---------- PROJECT CONTEXT ----------
    story.append(Paragraph("<b>2. Project Context</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        f"<b>Required operating profile:</b> {required_hrs} hours/day",
        styles["Normal"]
    ))

    story.append(Paragraph(
        "This study evaluates off-grid solar AGL systems using PVGIS simulation tools.",
        styles["Normal"]
    ))

    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Location</b>", styles["Heading2"]))
    story.append(Paragraph(
        f"{airport_label} ({loc['lat']:.5f}, {loc['lon']:.5f})",
        styles["Normal"]
    ))

    story.append(PageBreak())

    # ---------- RESULTS TABLE ----------
    story.append(Paragraph("<b>3. Technical Results</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))

    table_data = [[
        "Device", "Engine", "PV (W)", "Battery (Wh)",
        "Power (W)", "Status", "Margin"
    ]]

    for name, r in results.items():
        table_data.append([
            name,
            r["engine"],
            r["pv"],
            r["batt"],
            round(r["power"], 2),
            r["status"],
            round(r["min_margin"], 2)
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ]))

    story.append(table)
    story.append(PageBreak())

    # ---------- GRAPH ----------
    story.append(Paragraph("<b>4. Monthly Autonomy</b>", styles["Heading1"]))
    story.append(Spacer(1, 20))

    drawing = Drawing(400, 200)
    lp = LinePlot()
    lp.x = 50
    lp.y = 50
    lp.height = 125
    lp.width = 300

    data = []
    for name, r in results.items():
        series = [(i+1, r["hours"][i]) for i in range(12)]
        data.append(series)

    req_line = [(i+1, required_hrs) for i in range(12)]
    data.append(req_line)

    lp.data = data

    for i in range(len(data)):
        lp.lines[i].strokeWidth = 2
        lp.lines[i].symbol = makeMarker("Circle")

    drawing.add(lp)
    story.append(drawing)

    story.append(PageBreak())

    # ---------- METHODOLOGY ----------
    story.append(Paragraph("<b>5. Methodology</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "This study is based on PVGIS (European Commission JRC) tools.",
        styles["Normal"]
    ))

    story.append(Paragraph(
        "PVGIS performs hourly solar radiation modelling and off-grid system simulation.",
        styles["Normal"]
    ))

    story.append(Paragraph(
        "SALA uses PVGIS outputs and converts them into operational hours for AGL systems.",
        styles["Normal"]
    ))

    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "<b>Conclusion:</b> The system feasibility is determined based on the lowest-month performance.",
        styles["Normal"]
    ))

    doc.build(story)