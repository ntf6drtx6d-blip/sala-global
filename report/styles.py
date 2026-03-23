from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

styles = getSampleStyleSheet()

NAVY = colors.HexColor("#0F172A")
TEXT = colors.HexColor("#344054")
MUTED = colors.HexColor("#667085")
LINE = colors.HexColor("#DDE3EA")

BLUE_SOFT = colors.HexColor("#EEF4FF")
BLUE_BORDER = colors.HexColor("#D6E4FF")

RED_SOFT = colors.HexColor("#FEF3F2")
RED_BORDER = colors.HexColor("#F7C7C1")

SOFT_BG = colors.HexColor("#F8FAFC")

TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Heading1"],
    fontSize=24,
    leading=28,
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
