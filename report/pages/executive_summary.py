from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak

from ..styles import (
    TITLE, CARD_TITLE, KPI_VALUE, BODY, BODY_BOLD, SMALL, TABLE_HEADER, FOOTER,
    WHITE, BORDER, PAGE_WIDTH, SPACE_3, PRIMARY_SOFT, GREEN_SOFT, AMBER_SOFT, RED_SOFT, GREEN, AMBER, RED
)


def _status_palette(label: str):
    if label == "PASS":
        return GREEN_SOFT, GREEN
    if label == "NEAR THRESHOLD":
        return AMBER_SOFT, AMBER
    return RED_SOFT, RED


def _card(items, width, bg=WHITE, border=BORDER, padding=10):
    t = Table([[i] for i in items], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return t


def _kpi(title, value, subtitle, width):
    return _card([Paragraph(title, SMALL), Spacer(1, 2), Paragraph(value, KPI_VALUE), Spacer(1, 2), Paragraph(subtitle, SMALL)], width)


def build_summary(data):
    story = [Paragraph("Feasibility Result", TITLE), Spacer(1, SPACE_3)]

    fill, line = _status_palette(data["overall_result_label"])
    conclusion = _card([
        Paragraph("Overall conclusion", SMALL),
        Paragraph(data["overall_result_title"], BODY_BOLD),
        Spacer(1, 4),
        Paragraph(data["overall_result_text"], BODY),
    ], 250, bg=fill, border=line, padding=12)

    kpi1 = _kpi("Airport lighting requirement", data["required_operation"], "Required daily operating profile", 122)
    kpi2 = _kpi("Days with 0% battery depletion", f"{data['max_blackout_days']} days/year",
                "Days when battery is expected to reach 0% and required operation may not be sustained.", 122)
    kpis = Table([[kpi1, kpi2]], colWidths=[122, 122])
    kpis.setStyle(TableStyle([("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0)]))

    cov_fill, cov_line = _status_palette("PASS" if data["devices_pass_count"] == data["devices_total"] else ("NEAR THRESHOLD" if data["devices_fail_count"] == 0 else "FAIL"))
    coverage = _card([Paragraph(f"{data['devices_pass_count']} of {data['devices_total']} devices meet requirement", BODY_BOLD)], 250, bg=cov_fill, border=cov_line, padding=10)

    left = Table([[conclusion], [Spacer(1, 8)], [kpis], [Spacer(1, 8)], [coverage]], colWidths=[250])
    left.setStyle(TableStyle([("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0)]))

    header = [Paragraph("Device", TABLE_HEADER), Paragraph("Days with 0% battery depletion", TABLE_HEADER), Paragraph("Result", TABLE_HEADER)]
    rows = [header]
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_SOFT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for idx, d in enumerate(data["devices"], start=1):
        fill_i, line_i = _status_palette(d["result_class"])
        rows.append([Paragraph(d["name"], BODY), Paragraph(str(d["annual_blackout_days"]), BODY), Paragraph(d["result_label"], BODY_BOLD)])
        style_cmds += [("TEXTCOLOR", (2, idx), (2, idx), line_i), ("BACKGROUND", (2, idx), (2, idx), fill_i)]

    tbl = Table(rows, colWidths=[185, 110, 65], repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    right = _card([Paragraph("Device feasibility summary", CARD_TITLE), Spacer(1, 6), tbl], 255, WHITE, BORDER, 10)

    top = Table([[left, right]], colWidths=[250, 255])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(top)
    story.append(Spacer(1, 10))

    note = Paragraph("Devices are classified using annual days with 0% battery depletion. PASS means no expected battery depletion. NEAR THRESHOLD means limited depletion (1–3 days/year). FAIL means more than 3 days/year of expected battery depletion.", SMALL)
    story.append(note)
    story.append(Spacer(1, 18))

    footer = Table([[Paragraph(data["footer_note"], FOOTER), Paragraph("Page 2", FOOTER)]], colWidths=[430, 85])
    footer.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.7, BORDER), ("TOPPADDING", (0, 0), (-1, -1), 6), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(footer)
    story.append(PageBreak())
    return story
