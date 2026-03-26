from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

styles = getSampleStyleSheet()

NAVY = colors.HexColor("#0F254A")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#667085")
LINE = colors.HexColor("#C9D3DF")
WHITE = colors.white
SOFT_BG = colors.HexColor("#F7F9FC")

BLUE_SOFT = colors.HexColor("#EEF4FF")
BLUE_BORDER = colors.HexColor("#C8D8FF")
GREEN_SOFT = colors.HexColor("#EAF8EE")
GREEN_BORDER = colors.HexColor("#9DD9AE")
RED_SOFT = colors.HexColor("#FFF0EC")
RED_BORDER = colors.HexColor("#E26D5A")

TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=26,
    leading=30,
    textColor=NAVY,
)
SECTION = ParagraphStyle(
    "SECTION",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=18,
    textColor=NAVY,
)
BODY = ParagraphStyle(
    "BODY",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=TEXT,
)
SMALL = ParagraphStyle(
    "SMALL",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=10.5,
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
    fontSize=20,
    leading=24,
    textColor=NAVY,
)
