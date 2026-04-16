from collections import OrderedDict
from datetime import datetime
import re
import unicodedata

from .data_builder import build_report_data
from .html_builder import render_report_html
from .pdf_renderer import render_pdf
from core.devices import DEVICES
from core.person import normalize_person_name
from core.time_utils import format_timestamp


def _coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _device_label(device_id):
    raw = str(device_id)
    if "||" in raw:
        _, variant = raw.split("||", 1)
        return variant
    try:
        did = int(raw)
        device = DEVICES.get(did)
        if device:
            return device.get("name") or device.get("code") or raw
    except Exception:
        pass
    return raw


def _device_list_text(selected_ids):
    ordered = OrderedDict()
    for item in selected_ids or []:
        label = _device_label(item)
        ordered[label] = ordered.get(label, 0) + 1
    if not ordered:
        return "—"
    return ", ".join(f"{count} × {label}" for label, count in ordered.items())


def sanitize_airport_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name or "Airport"))
    text = text.encode("ascii", "ignore").decode("ascii")
    parts = re.findall(r"[A-Za-z0-9]+", text)
    if not parts:
        return "Airport"
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def format_report_date(dt) -> str:
    if isinstance(dt, datetime):
        parsed = dt
    else:
        raw = str(dt or "").strip()
        parsed = None
        for candidate in (raw, raw.replace("Z", "+00:00")):
            if not candidate:
                continue
            try:
                parsed = datetime.fromisoformat(candidate)
                break
            except Exception:
                pass
        if parsed is None:
            match = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
            if match:
                parsed = datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                )
            else:
                parsed = datetime.now()
    return parsed.strftime("%d%b%Y")


def _normalize_icao(icao) -> str:
    raw = re.sub(r"[^A-Za-z0-9]", "", str(icao or "").upper())
    return raw if len(raw) == 4 else ""


def _extract_icao_from_text(*values) -> str:
    for value in values:
        text = str(value or "")
        for match in re.findall(r"\b[A-Z]{4}\b", text.upper()):
            if match not in {"SALA", "PVGI", "PAPI"}:
                return match
    return ""


def _language_prefix(language: str) -> str:
    code = str(language or "en").strip().lower()
    return {
        "en": "ENG",
        "es": "ESP",
        "fr": "FR",
    }.get(code, "ENG")


def build_pdf_filename(icao, airport_name, report_date, report_id, language="en") -> str:
    safe_airport = sanitize_airport_name(airport_name)
    safe_date = format_report_date(report_date)
    safe_id = str(report_id or "SALA-REPORT").strip() or "SALA-REPORT"
    safe_icao = _normalize_icao(icao) or _extract_icao_from_text(icao, airport_name)
    prefix = _language_prefix(language)
    if safe_icao:
        return f"{prefix}_SALA_FS_{safe_icao}_{safe_airport}_{safe_date}_{safe_id}.pdf"
    return f"{prefix}_SALA_FS_{safe_airport}_{safe_date}_{safe_id}.pdf"


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
            "icao": kwargs.get("airport_icao", "") or kwargs.get("icao", ""),
        }
    else:
        loc = dict(loc)
        if kwargs.get("airport_icao") and not (loc.get("icao") or loc.get("airport_icao")):
            loc["icao"] = kwargs.get("airport_icao", "")

    # --- compatibility with old positional extra args ---
    user_name = kwargs.get("author_name") or kwargs.get("user_name")
    if not user_name and args:
        user_name = args[-1]
    if not user_name:
        user_name = "User"
    user_name = normalize_person_name(user_name)
    user_organization = kwargs.get("author_organization") or kwargs.get("organization") or ""

    if out_path is None:
        out_path = "SALA_report.pdf"

    if required_hours is None:
        required_hours = 0

    if results is None:
        results = {}

    if overall is None:
        overall = "UNKNOWN"

    data = build_report_data(
        loc,
        required_hours,
        results,
        overall,
        user_name,
        user_organization,
        kwargs.get("language", "en"),
    )

    # override generated metadata if explicitly passed by caller
    if kwargs.get("created_at"):
        data["date"] = format_timestamp(kwargs["created_at"], include_seconds=False)

    if kwargs.get("airport_label"):
        data["airport_name"] = kwargs["airport_label"]

    if kwargs.get("author_name"):
        data["generated_by"] = normalize_person_name(kwargs["author_name"])
    if user_organization:
        data["generated_for_organization"] = user_organization

    data["operating_profile_mode"] = kwargs.get("operating_profile_mode", "Custom hours per day")
    data["selected_devices_text"] = _device_list_text(kwargs.get("selected_ids") or [])

    report_filename = build_pdf_filename(
        kwargs.get("airport_icao")
        or data.get("airport_icao")
        or loc.get("icao")
        or loc.get("airport_icao")
        or _extract_icao_from_text(
            kwargs.get("airport_label"),
            loc.get("label"),
        ),
        data.get("airport_name") or loc.get("label"),
        data.get("date"),
        data.get("report_id"),
        kwargs.get("language", "en"),
    )
    data["pdf_filename"] = report_filename
    if out_path in {"sala_standardized_feasibility_study.pdf", "SALA_report.pdf"}:
        out_path = report_filename

    html = render_report_html(data)
    render_pdf(html, out_path)
    return report_filename
