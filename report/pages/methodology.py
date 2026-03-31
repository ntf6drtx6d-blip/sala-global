
from reportlab.platypus import Paragraph, Spacer
from ..styles import TITLE, BODY

def build_methodology(data):
    return [
        Paragraph("Methodology", TITLE),
        Spacer(1,12),
        Paragraph("Based on PVGIS (European Commission, JRC).", BODY),
        Paragraph("Full-year solar simulation applied.", BODY)
    ]
