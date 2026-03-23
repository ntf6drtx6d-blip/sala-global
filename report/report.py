from reportlab.pdfgen import canvas

from .theme import PAGE_W, PAGE_H
from .data_builder import build_report_data
from .page_cover import draw_cover_page
from .page_summary import draw_summary_page


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

    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    draw_cover_page(c, data)
    c.showPage()
    draw_summary_page(c, data)
    c.showPage()
    c.save()
