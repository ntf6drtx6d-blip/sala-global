from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from ..styles import SECTION, BODY, SMALL, LINE

PAGE_WIDTH = 510

def _img(path, w, h):
    try:
        im = Image(path)
        im._restrictSize(w, h)
        return im
    except Exception:
        return Paragraph("Chart unavailable", BODY)

def build_technical_results(data):
    story = []
    story.append(Paragraph("2. Technical Results", SECTION))
    story.append(Spacer(1, 12))
    story.append(_img(data.get("annual_profile_chart_path"), 500, 320))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "The chart above shows guaranteed daily operating hours by month for the selected configuration(s), compared against the required operating profile.",
        BODY,
    ))
    story.append(Spacer(1, 260))
    footer = Table([[Paragraph("Prepared using PVGIS-based off-grid assessment methodology", SMALL),
                     Paragraph("Page 3", SMALL)]], colWidths=[420, 90])
    footer.setStyle(TableStyle([("LINEABOVE",(0,0),(-1,-1),0.7,LINE),("ALIGN",(1,0),(1,0),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),6)]))
    story.append(footer)
    story.append(PageBreak())
    return story
