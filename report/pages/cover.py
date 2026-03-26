from reportlab.platypus import Paragraph, Spacer, PageBreak
from ..styles import TITLE, BODY, SMALL, BOLD


def build_cover(data):
    story = []

    story.append(Paragraph("SALA Standardized Feasibility Study", SMALL))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Solar AGL", TITLE))
    story.append(Spacer(1, 30))

    story.append(Paragraph(f"Project: {data['airport_name']}", BOLD))
    story.append(Paragraph(f"Document: {data['report_id']}", BODY))
    story.append(Paragraph(f"Date: {data['date']}", BODY))
    story.append(Paragraph(f"Prepared by: {data['prepared_by']}", BODY))

    story.append(Spacer(1, 30))

    story.append(Paragraph(data["methodology_note"], BODY))

    story.append(PageBreak())
    return story
