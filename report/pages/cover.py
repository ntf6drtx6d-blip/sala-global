from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from ..styles import TITLE, BODY, SMALL, BOLD, LINE, SOFT_BG, WHITE


PAGE_WIDTH = 510
LABEL_COL = 110
VALUE_COL = PAGE_WIDTH - LABEL_COL


def _format_selected_devices(data):
    devices = data.get("selected_devices", [])
    if not devices:
        return Paragraph("Not specified", BODY)

    if len(devices) <= 4:
        text = "<br/>".join(devices)
    else:
        text = "<br/>".join(devices[:4]) + f"<br/>+ {len(devices) - 4} more"

    return Paragraph(text, BODY)


def build_cover(data):
    story = []

    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Solar Airfield Lighting System", TITLE))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Feasibility assessment for the selected solar AGL configuration.",
        BODY,
    ))
    story.append(Spacer(1, 20))

    airport_block = Paragraph(
        f'<b>{data["airport_name"]}</b>',
        BODY
    )

    devices_block = _format_selected_devices(data)

    info_data = [
        ["Report ID", Paragraph(data["report_id"], BODY)],
        ["Date", Paragraph(data["date"], BODY)],
        ["Airport", airport_block],
        ["Selected device set", devices_block],
    ]

    info_table = Table(info_data, colWidths=[LABEL_COL, VALUE_COL])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7ECF2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    methodology_title = Table(
        [[Paragraph("SALA Verification Methodology", BOLD)]],
        colWidths=[PAGE_WIDTH],
    )
    methodology_title.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(methodology_title)
    story.append(Spacer(1, 8))

    methodology_body = Table(
        [[Paragraph(
            """
            Prepared under the <b>SALA Solar AGL Design Manual</b>.<br/><br/>
            Based on <b>PVGIS</b> off-grid simulation and independent solar data from the
            <b>Joint Research Centre (JRC), European Commission</b>.
            """,
            BODY
        )]],
        colWidths=[PAGE_WIDTH],
    )
    methodology_body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(methodology_body)
    story.append(Spacer(1, 12))

    trust_strip = Table(
        [[Paragraph(
            "Independent basis: PVGIS — Joint Research Centre (JRC), European Commission.",
            SMALL
        )]],
        colWidths=[PAGE_WIDTH],
    )
    trust_strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(trust_strip)

    story.append(PageBreak())
    return story
