from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

styles = getSampleStyleSheet()

PAGE_BG = colors.white
NAVY = colors.HexColor("#0F172A")
TEXT = colors.HexColor("#344054")
MUTED = colors.HexColor("#667085")
LINE = colors.HexColor("#DDE3EA")

BLUE = colors.HexColor("#1F4FBF")
BLUE_SOFT = colors.HexColor("#EEF4FF")
BLUE_BORDER = colors.HexColor("#D6E4FF")

GREEN = colors.HexColor("#067647")
GREEN_SOFT = colors.HexColor("#ECFDF3")
GREEN_BORDER = colors.HexColor("#ABEFC6")

RED = colors.HexColor("#B42318")
RED_SOFT = colors.HexColor("#FEF3F2")
RED_BORDER = colors.HexColor("#F7C7C1")

GOLD = colors.HexColor("#B54708")
GOLD_SOFT = colors.HexColor("#FFF7DB")
GOLD_BORDER = colors.HexColor("#F5C451")

TITLE_EYEBROW = ParagraphStyle(
    "TITLE_EYEBROW",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=12,
    textColor=BLUE,
    alignment=TA_LEFT,
    spaceAfter=6,
)

COVER_TITLE = ParagraphStyle(
    "COVER_TITLE",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=26,
    leading=30,
    textColor=NAVY,
    spaceAfter=8,
)

SECTION_TITLE = ParagraphStyle(
    "SECTION_TITLE",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=24,
    leading=28,
    textColor=NAVY,
    spaceAfter=8,
)

CARD_LABEL = ParagraphStyle(
    "CARD_LABEL",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    textColor=MUTED,
    spaceAfter=6,
)

BODY = ParagraphStyle(
    "BODY",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=TEXT,
)

BODY_SMALL = ParagraphStyle(
    "BODY_SMALL",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=11,
    textColor=MUTED,
)

BODY_BOLD = ParagraphStyle(
    "BODY_BOLD",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=TEXT,
)

BIG_VALUE = ParagraphStyle(
    "BIG_VALUE",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=22,
    textColor=NAVY,
)

CONCLUSION_TITLE = ParagraphStyle(
    "CONCLUSION_TITLE",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=18,
    textColor=NAVY,
)

RECOMMENDATION = ParagraphStyle(
    "RECOMMENDATION",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
)
