from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.summary import build_summary
from .assets.render_assets import generate_all_assets


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
        loc,
        required_hours,
        results,
        overall,
        document_no,
        revision_no,
        airport_label,
        report_date,
        reviewer,
    )

    map_path, monthly, annual = generate_all_assets(loc, results, required_hours)

    data["map_image_path"] = map_path
    data["monthly_chart_path"] = monthly
    data["annual_profile_chart_path"] = annual

    doc = SimpleDocTemplate(out_path, pagesize=A4)

    story = []
    story += build_cover(data)
    story += build_summary(data)

    doc.build(story)
