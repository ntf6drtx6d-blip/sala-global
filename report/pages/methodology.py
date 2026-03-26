from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from ..styles import SECTION, BODY, SMALL, BOLD, LINE, BLUE_SOFT

PAGE_WIDTH = 510

def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default

def build_methodology(data):
    meta = data.get("pvgis_meta", {})
    story = []
    story.append(Paragraph("3. Methodology", SECTION))
    story.append(Spacer(1, 12))

    rows = [
        [Paragraph("<b>Core method</b>", SMALL), Paragraph("PVGIS off-grid autonomy assessment", BODY)],
        [Paragraph("<b>Decision rule</b>", SMALL), Paragraph("Weakest month compared with required daily operating profile", BODY)],
        [Paragraph("<b>Dataset</b>", SMALL), Paragraph(_safe(meta.get("dataset"), "PVGIS SARAH / ERA5 where applicable"), BODY)],
        [Paragraph("<b>Location basis</b>", SMALL), Paragraph(_safe(data.get("coordinates")), BODY)],
        [Paragraph("<b>Requirement</b>", SMALL), Paragraph(_safe(data.get("required_operation")), BODY)],
        [Paragraph("<b>Interpretation</b>", SMALL), Paragraph("If the weakest month stays below the required operating profile, the configuration is not technically feasible for the selected use case.", BODY)],
    ]
    tbl = Table(rows, colWidths=[120, 390])
    tbl.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.7,LINE),
        ("BACKGROUND",(0,0),(0,-1),BLUE_SOFT),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(tbl)
    return story
