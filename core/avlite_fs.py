# core/avlite_fs.py
# Avlite feasibility engine
#
# Logic:
# 1) Use PVGIS MRcalc on each physical Avlite panel face (2-panel / 4-panel geometry)
# 2) Sum monthly panel generation
# 3) Derive a conservative equivalent single-plane panel
# 4) Run the SAME SHScalc off-grid approach used by the standard engine
#
# Compatible with:
# simulate_avlite_for_devices(loc, required_hrs, selected_ids, per_device_config=None, progress_callback=None)

import calendar
import time
from functools import lru_cache

import requests

from core.devices_avlite import AVLITE_FIXTURES, AVLITE_DEVICES
from pvgis_client import shs_monthly

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

PVGIS_BASES = [
    "https://re.jrc.ec.europa.eu/api/v5_3",
    "https://re.jrc.ec.europa.eu/api/v5_2",
]

HTTP_TIMEOUT = 45
USER_AGENT = "SALA-Avlite-FS/3.0"
DEFAULT_PR = 0.86
EQUIV_TILT_DEG = 33.0


def _days_in_month_non_leap(month_index_1_based: int) -> int:
    return calendar.monthrange(2025, month_index_1_based)[1]


def _south_facing_aspect(lat: float) -> float:
    # Same convention used in the standard engine.
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


