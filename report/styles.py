from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

styles = getSampleStyleSheet()

NAVY = colors.HexColor("#0F172A")
TEXT = colors.HexColor("#344054")
MUTED = colors.HexColor("#667085")
LINE = colors.HexColor("#DDE3EA")

BLUE = colors.HexColor("#1F4FBF")
BLUE_SOFT = colors.HexColor("#EEF4FF")
BLUE_BORDER = colors.HexColor("#D6E4FF")

GREEN_SOFT = colors.HexColor("#ECFDF3")
GREEN_BORDER = colors.HexColor("#ABEFC6")

RED_SOFT = colors.HexColor("#FEF3F2")
RED_BORDER = colors.HexColor("#F7C7C1")

GOLD_SOFT = colors.HexColor("#FFF7DB")
GOLD_BORDER = colors.HexColor("#F5C451")

SOFT_BG = colors.HexColor("#F8FAFC")
WHITE = colors.white

TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=24,
    leading=28,
    textColor=NAVY,
    spaceAfter=0,
)

SUBTITLE = ParagraphStyle(
    "SUBTITLE",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=NAVY,
    spaceAfter=0,
)

BODY = ParagraphStyle(
    "BODY",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=TEXT,
    spaceAfter=0,
)

SMALL = ParagraphStyle(
    "SMALL",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=11,
    textColor=MUTED,
    spaceAfter=0,
)

BOLD = ParagraphStyle(
    "BOLD",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=TEXT,
    spaceAfter=0,
)

BIG = ParagraphStyle(
    "BIG",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=20,
    textColor=NAVY,
    spaceAfter=0,
)

BIG_BLUE = ParagraphStyle(
    "BIG_BLUE",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=20,
    textColor=BLUE,
    spaceAfter=0,
)

CARD_LABEL = ParagraphStyle(
    "CARD_LABEL",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    textColor=MUTED,
    spaceAfter=0,
)

CONCLUSION_TITLE = ParagraphStyle(
    "CONCLUSION_TITLE",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=18,
    textColor=NAVY,
    spaceAfter=0,
)

RECOMMENDATION = ParagraphStyle(
    "RECOMMENDATION",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
    spaceAfter=0,
)
