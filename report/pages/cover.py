import os

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors

from ..styles import TITLE, BODY, SMALL, BOLD, LINE, SOFT_BG, WHITE


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SALA_LOGO = os.path.join(BASE_DIR, "assets", "sala_logo.png")
JRC_LOGO = os.path.join(BASE_DIR, "assets", "jrc_logo.jpg")


def _logo_or_spacer(path, width, height):
    if os.path.exists(path):
        return Image(path, width=width, height=height)
    return Spacer(width, height)


def build_cover(data):
    story = []

    # ------------------------------------------------------------------
    # TOP LOGO STRIP
    # ------------------------------------------------------------------
    left_logo = _logo_or_spacer(SALA_LOGO, 58, 58)

    right_logo = _logo_or_spacer(JRC_LOGO, 110, 40)
    right_text = Paragraph("PVGIS (JRC, European Commission)", SMALL)

    right_block = Table(
        [[right_logo], [right_text]],
        colWidths=[180],
    )
    right_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    logos = Table(
        [[left_logo, right_block]],
        colWidths=[90, 420],
    )
    logos.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(logos)
    story.append(Spacer(1, 26))

    # ------------------------------------------------------------------
    # TITLE BLOCK
    # ------------------------------------------------------------------
    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Solar Airfield Lighting System", TITLE))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Independent feasibility assessment based on long-term solar data and off-grid simulation.",
        BODY,
    ))
    story.append(Spacer(1, 22))

    # ------------------------------------------------------------------
    # MAIN INFO TABLE
    # ------------------------------------------------------------------
    airport_block = Paragraph(
        f'<b>{data["airport_name"]}</b><br/><font color="#667085">{data["coordinates"]}</font>',
        BODY
    )

    info_data = [
        ["Report ID", Paragraph(data["report_id"], BODY)],
        ["Date", Paragraph(data["date"], BODY)],
        ["Airport", airport_block],
    ]

    info_table = Table(info_data, colWidths=[90, 390])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7ECF2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 22))

    # ------------------------------------------------------------------
    # METHODOLOGY TITLE BAR
    # ------------------------------------------------------------------
    methodology_title = Table(
        [[Paragraph("SALA Verification Methodology", BOLD)]],
        colWidths=[510],
    )
    methodology_title.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(methodology_title)
    story.append(Spacer(1, 8))

    # ------------------------------------------------------------------
    # METHODOLOGY BODY
    # ------------------------------------------------------------------
    methodology_body = Table(
        [[Paragraph(
            """
            Prepared under the <b>SALA Solar AGL Design Manual</b>.<br/><br/>
            Based on <b>PVGIS</b> off-grid simulation and independent solar data from the 
            <b>Joint Research Centre (JRC), European Commission</b>.
            """,
            BODY
        )]],
        colWidths=[510],
    )
    methodology_body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(methodology_body)
    story.append(Spacer(1, 14))

    # ------------------------------------------------------------------
    # TRUST STRIP
    # ------------------------------------------------------------------
    trust_strip = Table(
        [[Paragraph(
            "Independent basis: PVGIS — Joint Research Centre (JRC), European Commission.",
            SMALL
        )]],
        colWidths=[510],
    )
    trust_strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(trust_strip)

    story.append(PageBreak())
    return story