def resolve_avlite_config(device_id, per_device_config=None):
    per_device_config = per_device_config or {}
    parsed_device_id, user_cfg = _parse_avlite_device_identifier(device_id, per_device_config)
    dspec = AVLITE_DEVICES[parsed_device_id]
    fixture = AVLITE_FIXTURES[dspec["fixture_key"]]

    display_name = user_cfg.get("display_label") or dspec["name"]

    return {
        "device_id": parsed_device_id,
        "device_code": dspec.get("code", ""),
        "device_name": display_name,
        "system_type": "avlite_fixture",
        "fixture_key": dspec["fixture_key"],
        "fixture_name": fixture["name"],
        "battery_type": fixture.get("battery_type", ""),
        "battery_voltage_v": float(fixture.get("battery_voltage_v", 0.0)),
        "battery_ah": float(fixture.get("battery_ah", 0.0)),
        "batt_nominal_wh": float(fixture["battery_wh_nominal"]),
        "cutoff_pct": float(fixture["cutoff_pct"]),
        "usable_battery_pct": 100.0 - float(fixture["cutoff_pct"]),
        "batt_usable_wh": float(fixture["battery_wh_nominal"]) * (1.0 - float(fixture["cutoff_pct"]) / 100.0),
        "power": float(fixture["power_w_100"]),
        "pv": float(fixture.get("pv_total_wp", sum(float(p["wp"]) for p in fixture["panels"]))),
        "panel_count": int(fixture.get("panel_count", len(fixture["panels"]))),
        "panel_geometry": fixture.get("panel_geometry", ""),
        "panels": fixture["panels"],
        "certified_intensity": fixture.get("certified_intensity", "100%"),
        "source_note": fixture.get("source_note", ""),
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
    """
    MRcalc JSON response:
        outputs["monthly"] = [
            {"year": 2005, "month": 1, "H(i)_m": ...},
            ...
        ]

    We aggregate all years by calendar month and return 12 monthly averages.
    """
    try:
        rows = data["outputs"]["monthly"]

        if not isinstance(rows, list) or not rows:
            raise ValueError("outputs.monthly is empty or not a list")

        by_month = {m: [] for m in range(1, 13)}

        for row in rows:
            if not isinstance(row, dict):
                continue

            month = row.get("month")
            val = row.get("H(i)_m")

            if month is None or val is None:
                continue

            month = int(month)
            val = float(val)

            if 1 <= month <= 12:
                by_month[month].append(val)

        result = []
        for m in range(1, 13):
            vals = by_month[m]
            if not vals:
                raise ValueError(f"No values for month {m}")
            result.append(sum(vals) / len(vals))

        if len(result) != 12:
            raise ValueError(f"Expected 12 monthly averages, got {len(result)}")

        return result

    except Exception as e:
        top_keys = list(data.keys()) if isinstance(data, dict) else str(type(data))
        raise RuntimeError(
            f"MRcalc JSON structure unexpected. Top-level keys: {top_keys}. Error: {e}"
        ) from e


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

                if not isinstance(monthly, list) or len(monthly) != 12:
                    raise RuntimeError(f"MRcalc returned invalid monthly values: {monthly}")

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
    """
    Convert MRcalc monthly irradiation into average daily electrical generation.
    Key fix:
      monthly irradiation must be divided by number of days in month.
    """
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


def _monthly_generation_wh_per_day(lat, lon, resolved_cfg, pr=DEFAULT_PR):
    per_panel = []
    total = [0.0] * 12

    for panel in resolved_cfg["panels"]:
        monthly_gen, meta = _panel_monthly_generation_wh_day(lat, lon, panel, pr=pr)
        per_panel.append(meta)
        for i in range(12):
            total[i] += float(monthly_gen[i])

    return total, per_panel


def _build_panel_summary(resolved_cfg):
    panels = resolved_cfg["panels"]
    total_wp = sum(float(p["wp"]) for p in panels)

    return {
        "panel_count": len(panels),
        "panel_list": [
            {
                "name": p["name"],
                "wp": float(p["wp"]),
                "tilt": float(p["tilt"]),
                "aspect": float(p["aspect"]),
            }
            for p in panels
        ],
        "total_nominal_wp": total_wp,
    }


def _derive_equivalent_single_plane(lat, lon, total_monthly_wh_day):
    """
    Derive one equivalent single-plane panel at fixed tilt 33° and south-facing aspect.
    Conservative rule:
      - fit monthly profile against reference plane
      - cap by worst winter-month ratio (Nov-Feb) to avoid optimistic equivalent PV
    """
    aspect = _south_facing_aspect(lat)
    ref_monthly_irr_sum, meta = _mrcalc_monthly_selected_plane(
        float(lat), float(lon), float(EQUIV_TILT_DEG), float(aspect)
    )

    ref_daily_basis = []
    for i, h_month in enumerate(ref_monthly_irr_sum, start=1):
        days = _days_in_month_non_leap(i)
        ref_daily_basis.append((float(h_month) / days) * DEFAULT_PR)

    # weighted least squares with more weight on winter months
    weights = [2.0 if i in (1, 2, 11, 12) else 1.0 for i in range(1, 13)]
    num = sum(weights[i] * float(total_monthly_wh_day[i]) * ref_daily_basis[i] for i in range(12))
    den = sum(weights[i] * (ref_daily_basis[i] ** 2) for i in range(12))
    fit_wp = max(0.0, num / den) if den > 0 else 0.0

    # conservative winter cap
    winter_idx = [0, 1, 10, 11]  # Jan, Feb, Nov, Dec
    ratios = []
    for i in winter_idx:
        b = ref_daily_basis[i]
        if b > 1e-9:
            ratios.append(float(total_monthly_wh_day[i]) / b)
    winter_cap_wp = min(ratios) if ratios else fit_wp

    equiv_wp = min(fit_wp, winter_cap_wp)

    return {
        "equivalent_wp": max(0.0, float(equiv_wp)),
        "equivalent_tilt_deg": float(EQUIV_TILT_DEG),
        "equivalent_aspect_deg": float(aspect),
        "fit_wp": float(fit_wp),
        "winter_cap_wp": float(winter_cap_wp),
        "reference_monthly_irr_kwh_m2_month": ref_monthly_irr_sum,
        "reference_daily_basis_wh_day_per_wp": ref_daily_basis,
        "api_meta": meta,
    }


def _max_wh_for_month_equivalent(lat, lon, pv_wp, batt_wh, tilt, aspect, cutoff_pct, month_index_zero_based):
    hi_cap = int(min(20000, max(3 * batt_wh, 8 * pv_wp * 24)))

    def fe_for(cons_wh_day):
        if cons_wh_day <= 0:
            return 0.0
        monthly = shs_monthly(
            lat, lon,
            pv_wp, batt_wh,
            float(cons_wh_day),
            tilt, aspect,
            cutoff_pct=cutoff_pct,
        )
        return float(monthly[month_index_zero_based].get("f_e", 0.0))

    lo, hi = 1, hi_cap
    best = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        fe = fe_for(mid)

        if fe <= 0.0:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return int(best)


def _get_empty_battery_stats_for_required_mode_equivalent(lat, lon, pv_wp, batt_wh, tilt, aspect, cutoff_pct, required_daily_wh):
    monthly = shs_monthly(
        lat, lon,
        pv_wp,
        batt_wh,
        required_daily_wh,
        tilt,
        aspect,
        cutoff_pct=cutoff_pct,
    )

    pct_by_month = []
    days_by_month = []

    total_days = 0
    weighted_pct_sum = 0.0

    for mi in range(12):
        f_e = float(monthly[mi].get("f_e", 0.0))
        dim = _days_in_month_non_leap(mi + 1)
        pct_by_month.append(f_e)
        days_by_month.append(round(dim * f_e / 100.0))

        weighted_pct_sum += f_e * dim
        total_days += dim

    overall_pct = weighted_pct_sum / total_days if total_days else 0.0
    return pct_by_month, days_by_month, overall_pct


def build_avlite_pvgis_meta(lat, lon, resolved_cfg, panel_summary, per_panel_monthly, total_monthly_wh_day, equivalent_plane):
    return {
        "dataset_note": (
            "Physical Avlite panel geometry is calculated with PVGIS MRcalc. "
            "Then an equivalent single-plane panel is derived and evaluated with PVGIS SHScalc "
            "using the same off-grid approach as the standard engine."
        ),
        "lat": float(lat),
        "lon": float(lon),
        "device": resolved_cfg["fixture_name"],
        "certified_intensity": resolved_cfg["certified_intensity"],
        "power_w_100": resolved_cfg["power"],
        "battery_type": resolved_cfg["battery_type"],
        "battery_nominal_wh": resolved_cfg["batt_nominal_wh"],
        "battery_usable_wh": resolved_cfg["batt_usable_wh"],
        "cutoff_pct": resolved_cfg["cutoff_pct"],
        "panel_count": panel_summary["panel_count"],
        "panel_geometry": resolved_cfg["panel_geometry"],
        "physical_panels": panel_summary["panel_list"],
        "total_nominal_wp": panel_summary["total_nominal_wp"],
        "panels": per_panel_monthly,
        "monthly_total_wh_day": total_monthly_wh_day,
        "equivalent_single_plane": equivalent_plane,
    }


def simulate_avlite_for_devices(
    loc,
    required_hrs,
    selected_ids,
    per_device_config=None,
    progress_callback=None,
):
    per_device_config = per_device_config or {}
    lat, lon = float(loc["lat"]), float(loc["lon"])
    results = {}

    total_steps = max(1, len(selected_ids) * 12)
    completed_steps = 0
    started_at = time.time()

    for did in selected_ids:
        resolved = resolve_avlite_config(did, per_device_config)
        panel_summary = _build_panel_summary(resolved)

        # 1) Real physical panel geometry → summed daily generation basis
        total_monthly_wh_day, per_panel_monthly = _monthly_generation_wh_per_day(
            lat=lat,
            lon=lon,
            resolved_cfg=resolved,
            pr=DEFAULT_PR,
        )

        # 2) Build conservative equivalent single-plane PV
        equivalent_plane = _derive_equivalent_single_plane(
            lat=lat,
            lon=lon,
            total_monthly_wh_day=total_monthly_wh_day,
        )

        eq_wp = equivalent_plane["equivalent_wp"]
        eq_tilt = equivalent_plane["equivalent_tilt_deg"]
        eq_aspect = equivalent_plane["equivalent_aspect_deg"]

        # 3) Run the SAME off-grid approach as the standard engine
        hours = []
        monthly_energy_wh = []

        for mi in range(12):
            best_wh = _max_wh_for_month_equivalent(
                lat=lat,
                lon=lon,
                pv_wp=eq_wp,
                batt_wh=resolved["batt_nominal_wh"],
                tilt=eq_tilt,
                aspect=eq_aspect,
                cutoff_pct=resolved["cutoff_pct"],
                month_index_zero_based=mi,
            )
            monthly_energy_wh.append(best_wh)
            hours.append(min(best_wh / max(resolved["power"], 0.05), 24.0))

            completed_steps += 1
            if progress_callback:
                elapsed = time.time() - started_at
                pct = completed_steps / total_steps
                eta = (elapsed / completed_steps) * (total_steps - completed_steps) if completed_steps else 0.0
                progress_callback(
                    completed_steps,
                    total_steps,
                    pct,
                    elapsed,
                    eta,
                    resolved["device_name"],
                    MONTHS[mi],
                )

        min_margin = min(h - float(required_hrs) for h in hours)
        status = "PASS" if all(h >= float(required_hrs) - 1e-6 for h in hours) else "FAIL"
        fail_months = [MONTHS[i] for i, h in enumerate(hours) if h + 1e-6 < float(required_hrs)]

        empty_battery_pct_by_month, empty_battery_days_by_month, overall_empty_battery_pct = \
            _get_empty_battery_stats_for_required_mode_equivalent(
                lat=lat,
                lon=lon,
                pv_wp=eq_wp,
                batt_wh=resolved["batt_nominal_wh"],
                tilt=eq_tilt,
                aspect=eq_aspect,
                cutoff_pct=resolved["cutoff_pct"],
                required_daily_wh=float(required_hrs) * max(float(resolved["power"]), 0.05),
            )

        pvgis_meta = build_avlite_pvgis_meta(
            lat=lat,
            lon=lon,
            resolved_cfg=resolved,
            panel_summary=panel_summary,
            per_panel_monthly=per_panel_monthly,
            total_monthly_wh_day=total_monthly_wh_day,
            equivalent_plane=equivalent_plane,
        )

        result_key = resolved["device_name"]
        results[result_key] = {
            "device_id": did,
            "device_code": resolved["device_code"],
            "name": resolved["device_name"],
            "system_type": "avlite_fixture",
            "engine": "AVLITE",
            "engine_key": resolved["fixture_key"],
            "pv": eq_wp,  # simulation PV is equivalent single-plane panel
            "pv_physical_nominal": panel_summary["total_nominal_wp"],
            "batt": resolved["batt_nominal_wh"],
            "batt_std": resolved["batt_nominal_wh"],
            "battery_mode": "Built-in",
            "tilt": eq_tilt,
            "azim": float(eq_aspect),
            "hours": hours,
            "status": status,
            "min_margin": min_margin,
            "fail_months": fail_months,
            "power": resolved["power"],
            "lamp_variant": None,
            "monthly_energy_wh": monthly_energy_wh,
            "empty_battery_pct_by_month": empty_battery_pct_by_month,
            "empty_battery_days_by_month": empty_battery_days_by_month,
            "overall_empty_battery_pct": overall_empty_battery_pct,
            "pvgis_meta": pvgis_meta,

            # extra transparency fields
            "panel_count": panel_summary["panel_count"],
            "panel_list": panel_summary["panel_list"],
            "total_nominal_wp": panel_summary["total_nominal_wp"],
            "equivalent_panel_wp": eq_wp,
            "equivalent_panel_tilt": eq_tilt,
            "equivalent_panel_aspect": eq_aspect,
            "certified_intensity": resolved["certified_intensity"],
            "source_note": resolved["source_note"],
        }

    worst_name, worst_gap = None, 1e9
    overall = "PASS"

    for name, r in results.items():
        gap = r["min_margin"]
        if gap < worst_gap:
            worst_gap, worst_name = gap, name
        if r["status"] == "FAIL":
            overall = "FAIL"

    return results, overall, worst_name
