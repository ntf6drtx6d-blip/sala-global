from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

styles = getSampleStyleSheet()

# SALA-led palette
PRIMARY = colors.HexColor("#1F4FBF")
PRIMARY_DARK = colors.HexColor("#12355B")
PRIMARY_SOFT = colors.HexColor("#EEF4FF")

GREEN = colors.HexColor("#169B62")
GREEN_SOFT = colors.HexColor("#ECFDF3")

AMBER = colors.HexColor("#D97706")
AMBER_SOFT = colors.HexColor("#FFF7E6")

RED = colors.HexColor("#C73E1D")
RED_SOFT = colors.HexColor("#FFF1EE")

TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#667085")
BORDER = colors.HexColor("#D7DEE8")
LIGHT_BG = colors.HexColor("#F8FAFC")
WHITE = colors.white

PAGE_WIDTH = 515

SPACE_1 = 6
SPACE_2 = 10
SPACE_3 = 16
SPACE_4 = 24

TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=22,
    leading=26,
    textColor=TEXT,
    spaceAfter=0,
)

SECTION = ParagraphStyle(
    "SECTION",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=18,
    textColor=TEXT,
    spaceAfter=0,
)

CARD_TITLE = ParagraphStyle(
    "CARD_TITLE",
    parent=styles["Heading3"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=TEXT,
    spaceAfter=0,
)

KPI_VALUE = ParagraphStyle(
    "KPI_VALUE",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=21,
    textColor=TEXT,
    spaceAfter=0,
)

BODY = ParagraphStyle(
    "BODY",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=13,
    textColor=TEXT,
    spaceAfter=0,
)

BODY_BOLD = ParagraphStyle(
    "BODY_BOLD",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=9.5,
    leading=13,
    textColor=TEXT,
    spaceAfter=0,
)

SMALL = ParagraphStyle(
    "SMALL",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10.5,
    textColor=MUTED,
    spaceAfter=0,
)

SMALL_BOLD = ParagraphStyle(
    "SMALL_BOLD",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10.5,
    textColor=MUTED,
    spaceAfter=0,
)

TABLE_HEADER = ParagraphStyle(
    "TABLE_HEADER",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8.5,
    leading=10.5,
    textColor=TEXT,
    spaceAfter=0,
)

FOOTER = ParagraphStyle(
    "FOOTER",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9,
    textColor=MUTED,
    spaceAfter=0,
)
