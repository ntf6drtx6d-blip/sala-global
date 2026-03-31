from reportlab.platypus import Paragraph, Spacer, PageBreak
from ..styles import TITLE, BODY

def build_cover(data):
    story = []
    story.append(Paragraph("Solar Airfield Lighting Feasibility Study", TITLE))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"Airport: {data['airport']}", BODY))
    story.append(Paragraph(f"Coordinates: {data['coords']}", BODY))
    story.append(Paragraph(f"Prepared for: {data['user']}", BODY))
    story.append(Paragraph(f"Date: {data['date']}", BODY))
    story.append(Paragraph(f"Document ID: {data['doc_id']}", BODY))

    story.append(PageBreak())
    return story
