from reportlab.platypus import Paragraph, Spacer, PageBreak
from ..styles import TITLE, BODY

def build_technical(data):
    story = []

    story.append(Paragraph("Technical Results", TITLE))
    story.append(Spacer(1, 12))

    if data["max_blackout"] > 0:
        story.append(Paragraph("Blackout chart should be here", BODY))
        story.append(Spacer(1, 20))

    story.append(Paragraph("Annual operating profile chart should be here", BODY))

    story.append(PageBreak())
    return story
