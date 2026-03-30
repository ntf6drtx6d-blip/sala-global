
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.executive_summary import build_summary
from .pages.technical_results import build_technical
from .pages.methodology import build_methodology

# KEEP OLD SIGNATURE (compat with ui/cockpit.py)
def make_pdf(out_path, loc, required_hours, results, overall, *args):
    user_name = args[-1] if args else "User"

    data = build_report_data(loc, required_hours, results, overall, user_name)

    doc = SimpleDocTemplate(out_path, pagesize=A4,
        leftMargin=40, rightMargin=40, topMargin=30, bottomMargin=30)

    story = []
    story += build_cover(data)
    story += build_summary(data)
    story += build_technical(data)
    story += build_methodology(data)

    doc.build(story)
