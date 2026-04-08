
# core/avlite_fs.py
# Avlite equivalent-panel translator.
#
# Purpose:
# 1) Calculate real physical 2-panel / 4-panel geometry using PVGIS MRcalc
# 2) Derive one equivalent single panel per lamp
# 3) Return a resolved config compatible with the standard simulator path
#
# Method used for equivalent panel:
# - Calculate monthly equivalent Wp values against a 1 Wp reference panel @ 33°
# - Keep transparency values:
#     * annual average equivalent
#     * worst-month equivalent
#     * third-worst equivalent
# - Use third-worst equivalent as the simulation value

import calendar
from functools import lru_cache
import requests

from core.devices_avlite import AVLITE_FIXTURES, AVLITE_DEVICES

PVGIS_BASES = [
    "https://re.jrc.ec.europa.eu/api/v5_3",
    "https://re.jrc.ec.europa.eu/api/v5_2",
]

HTTP_TIMEOUT = 45
USER_AGENT = "SALA-Avlite-EQ/1.1"
DEFAULT_PR = 0.86
EQUIV_TILT_DEG = 33.0


def _days_in_month_non_leap(month_index_1_based: int) -> int:
    return calendar.monthrange(2025, month_index_1_based)[1]


def _south_facing_aspect(lat: float) -> float:
    return 0.0 if float(lat) >= 0 else 180.0


def _parse_avlite_device_identifier(device_identifier, per_device_config=None):
    per_device_config = per_device_config or {}
    user_cfg = per_device_config.get(device_identifier) or per_device_config.get(str(device_identifier), {})
    raw_id = user_cfg.get("device_id", device_identifier)
    try:
        device_id = int(raw_id)
    except Exception:
        device_id = int(device_identifier)
    return device_id, user_cfg


def resolve_avlite_fixture(device_id, per_device_config=None):
    per_device_config = per_device_config or {}
    parsed_device_id, user_cfg = _parse_avlite_device_identifier(device_id, per_device_config)

    dspec = AVLITE_DEVICES[parsed_device_id]
    fixture = AVLITE_FIXTURES[dspec["fixture_key"]]
    display_name = user_cfg.get("display_label") or dspec["name"]

    return {
        "device_id": parsed_device_id,
        "device_code": dspec.get("code", ""),
        "device_name": display_name,
        "fixture_key": dspec["fixture_key"],
        "fixture_name": fixture["name"],
        "battery_type": fixture.get("battery_type", ""),
        "batt_nominal_wh": float(fixture["battery_wh_nominal"]),
        "power": float(fixture["power_w_100"]),
        "panel_count": int(fixture.get("panel_count", len(fixture["panels"]))),
        "panel_geometry": fixture.get("panel_geometry", ""),
        "panels": fixture["panels"],
        "pv_total_wp": float(fixture.get("pv_total_wp", sum(float(p["wp"]) for p in fixture["panels"]))),
        "certified_intensity": fixture.get("certified_intensity", "100%"),
        "source_note": fixture.get("source_note", ""),
        "cutoff_pct": float(fixture.get("cutoff_pct", 30)),
    }


def _extract_error_text(resp) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            for key in ["message", "error", "msg", "detail"]:
                if key in data:
                    return str(data[key])
            return str(data)[:1200]
    except Exception:
        pass
    return (resp.text or "")[:1200]


def _sanitize_geometry(angle_deg: float, aspect_deg: float):
    angle = float(angle_deg)
    aspect = float(aspect_deg)

    if angle >= 90.0:
        angle = 89.999
    if angle <= 0.0:
        angle = 0.001

    if aspect >= 180.0:
        aspect = 179.999
    if aspect <= -180.0:
        aspect = -179.999

    return angle, aspect


def _extract_monthly_from_mrcalc_json(data):
    rows = data["outputs"]["monthly"]
    by_month = {m: [] for m in range(1, 13)}

    for row in rows:
        month = int(row["month"])
        val = float(row["H(i)_m"])
        if 1 <= month <= 12:
            by_month[month].append(val)

    out = []
    for m in range(1, 13):
        vals = by_month[m]
        if not vals:
            raise RuntimeError(f"No MRcalc values for month {m}")
        out.append(sum(vals) / len(vals))
    return out


