import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from report.data_builder import build_report_data


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR
ASSETS_DIR = BASE_DIR / "assets"

SALA_LOGO = ASSETS_DIR / "sala_logo.png"
JRC_LOGO = ASSETS_DIR / "jrc_logo.jpg"
TEMPLATE_NAME = "template.html"


def _file_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""

    suffix = path.suffix.lower()
    if suffix == ".png":
        mime = "image/png"
    elif suffix in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    else:
        mime = "application/octet-stream"

    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _optional_image_to_data_uri(path_str: Optional[str]) -> str:
    if not path_str:
        return ""
    path = Path(path_str)
    if not path.exists():
        return ""
    return _file_to_data_uri(path)


def _find_map_image() -> str:
    """
    Optional.
    If you later save a static map screenshot somewhere, put candidate paths here.
    """
    candidates = [
        Path("/mnt/data/current_report_render/page-1.png"),
        Path("/mnt/data/current_report_render/page-2.png"),
        Path("/mnt/data/study_map.png"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ""


def _build_html_context(
    loc,
    required_hours,
    results,
    overall,
    document_no="",
    revision_no=0,
    airport_label="",
    report_date="",
):
    data = build_report_data(
        loc=loc,
        required_hours=required_hours,
        results=results,
        overall=overall,
        document_no=document_no,
        revision_no=revision_no,
        airport_label=airport_label,
        report_date=report_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    accent = data.get("accent", "red")

    if accent == "green":
        conclusion_class = "pass"
    elif accent == "gold":
        conclusion_class = "warn"
    else:
        conclusion_class = ""

    worst_blackout_risk = str(data.get("worst_blackout_risk", ""))
    if worst_blackout_risk.startswith("0 "):
        risk_class = "pass"
    else:
        risk_class = ""

    context = {
        "report_id": data["report_id"],
        "report_date": data["date"],
        "airport_name": data["airport_name"],
        "coordinates": data["coordinates"],
        "overall_conclusion_title": data["overall_conclusion_title"],
        "overall_conclusion_text": data["overall_conclusion_text"],
        "required_operation": data["required_operation"],
        "worst_blackout_risk": data["worst_blackout_risk"],
        "worst_blackout_pct": data["worst_blackout_pct"],
        "interpretation": data["interpretation"],
        "recommendation": data["recommendation"],
        "methodology_note": data["methodology_note"],
        "conclusion_class": conclusion_class,
        "risk_class": risk_class,
        "sala_logo_src": _file_to_data_uri(SALA_LOGO),
        "jrc_logo_src": _file_to_data_uri(JRC_LOGO),
        "map_image_src": _optional_image_to_data_uri(_find_map_image()),
    }
    return context


def render_html(
    loc,
    required_hours,
    results,
    overall,
    document_no="",
    revision_no=0,
    airport_label="",
    report_date="",
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template(TEMPLATE_NAME)

    context = _build_html_context(
        loc=loc,
        required_hours=required_hours,
        results=results,
        overall=overall,
        document_no=document_no,
        revision_no=revision_no,
        airport_label=airport_label,
        report_date=report_date,
    )

    return template.render(**context)


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
    save_debug_html: bool = False,
):
    html_string = render_html(
        loc=loc,
        required_hours=required_hours,
        results=results,
        overall=overall,
        document_no=document_no,
        revision_no=revision_no,
        airport_label=airport_label,
        report_date=report_date,
    )

    if save_debug_html:
        debug_path = str(Path(out_path).with_suffix(".html"))
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html_string)

    HTML(string=html_string, base_url=str(BASE_DIR)).write_pdf(out_path)
