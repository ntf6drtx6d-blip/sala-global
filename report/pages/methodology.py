from reportlab.platypus import Paragraph, Spacer
from ..styles import TITLE, BODY

def build_methodology(data):
    story = []

    story.append(Paragraph("Methodology", TITLE))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Based on PVGIS (European Commission, JRC).", BODY))
    story.append(Paragraph("Simulation considers full-year solar conditions.", BODY))

    return story