@lru_cache(maxsize=2048)
def _mrcalc_monthly_selected_plane(lat, lon, angle_deg, aspect_deg):
    angle_deg, aspect_deg = _sanitize_geometry(angle_deg, aspect_deg)
    last_err = None
    db_options = [None, "PVGIS-ERA5"]

    for base in PVGIS_BASES:
        for db in db_options:
            params = {
                "lat": float(lat),
                "lon": float(lon),
                "selectrad": 1,
                "angle": float(angle_deg),
                "aspect": float(aspect_deg),
                "outputformat": "json",
                "browser": 0,
            }
            if db:
                params["raddatabase"] = db

            resp = None
            try:
                resp = requests.get(
                    f"{base}/MRcalc",
                    params=params,
                    timeout=HTTP_TIMEOUT,
                    headers={"User-Agent": USER_AGENT},
                )
                resp.raise_for_status()
                data = resp.json()
                monthly = _extract_monthly_from_mrcalc_json(data)
                return monthly, {
                    "base": base,
                    "raddatabase": db or "default",
                    "angle": float(angle_deg),
                    "aspect": float(aspect_deg),
                }
            except Exception as e:
                if resp is not None:
                    last_err = f"{type(e).__name__}: {e}; response={_extract_error_text(resp)}"
                else:
                    last_err = f"{type(e).__name__}: {e}"
                continue

    raise RuntimeError(
        f"PVGIS MRcalc failed for all endpoints. "
        f"lat={lat}, lon={lon}, angle={angle_deg}, aspect={aspect_deg}. "
        f"Last error: {last_err}"
    )


def _panel_monthly_generation_wh_day(lat, lon, panel, pr=DEFAULT_PR):
    monthly_irr_sum, meta = _mrcalc_monthly_selected_plane(
        float(lat), float(lon), float(panel["tilt"]), float(panel["aspect"])
    )

    wp = float(panel["wp"])
    monthly_irr_day = []
    monthly_gen_wh_day = []

    for i, h_month in enumerate(monthly_irr_sum, start=1):
        days = _days_in_month_non_leap(i)
        h_day = float(h_month) / days
        monthly_irr_day.append(h_day)
        monthly_gen_wh_day.append(h_day * wp * float(pr))

    return monthly_gen_wh_day, {
        "name": panel["name"],
        "wp": wp,
        "tilt": float(panel["tilt"]),
        "aspect": float(panel["aspect"]),
        "monthly_irr_kwh_m2_month": monthly_irr_sum,
        "monthly_irr_kwh_m2_day": monthly_irr_day,
        "monthly_gen_wh_day": monthly_gen_wh_day,
        "api_meta": meta,
    }


def _physical_generation_wh_day(lat, lon, fixture_cfg):
    per_panel = []
    total = [0.0] * 12

    for panel in fixture_cfg["panels"]:
        monthly_gen, meta = _panel_monthly_generation_wh_day(lat, lon, panel)
        per_panel.append(meta)
        for i in range(12):
            total[i] += float(monthly_gen[i])

    return total, per_panel


def _derive_equivalent_single_plane(lat, lon, total_monthly_wh_day):
    aspect = _south_facing_aspect(lat)

    ref_monthly_irr_sum, meta = _mrcalc_monthly_selected_plane(
        float(lat),
        float(lon),
        float(EQUIV_TILT_DEG),
        float(aspect),
    )

    ref_daily_basis = []
    for i, h_month in enumerate(ref_monthly_irr_sum, start=1):
        days = _days_in_month_non_leap(i)
        h_day = float(h_month) / days
        ref_daily_basis.append(h_day * DEFAULT_PR)

    monthly_equivalent_wp = []
    for i in range(12):
        basis = ref_daily_basis[i]
        if basis <= 1e-9:
            monthly_equivalent_wp.append(0.0)
        else:
            monthly_equivalent_wp.append(float(total_monthly_wh_day[i]) / basis)

    annual_average_wp = sum(monthly_equivalent_wp) / 12.0

    sorted_wp = sorted(monthly_equivalent_wp)
    worst_month_wp = sorted_wp[0]
    third_worst_wp = sorted_wp[2] if len(sorted_wp) >= 3 else sorted_wp[0]

    equivalent_wp_used = max(0.0, third_worst_wp)

    return {
        "equivalent_wp": float(equivalent_wp_used),
        "equivalent_tilt_deg": float(EQUIV_TILT_DEG),
        "equivalent_aspect_deg": float(aspect),

        "annual_average_wp": float(annual_average_wp),
        "worst_month_wp": float(worst_month_wp),
        "third_worst_wp": float(third_worst_wp),
        "monthly_equivalent_wp": [float(x) for x in monthly_equivalent_wp],
        "reference_monthly_irr_kwh_m2_month": [float(x) for x in ref_monthly_irr_sum],
        "reference_daily_basis_wh_day_per_wp": [float(x) for x in ref_daily_basis],
        "api_meta": meta,
    }


