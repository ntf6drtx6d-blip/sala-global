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

SOFT_BG = colors.HexColor("#F8FAFC")
WHITE = colors.white

TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Heading1"],
    fontSize=24,
    leading=28,
    textColor=NAVY,
)

SUBTITLE = ParagraphStyle(
    "SUBTITLE",
    parent=styles["Heading2"],
    fontSize=14,
    leading=18,
    textColor=NAVY,
)

BODY = ParagraphStyle(
    "BODY",
    parent=styles["BodyText"],
    fontSize=10,
    leading=13,
    textColor=TEXT,
)

SMALL = ParagraphStyle(
    "SMALL",
    parent=styles["BodyText"],
    fontSize=9,
    leading=11,
    textColor=MUTED,
)

BOLD = ParagraphStyle(
    "BOLD",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=TEXT,
)

BIG = ParagraphStyle(
    "BIG",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=20,
    textColor=NAVY,
)
