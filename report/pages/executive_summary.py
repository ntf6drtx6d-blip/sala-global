from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from ..styles import SECTION, BODY, SMALL, BOLD, BIG, LINE, WHITE, RED_SOFT, RED_BORDER, GREEN_SOFT, GREEN_BORDER, BLUE_SOFT

PAGE_WIDTH = 510

def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default

def _img(path, w, h):
    try:
        im = Image(path)
        im._restrictSize(w, h)
        return im
    except Exception:
        return Paragraph("Map / chart unavailable", SMALL)

def _kpi(title, value, subtitle, width=115):
    t = Table([[Paragraph(value, BIG)], [Paragraph(title, SMALL)], [Paragraph(subtitle, SMALL)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.7, LINE),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    return t

def build_executive_summary(data):
    story = []
    story.append(Paragraph("1. Executive Summary", SECTION))
    story.append(Spacer(1, 14))

    kpis = Table([[
        _kpi(_safe(data.get("overall_result_label")), _safe(data.get("overall_result_value")), "Overall result"),
        _kpi("Gap vs requirement", _safe(data.get("gap_vs_requirement")), ""),
        _kpi("Weakest month", _safe(data.get("weakest_month_short")), ""),
        _kpi("Strongest month", _safe(data.get("strongest_month_short")), ""),
    ]], colWidths=[117,117,117,117])
    kpis.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
    story.append(kpis)
    story.append(Spacer(1, 12))

    story.append(Paragraph(_safe(data.get("executive_summary")), BODY))
    story.append(Spacer(1, 14))

    left = _img(data.get("map_image_path"), 230, 170)
    method_rows = [
        [Paragraph("<b>Method</b>", SMALL), Paragraph("PVGIS off-grid autonomy evaluation", BODY)],
        [Paragraph("<b>Logic</b>", SMALL), Paragraph("Worst-month operating hours vs required hours/day", BODY)],
        [Paragraph("<b>Output</b>", SMALL), Paragraph("PASS / FAIL by weakest month", BODY)],
        [Paragraph("<b>Interpretation</b>", SMALL), Paragraph("Solar autonomy = guaranteed daily hours without blackout", BODY)],
        [Paragraph("<b>Prepared</b>", SMALL), Paragraph(_safe(data.get("date")), BODY)],
    ]
    right = Table(method_rows, colWidths=[85, 210])
    right.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.7,LINE),
        ("BACKGROUND",(0,0),(0,-1),BLUE_SOFT),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    top = Table([[left, right]], colWidths=[230, 280])
    top.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(top)
    story.append(Spacer(1, 12))

    loc_rows = [
        [Paragraph("<b>Location</b>", SMALL), Paragraph(_safe(data.get("airport_name")), BODY)],
        [Paragraph("<b>Coordinates</b>", SMALL), Paragraph(_safe(data.get("coordinates")), BODY)],
        [Paragraph("<b>Required hrs</b>", SMALL), Paragraph(_safe(data.get("required_operation")), BODY)],
        [Paragraph("<b>Base tilt</b>", SMALL), Paragraph(_safe(data.get("base_tilt")), BODY)],
        [Paragraph("<b>Azimuth mode</b>", SMALL), Paragraph(_safe(data.get("azimuth_mode")), BODY)],
    ]
    loc = Table(loc_rows, colWidths=[90, 130])
    loc.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.7,LINE),
        ("BACKGROUND",(0,0),(0,-1),BLUE_SOFT),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(loc)
    story.append(Spacer(1, 14))

    bar = Table([[Paragraph(
        f"<b>OVERALL: {_safe(data.get('overall_result_value'))}</b> &nbsp;&nbsp; "
        f"{_safe(data.get('overall_result_label'))} &nbsp;&nbsp; · &nbsp;&nbsp; "
        f"Weakest case: {_safe(data.get('gap_vs_requirement'))}",
        BODY)]], colWidths=[PAGE_WIDTH])
    bar.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), RED_BORDER if data.get("accent")=="red" else GREEN_BORDER),
        ("TEXTCOLOR",(0,0),(-1,-1), WHITE),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(bar)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "The system is assessed using PVGIS-based off-grid simulations. The decision criterion is the lowest month of the year relative to the required daily operating profile.",
        SMALL,
    ))
    story.append(Spacer(1, 180))
    footer = Table([[Paragraph("Prepared using PVGIS-based off-grid assessment methodology", SMALL),
                     Paragraph("Page 2", SMALL)]], colWidths=[420, 90])
    footer.setStyle(TableStyle([("LINEABOVE",(0,0),(-1,-1),0.7,LINE),("ALIGN",(1,0),(1,0),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),6)]))
    story.append(footer)
    story.append(PageBreak())
    return story
