from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from .data_builder import build_report_data
from .pages.cover import build_cover
from .pages.executive_summary import build_summary
from .pages.technical_results import build_technical
from .pages.device_details import build_device_details
from .pages.methodology import build_methodology


def _coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None


def make_pdf(
    out_path=None,
    loc=None,
    required_hours=None,
    results=None,
    overall=None,
    *args,
    **kwargs,
):
    """
    Backward- and forward-compatible PDF generator.

    Supports both call styles:

    Old style:
        make_pdf(out_path, loc, required_hours, results, overall, user_name)

    New style:
        make_pdf(
            results=results,
            overall=overall,
            airport_label="...",
            created_at="...",
            author_name="...",
            required_hours=12,
            output_path="/tmp/xxx.pdf",
            lat=...,
            lon=...,
            selected_ids=[...],
        )

    Unknown extra kwargs are ignored on purpose, so cockpit/report interface
    changes do not crash PDF generation.
    """

    # --- compatibility with new keyword-based call style ---
    out_path = _coalesce(out_path, kwargs.get("output_path"), kwargs.get("out_path"))
    results = _coalesce(results, kwargs.get("results"))
    overall = _coalesce(overall, kwargs.get("overall"))
    required_hours = _coalesce(required_hours, kwargs.get("required_hours"))

    if loc is None:
        lat = kwargs.get("lat", 0)
        lon = kwargs.get("lon", 0)
        airport_label = kwargs.get("airport_label", "Study point")
        country = kwargs.get("country", "")
        loc = {
            "label": airport_label,
            "lat": lat,
            "lon": lon,
            "country": country,
        }

    # --- compatibility with old positional extra args ---
    user_name = kwargs.get("author_name") or kwargs.get("user_name")
    if not user_name and args:
        user_name = args[-1]
    if not user_name:
        user_name = "User"

    if out_path is None:
        out_path = "sala_standardized_feasibility_study.pdf"

    if required_hours is None:
        required_hours = 0

    if results is None:
        results = {}

    if overall is None:
        overall = "UNKNOWN"

    data = build_report_data(loc, required_hours, results, overall, user_name)

    # override generated metadata if explicitly passed by caller
    if kwargs.get("created_at"):
        data["date"] = kwargs["created_at"]

    if kwargs.get("airport_label"):
        data["airport_name"] = kwargs["airport_label"]

    if kwargs.get("author_name"):
        data["prepared_for"] = kwargs["author_name"]

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
