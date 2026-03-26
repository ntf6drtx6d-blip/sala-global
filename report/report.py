from reportlab.platypus import SimpleDocTemplate

from .data_builder import build_report_data
from .assets.render_assets import generate_all_assets
from .pages.cover import build_cover
from .pages.executive_summary import build_executive_summary
from .pages.technical_results import build_technical_results
from .pages.methodology import build_methodology

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
        prepared_by=reviewer,
    )

    map_path, monthly, annual = generate_all_assets(loc, results, required_hours)
    data["map_image_path"] = map_path
    data["monthly_chart_path"] = monthly
    data["annual_profile_chart_path"] = annual

    doc = SimpleDocTemplate(out_path, leftMargin=42, rightMargin=42, topMargin=28, bottomMargin=24)

    story = []
    story += build_cover(data)
    story += build_executive_summary(data)
    story += build_technical_results(data)
    story += build_methodology(data)

    doc.build(story)
