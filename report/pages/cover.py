
from reportlab.platypus import Paragraph, Spacer, PageBreak
from ..styles import TITLE, BODY

def build_cover(data):
    return [
        Paragraph("Solar Airfield Lighting Feasibility Study", TITLE),
        Spacer(1,20),
        Paragraph(f"Airport: {data['airport']}", BODY),
        Paragraph(f"Coordinates: {data['coords']}", BODY),
        Paragraph(f"Prepared for: {data['user']}", BODY),
        Paragraph(f"Date: {data['date']}", BODY),
        Paragraph(f"Document ID: {data['doc_id']}", BODY),
        PageBreak()
    ]
