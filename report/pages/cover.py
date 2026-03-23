from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from ..styles import TITLE, BODY, SMALL, BOLD, LINE, SOFT_BG, WHITE


def build_cover(data):
    story = []

    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Solar Airfield Lighting System", TITLE))
    story.append(Spacer(1, 16))

    story.append(Paragraph(
        "Formal engineering-style feasibility assessment for solar airfield lighting deployment.",
        BODY
    ))
    story.append(Spacer(1, 20))

    table_data = [
        ["Report ID", data["report_id"], "Airport", data["airport_name"]],
        ["Revision", data["revision"], "Location", data["country"]],
        ["Date", data["date"], "Coordinates", data["coordinates"]],
    ]

    table = Table(table_data, colWidths=[70, 140, 80, 160])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "Prepared under SALA-SAGL-100 methodology",
        BOLD
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "This report presents the feasibility outcome for the selected solar airfield lighting configuration based on long-term solar irradiation data and off-grid simulation.",
        BODY
    ))

    story.append(PageBreak())
    return story
