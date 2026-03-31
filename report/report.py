from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.executive_summary import build_summary
from .pages.technical_results import build_technical
from .pages.device_details import build_device_details
from .pages.methodology import build_methodology


def make_pdf(out_path, loc, required_hours, results, overall, *args):
    user_name = args[-1] if args else "User"
    data = build_report_data(loc, required_hours, results, overall, user_name)

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=28,
        bottomMargin=24,
    )

    story = []
    story += build_cover(data)
    story += build_summary(data)
    story += build_technical(data)
    story += build_device_details(data)
    story += build_methodology(data)
    doc.build(story)
