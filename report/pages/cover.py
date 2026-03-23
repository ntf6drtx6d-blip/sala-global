import os

from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)

from ..styles import (
    TITLE_EYEBROW,
    COVER_TITLE,
    BODY,
    BODY_SMALL,
    BODY_BOLD,
    CARD_LABEL,
    NAVY,
    TEXT,
    MUTED,
    LINE,
    SOFT_BG,
    WHITE,
    BLUE,
    BLUE_SOFT,
    BLUE_BORDER,
)

SALA_LOGO = "sala_logo.png"
EU_LOGO = "logo_en.gif"


def _logo_or_spacer(path, width, height):
    if os.path.exists(path):
        img = Image(path, width=width, height=height)
        return img
    return Spacer(width, height)


def build_cover(data):
    story = []

    # top logos row
    logos = Table(
        [[
            _logo_or_spacer(SALA_LOGO, 60, 36),
            _logo_or_spacer(EU_LOGO, 80, 36),
        ]],
        colWidths=[220, 220],
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
    story.append(Spacer(1, 20))

    # title + status side by side
    title_block = [
        Paragraph("SALA Standardized Feasibility Study", TITLE_EYEBROW),
        Paragraph("Solar Airfield Lighting System", COVER_TITLE),
        Paragraph(
            "Formal engineering-style feasibility assessment for solar airfield lighting deployment.",
            BODY,
        ),
    ]

    status_box = Table(
        [[
            Paragraph("DOCUMENT STATUS", CARD_LABEL),
            Paragraph(f"<font color='#1F4FBF'><b>{data['status']}</b></font>", BODY_BOLD),
            Paragraph("METHODOLOGY", CARD_LABEL),
            Paragraph("SALA-SAGL-100", BODY),
        ]],
        colWidths=[180],
    )
    status_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, BLUE_BORDER),
        ("ROUNDEDCORNERS", [12, 12, 12, 12]),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    hero = Table(
        [[title_block, status_box]],
        colWidths=[280, 190],
    )
    hero.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hero)
    story.append(Spacer(1, 24))

    # document plate
    plate_data = [
        [
            Paragraph("<b>REPORT ID</b>", CARD_LABEL),
            Paragraph(data["report_id"], BODY),
            Paragraph("<b>AIRPORT</b>", CARD_LABEL),
            Paragraph(data["airport_name"], BODY),
        ],
        [
            Paragraph("<b>REVISION</b>", CARD_LABEL),
            Paragraph(data["revision"], BODY),
            Paragraph("<b>LOCATION</b>", CARD_LABEL),
            Paragraph(data["country"], BODY),
        ],
        [
            Paragraph("<b>DATE</b>", CARD_LABEL),
            Paragraph(data["date"], BODY),
            Paragraph("<b>COORDINATES</b>", CARD_LABEL),
            Paragraph(data["coordinates"], BODY),
        ],
    ]

    plate = Table(plate_data, colWidths=[70, 165, 85, 150])
    plate.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#E7ECF2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(plate)
    story.append(Spacer(1, 22))

    # methodology block
    meth = Table(
        [[
            Paragraph("METHODOLOGY BASIS", CARD_LABEL),
            Paragraph("Prepared under SALA-SAGL-100 methodology", BODY_BOLD),
            Paragraph(
                "This report presents the feasibility outcome for the selected solar airfield lighting "
                "configuration based on long-term solar irradiation data and off-grid performance simulation.",
                BODY,
            ),
        ]],
        colWidths=[470],
    )
    meth.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(meth)
    story.append(Spacer(1, 18))

    # document basis strip
    basis = Table(
        [[
            Paragraph("DOCUMENT BASIS", CARD_LABEL),
            Paragraph(
                "Prepared as a formal engineering-style study under SALA-approved report structure, "
                "with document identity, revision control and project-specific registration.",
                BODY_SMALL,
            ),
        ]],
        colWidths=[470],
    )
    basis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(basis)
    story.append(PageBreak())

    return story
