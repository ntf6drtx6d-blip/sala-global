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
    # LOGOS
    # ------------------------------------------------------------------
    logos = Table(
        [[
            _logo_or_spacer(SALA_LOGO, 70, 40),
            _logo_or_spacer(JRC_LOGO, 120, 40),
        ]],
        colWidths=[220, 290],
    )
    logos.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(logos)
    story.append(Spacer(1, 22))

    # ------------------------------------------------------------------
    # TITLE BLOCK
    # ------------------------------------------------------------------
    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Solar Airfield Lighting System", TITLE))
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "Independent feasibility assessment of solar airfield lighting performance "
        "based on long-term solar irradiation data and off-grid simulation.",
        BODY,
    ))
    story.append(Spacer(1, 22))

    # ------------------------------------------------------------------
    # MAIN INFO TABLE
    # ------------------------------------------------------------------
    airport_block = f"""
    <b>{data["airport_name"]}</b><br/>
    <font size="9" color="#667085">{data["coordinates"]}</font>
    """

    info_data = [
        ["Report ID", data["report_id"]],
        ["Date", data["date"]],
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
    story.append(Spacer(1, 24))

    # ------------------------------------------------------------------
    # SALA VERIFICATION METHODOLOGY
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

    methodology_body = Table(
        [[Paragraph(
            """
            This report is prepared in accordance with the <b>SALA Solar AGL Design Manual</b>, 
            which establishes a standardized methodology for evaluating solar airfield lighting systems.
            <br/><br/>
            The assessment is based on independent solar resource data and off-grid performance simulation 
            using the <b>Photovoltaic Geographical Information System (PVGIS)</b>, developed by the 
            <b>Joint Research Centre (JRC) of the European Commission</b>.
            <br/><br/>
            PVGIS is a publicly available scientific platform providing long-term, satellite-derived solar 
            irradiation data and photovoltaic system performance modelling for both grid-connected and off-grid systems.
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
    story.append(Spacer(1, 16))

    # ------------------------------------------------------------------
    # TRUST STRIP
    # ------------------------------------------------------------------
    trust_strip = Table(
        [[Paragraph(
            "Independent data source and simulation basis: PVGIS — Joint Research Centre (JRC), European Commission.",
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
