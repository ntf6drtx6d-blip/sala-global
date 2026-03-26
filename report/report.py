from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.summary import build_summary
from .assets.render_assets import generate_all_assets


def _extract_selected_devices(results):
    devices = []
    for device_id, result in results.items():
        label = (
            result.get("device_name")
            or result.get("label")
            or str(device_id)
        )
        devices.append(label)
    return devices


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
    # -------------------------
    # BUILD DATA
    # -------------------------
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

    # Selected devices
    data["selected_devices"] = _extract_selected_devices(results)

    # -------------------------
    # GENERATE ASSETS (MAP + CHARTS)
    # -------------------------
    try:
        map_path, monthly_chart, annual_chart = generate_all_assets(
            loc, results, required_hours
        )
    except Exception as e:
        print("ASSET GENERATION FAILED:", e)
        map_path, monthly_chart, annual_chart = None, None, None

    data["map_image_path"] = map_path
    data["monthly_chart_path"] = monthly_chart
    data["annual_profile_chart_path"] = annual_chart

    # -------------------------
    # PDF SETUP
    # -------------------------
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=36,
        bottomMargin=30,
    )

    # -------------------------
    # BUILD STORY
    # -------------------------
    story = []

    # Cover
    try:
        story += build_cover(data)
    except Exception as e:
        print("COVER FAILED:", e)

    # Summary
    try:
        story += build_summary(data)
    except Exception as e:
        print("SUMMARY FAILED:", e)

    # -------------------------
    # BUILD PDF
    # -------------------------
    doc.build(story)
