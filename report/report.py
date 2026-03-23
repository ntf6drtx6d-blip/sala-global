from reportlab.lib.pagesizes import A4
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.summary import build_summary


def _add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColorRGB(0.4, 0.45, 0.52)
    report_id = getattr(doc, "report_id", "")
    revision = getattr(doc, "revision", "")
    canvas.drawString(doc.leftMargin, 20, f"{report_id} | {revision}")
    canvas.drawRightString(A4[0] - doc.rightMargin, 20, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def make_pdf(
    out_path,
    loc,
    required_hours,
    results,
    overall,
    project_name="",
    revision_no=0,
    document_no="",
    airport_label="",
    report_date="",
    reviewer=None,
):
    data = build_report_data(
        loc=loc,
        required_hours=required_hours,
        results=results,
        overall=overall,
        document_no=document_no,
        revision_no=revision_no,
        airport_label=airport_label,
        report_date=report_date,
    )

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=40,
        bottomMargin=36,
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin + 8,
        doc.width,
        doc.height - 8,
        id="normal",
    )

    template = PageTemplate(id="main", frames=[frame], onPage=_add_footer)
    doc.addPageTemplates([template])

    doc.report_id = data["report_id"]
    doc.revision = data["revision"]

    story = []
    story += build_cover(data)
    story += build_summary(data)

    doc.build(story)
