from datetime import datetime
import math

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _short_name(result_key: str, r: dict) -> str:
    code = (r.get("device_code") or "").strip()
    engine = (r.get("engine") or "").strip()
    if code and engine and engine != "BUILT-IN":
        return f"{code} + {engine}"
    if code:
        return code
    if "—" in result_key:
        return result_key.split("—", 1)[0].strip()
    return result_key.strip()


def _annual_days(r: dict) -> int:
    if isinstance(r.get("empty_battery_days_by_month"), (list, tuple)):
        try:
            return int(round(sum(float(x) for x in r["empty_battery_days_by_month"])))
        except Exception:
            pass
    pct = float(r.get("overall_empty_battery_pct", 0) or 0)
    return int(round(365 * pct / 100.0))


def _classify(days: int) -> str:
    if days == 0:
        return "PASS"
    if days <= 3:
        return "NEAR THRESHOLD"
    return "FAIL"


def _overall_case(pass_count: int, near_count: int, fail_count: int, total: int) -> tuple[str, str, str]:
    if pass_count == total:
        return (
            "All evaluated devices support the required operating profile.",
            "The evaluated configurations remain free from battery depletion under the defined annual operating profile.",
            "PASS",
        )
    if fail_count == 0 and near_count > 0:
        return (
            "The system is close to full compliance.",
            "Most evaluated configurations support the required operating profile, but limited battery depletion remains in some cases.",
            "NEAR THRESHOLD",
        )
    if fail_count == 1 and pass_count >= 1:
        return (
            "Most devices support the required operating profile, but not all configurations are compliant.",
            "At least one evaluated configuration experiences battery depletion and may not sustain the required operating profile year-round.",
            "FAIL",
        )
    return (
        "The evaluated configurations do not support the required operating profile without battery depletion.",
        "Multiple configurations experience battery depletion during the year and may not sustain the required operating profile reliably.",
        "FAIL",
    )


def _device_interpretation(name: str, days: int, cls: str) -> str:
    if cls == "PASS":
        return f"{name} supports the required operating profile year-round without battery depletion."
    if cls == "NEAR THRESHOLD":
        return f"{name} is close to compliance, with limited battery depletion during the year."
    return f"{name} does not sustain the required operating profile under annual worst-case conditions."


def build_report_data(loc, required_hours, results, overall, user_name):
    now = datetime.now()
    airport_name = (loc.get("label") or "Study point").strip()
    coords = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

    devices = []
    pass_count = 0
    near_count = 0
    fail_count = 0
    max_blackout = 0

    for result_key, r in results.items():
        short = _short_name(result_key, r)
        annual_days = _annual_days(r)
        cls = _classify(annual_days)
        if cls == "PASS":
            pass_count += 1
        elif cls == "NEAR THRESHOLD":
            near_count += 1
        else:
            fail_count += 1

        max_blackout = max(max_blackout, annual_days)

        devices.append({
            "name": short,
            "result_key": result_key,
            "annual_blackout_days": annual_days,
            "result_class": cls,
            "result_label": cls,
            "monthly_blackout_days": list(r.get("empty_battery_days_by_month") or [0] * 12),
            "monthly_operating_hours": list(r.get("hours") or [0] * 12),
            "interpretation_text": _device_interpretation(short, annual_days, cls),
            "dataset": (r.get("pvgis_meta") or {}).get("dataset", "PVGIS-SARAH2 (fallback: PVGIS-ERA5)"),
        })

    devices.sort(key=lambda x: ({"FAIL": 0, "NEAR THRESHOLD": 1, "PASS": 2}[x["result_class"]], -x["annual_blackout_days"], x["name"]))

    total = len(devices)
    title, text, overall_label = _overall_case(pass_count, near_count, fail_count, total)

    cover_verdict = overall_label if overall_label != "NEAR THRESHOLD" else "NEAR THRESHOLD"

    return {
        "airport_name": airport_name,
        "coordinates": coords,
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "report_id": f"SALA-{now.strftime('%Y%m%d%H%M%S')}",
        "prepared_for": user_name,
        "required_operation": f"{float(required_hours):.1f} hrs/day",
        "required_hours": float(required_hours),
        "devices": devices,
        "devices_total": total,
        "devices_pass_count": pass_count,
        "devices_near_count": near_count,
        "devices_fail_count": fail_count,
        "max_blackout_days": max_blackout,
        "show_blackout_chart": max_blackout > 0,
        "overall_result_title": title,
        "overall_result_text": text,
        "overall_result_label": overall_label,
        "cover_verdict": cover_verdict,
        "cover_statement": text,
        "methodology_note": "Assessment based on PVGIS methodology developed by the Joint Research Centre (JRC), European Commission.",
        "pvgis_dataset": devices[0]["dataset"] if devices else "PVGIS-SARAH2 (fallback: PVGIS-ERA5)",
        "country": loc.get("country", ""),
        "lat": float(loc.get("lat", 0)),
        "lon": float(loc.get("lon", 0)),
        "footer_note": "Prepared using SALA standardized off-grid feasibility methodology based on PVGIS.",
    }
