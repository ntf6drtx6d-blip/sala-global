from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from ..styles import SECTION, BODY, SMALL, BOLD, LINE, WHITE

PAGE_WIDTH = 510


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _stack(items, width, style=None):
    t = Table([[x] for x in items], colWidths=[width])
    if style:
        t.setStyle(TableStyle(style))
    return t


def build_methodology(data):
    meta = data.get("pvgis_meta", {})

    story = []
    story.append(Paragraph("Methodology", SECTION))
    story.append(Spacer(1, 12))

    block1 = _stack(
        [
            Paragraph("Methodological basis", SMALL),
            Paragraph(
                "This report is prepared using PVGIS developed by the Joint Research Centre (JRC), European Commission.",
                BOLD,
            ),
            Spacer(1, 6),
            Paragraph(
                _safe(data.get("methodology_note")),
                BODY,
            ),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ],
    )
    story.append(block1)
    story.append(Spacer(1, 12))

    dataset = _safe(meta.get("dataset"))
    explanation = _safe(meta.get("explanation"))
    pvcalc_url = _safe(meta.get("pvcalc_url_example"))
    shs_url = _safe(meta.get("shs_url_example"))

    block2 = _stack(
        [
            Paragraph("PVGIS dataset and calculation logic", SMALL),
            Paragraph(f"Dataset: {dataset}", BOLD),
            Spacer(1, 4),
            Paragraph(explanation, BODY),
            Spacer(1, 8),
            Paragraph("Illustrative PVGIS request endpoints used in the study logic:", SMALL),
            Paragraph(f"PVcalc: {pvcalc_url}", BODY),
            Paragraph(f"SHScalc: {shs_url}", BODY),
        ],
        PAGE_WIDTH,
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 1, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ],
    )
    story.append(block2)
    return story
