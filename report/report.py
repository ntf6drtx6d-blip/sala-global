from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.summary import build_summary


def _extract_selected_devices(results):
    devices = []
    for device_id, result in results.items():
        label = result.get("device_name") or result.get("label") or str(device_id)
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

    data["selected_devices"] = _extract_selected_devices(results)

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=36,
        bottomMargin=30,
    )

    story = []
    story += build_cover(data)
    story += build_summary(data)

    doc.build(story)