def resolve_avlite_equivalent_config(device_id, loc, per_device_config=None):
    fixture_cfg = resolve_avlite_fixture(device_id, per_device_config)
    lat = float(loc["lat"])
    lon = float(loc["lon"])

    total_monthly_wh_day, per_panel_monthly = _physical_generation_wh_day(lat, lon, fixture_cfg)
    equiv = _derive_equivalent_single_plane(lat, lon, total_monthly_wh_day)

    total_nominal_wp = float(fixture_cfg["pv_total_wp"])
    equivalent_wp = float(equiv["equivalent_wp"])
    annual_average_wp = float(equiv["annual_average_wp"])
    worst_month_wp = float(equiv["worst_month_wp"])
    third_worst_wp = float(equiv["third_worst_wp"])

    equivalent_pct = (equivalent_wp / total_nominal_wp * 100.0) if total_nominal_wp > 0 else 0.0
    annual_average_pct = (annual_average_wp / total_nominal_wp * 100.0) if total_nominal_wp > 0 else 0.0
    worst_month_pct = (worst_month_wp / total_nominal_wp * 100.0) if total_nominal_wp > 0 else 0.0
    third_worst_pct = (third_worst_wp / total_nominal_wp * 100.0) if total_nominal_wp > 0 else 0.0

    avlite_meta = {
        "dataset_note": (
            "Avlite physical panel geometry was calculated with PVGIS MRcalc. "
            "A single equivalent panel was then derived and sent through the same off-grid simulator path as S4GA."
        ),
        "physical_panel_geometry": fixture_cfg["panel_geometry"],
        "physical_panels": per_panel_monthly,
        "panel_count": fixture_cfg["panel_count"],
        "total_nominal_wp": total_nominal_wp,
        "equivalent_single_plane": equiv,
    }

    resolved = {
        "device_id": fixture_cfg["device_id"],
        "device_code": fixture_cfg["device_code"],
        "device_name": fixture_cfg["device_name"],
        "lamp_variant": None,
        "system_type": "avlite_fixture",
        "engine_key": fixture_cfg["fixture_key"],
        "engine_name": "BUILT-IN",
        "power": fixture_cfg["power"],
        "pv": equivalent_wp,
        "batt_std": fixture_cfg["batt_nominal_wh"],
        "batt": fixture_cfg["batt_nominal_wh"],
        "battery_mode": "Built-in",
        "fixed": True,
        "tilt_options": [float(EQUIV_TILT_DEG)],
        "tilt": float(EQUIV_TILT_DEG),
        "equivalent_aspect": float(equiv["equivalent_aspect_deg"]),
        "avlite_meta": avlite_meta,
        "battery_type": fixture_cfg["battery_type"],
        "cutoff_pct": fixture_cfg["cutoff_pct"],

        "panel_count": fixture_cfg["panel_count"],
        "panel_list": [{
            "name": p["name"],
            "wp": float(p["wp"]),
            "tilt": float(p["tilt"]),
            "aspect": float(p["aspect"]),
        } for p in fixture_cfg["panels"]],
        "total_nominal_wp": total_nominal_wp,

        "equivalent_panel_wp": equivalent_wp,
        "equivalent_panel_tilt": float(EQUIV_TILT_DEG),
        "equivalent_panel_aspect": float(equiv["equivalent_aspect_deg"]),
        "equivalent_pct_of_physical_nominal": equivalent_pct,

        "annual_average_equivalent_wp": annual_average_wp,
        "annual_average_equivalent_pct": annual_average_pct,
        "worst_month_equivalent_wp": worst_month_wp,
        "worst_month_equivalent_pct": worst_month_pct,
        "third_worst_equivalent_wp": third_worst_wp,
        "third_worst_equivalent_pct": third_worst_pct,
        "monthly_equivalent_wp": equiv["monthly_equivalent_wp"],

        "physical_panel_geometry": fixture_cfg["panel_geometry"],
        "certified_intensity": fixture_cfg["certified_intensity"],
        "source_note": fixture_cfg["source_note"],
    }
    return resolved
