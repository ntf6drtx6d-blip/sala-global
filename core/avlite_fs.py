# core/avlite_fs.py
# Avlite equivalent-panel translator.
#
# Corrected method:
# 1) Calculate annual PV electricity output for the relevant physical / proxy geometry
#    using PVGIS Grid-Connected PV (PVcalc) yearly production.
# 2) Compare against a properly oriented single reference panel at 33° with the same
#    total nominal Wp.
# 3) Derive one annual site-specific geometry coefficient.
# 4) Apply this coefficient to the REAL nominal PV of the lamp.
# 5) Return a resolved config compatible with the standard simulator path.
#
# Important implementation choices:
# - Annual ratio only (no worst-month / third-worst logic)
# - AV70 uses fixed East-West proxy geometry for coefficient calculation:
#       7W East + 7W West vs single 14W @ 33°
#   then applies that coefficient to the REAL AV70 nominal PV = 1.4 W
# - AV426 uses its actual configured 4-sided fixture geometry from devices_avlite
#   (supports both 4x5W and 4x7W variants automatically if present in fixture data)
# - Coefficient step uses PVGIS Grid-Connected yearly electricity production (E_y),
#   not MRcalc irradiation proxy.

from functools import lru_cache
import requests

from core.devices_avlite import AVLITE_FIXTURES, AVLITE_DEVICES

PVGIS_BASES = [
    "https://re.jrc.ec.europa.eu/api/v5_3",
    "https://re.jrc.ec.europa.eu/api/v5_2",
]

HTTP_TIMEOUT = 45
USER_AGENT = "SALA-Avlite-EQ/1.3"
REFERENCE_TILT_DEG = 33.0
PHYSICAL_TILT_DEG_AV70 = 50.0
GRID_PV_LOSS_PCT = 14.0
GRID_PV_TECH = "crystSi"
GRID_MOUNTING = "free"

# PVGIS convention for fixed planes: 0=south, 90=west, -90=east.
ASPECT_NORTH = 180.0
ASPECT_EAST = -90.0
ASPECT_SOUTH = 0.0
ASPECT_WEST = 90.0


def _equator_facing_aspect(lat: float) -> float:
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

    if angle < 0.0:
        angle = 0.0
    if angle > 90.0:
        angle = 90.0

    # PVGIS examples/documentation use 180 for north, but guard exact overflow.
    if aspect > 180.0:
        aspect = 180.0
    if aspect < -180.0:
        aspect = -180.0

    return angle, aspect



def _extract_yearly_pv_energy_kwh(data: dict) -> float:
    # Official examples show outputs.totals.fixed.E_y for PVcalc JSON.
    outputs = data.get("outputs") or {}
    totals = outputs.get("totals") or {}
    fixed = totals.get("fixed") or {}
    e_y = fixed.get("E_y")
    if e_y is None:
        raise RuntimeError(f"PVGIS PVcalc JSON missing outputs.totals.fixed.E_y: {list((outputs or {}).keys())}")
    return float(e_y)


@lru_cache(maxsize=4096)
def _pvcalc_yearly_kwh(
    lat: float,
    lon: float,
    peakpower_kw: float,
    tilt_deg: float,
    aspect_deg: float,
    pvtechchoice: str = GRID_PV_TECH,
    loss_pct: float = GRID_PV_LOSS_PCT,
    mountingplace: str = GRID_MOUNTING,
    raddatabase: str | None = None,
):
    """
    Returns PVGIS Grid-Connected yearly PV electricity production E_y in kWh/year.
    peakpower_kw must be in kW as required by PVcalc.
    """
    angle_deg, aspect_deg = _sanitize_geometry(tilt_deg, aspect_deg)
    last_err = None

    # First try with default DB (closest to UI behavior). If it fails, try explicit DBs.
    db_options = [raddatabase] if raddatabase else [None, "PVGIS-SARAH3", "PVGIS-NSRDB", "PVGIS-ERA5"]

    for base in PVGIS_BASES:
        for db in db_options:
            params = {
                "lat": float(lat),
                "lon": float(lon),
                "peakpower": float(peakpower_kw),
                "pvtechchoice": pvtechchoice,
                "mountingplace": mountingplace,
                "loss": float(loss_pct),
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
                    f"{base}/PVcalc",
                    params=params,
                    timeout=HTTP_TIMEOUT,
                    headers={"User-Agent": USER_AGENT},
                )
                resp.raise_for_status()
                data = resp.json()
                e_y_kwh = _extract_yearly_pv_energy_kwh(data)
                inputs = data.get("inputs") or {}
                meta = {
                    "base": base,
                    "raddatabase": inputs.get("meteo_data", {}).get("radiation_db") or db or "default",
                    "peakpower_kw": float(peakpower_kw),
                    "angle": float(angle_deg),
                    "aspect": float(aspect_deg),
                    "pvtechchoice": pvtechchoice,
                    "loss_pct": float(loss_pct),
                    "mountingplace": mountingplace,
                }
                return {
                    "annual_gen_kwh_year": float(e_y_kwh),
                    "annual_gen_wh_year": float(e_y_kwh) * 1000.0,
                    "api_meta": meta,
                }
            except Exception as e:
                if resp is not None:
                    last_err = f"{type(e).__name__}: {e}; response={_extract_error_text(resp)}"
                else:
                    last_err = f"{type(e).__name__}: {e}"
                continue

    raise RuntimeError(
        f"PVGIS PVcalc failed for all endpoints. "
        f"lat={lat}, lon={lon}, peakpower_kw={peakpower_kw}, angle={angle_deg}, aspect={aspect_deg}. "
        f"Last error: {last_err}"
    )



def _cached_yearly_generation(lat: float, lon: float, wp: float, tilt_deg: float, aspect_deg: float):
    return _pvcalc_yearly_kwh(
        float(lat),
        float(lon),
        float(wp) / 1000.0,
        float(tilt_deg),
        float(aspect_deg),
    )



def _device_family(fixture_cfg):
    text = " ".join([
        str(fixture_cfg.get("device_code", "")),
        str(fixture_cfg.get("device_name", "")),
        str(fixture_cfg.get("fixture_key", "")),
        str(fixture_cfg.get("fixture_name", "")),
    ]).lower()
    if "av70" in text:
        return "AV70"
    if "av426" in text:
        return "AV426"
    return "GENERIC"



def _build_reference_annual(lat, lon, total_wp):
    aspect = _equator_facing_aspect(lat)
    return _cached_yearly_generation(float(lat), float(lon), float(total_wp), REFERENCE_TILT_DEG, aspect)



def _geometry_coefficient_av70(lat, lon):
    east = _cached_yearly_generation(float(lat), float(lon), 7.0, PHYSICAL_TILT_DEG_AV70, ASPECT_EAST)
    west = _cached_yearly_generation(float(lat), float(lon), 7.0, PHYSICAL_TILT_DEG_AV70, ASPECT_WEST)
    ref = _build_reference_annual(lat, lon, 14.0)

    geom_annual = east["annual_gen_wh_year"] + west["annual_gen_wh_year"]
    ref_annual = ref["annual_gen_wh_year"]
    coeff = (geom_annual / ref_annual) if ref_annual > 0 else 0.0

    return {
        "method": "grid_pvcalc_proxy_ew_vs_single_33_annual",
        "coefficient": float(coeff),
        "geometry_annual_gen_wh_year": float(geom_annual),
        "reference_annual_gen_wh_year": float(ref_annual),
        "geometry_inputs": [east, west],
        "reference_input": ref,
        "proxy_total_wp": 14.0,
        "real_total_wp": 1.4,
    }



def _geometry_coefficient_from_actual_panels(lat, lon, fixture_cfg, method_name: str):
    total_nominal_wp = float(fixture_cfg["pv_total_wp"])
    per_panel = []
    geom_annual = 0.0

    for panel in fixture_cfg["panels"]:
        info = _cached_yearly_generation(
            float(lat),
            float(lon),
            float(panel["wp"]),
            float(panel["tilt"]),
            float(panel["aspect"]),
        )
        per_panel.append({
            **info,
            "wp": float(panel["wp"]),
            "tilt": float(panel["tilt"]),
            "aspect": float(panel["aspect"]),
            "name": panel.get("name", ""),
        })
        geom_annual += info["annual_gen_wh_year"]

    ref = _build_reference_annual(lat, lon, total_nominal_wp)
    ref_annual = ref["annual_gen_wh_year"]
    coeff = (geom_annual / ref_annual) if ref_annual > 0 else 0.0

    return {
        "method": method_name,
        "coefficient": float(coeff),
        "geometry_annual_gen_wh_year": float(geom_annual),
        "reference_annual_gen_wh_year": float(ref_annual),
        "geometry_inputs": per_panel,
        "reference_input": ref,
        "proxy_total_wp": total_nominal_wp,
        "real_total_wp": total_nominal_wp,
    }



def _geometry_coefficient_av426(lat, lon, fixture_cfg):
    # Use actual fixture geometry so both 4x5W and 4x7W variants are supported.
    return _geometry_coefficient_from_actual_panels(
        lat,
        lon,
        fixture_cfg,
        method_name="grid_pvcalc_physical_4side_vs_single_33_annual",
    )



def _geometry_coefficient_generic(lat, lon, fixture_cfg):
    return _geometry_coefficient_from_actual_panels(
        lat,
        lon,
        fixture_cfg,
        method_name="grid_pvcalc_generic_physical_vs_single_33_annual",
    )



def _resolve_geometry_coefficient(lat, lon, fixture_cfg):
    family = _device_family(fixture_cfg)
    if family == "AV70":
        return family, _geometry_coefficient_av70(lat, lon)
    if family == "AV426":
        return family, _geometry_coefficient_av426(lat, lon, fixture_cfg)
    return family, _geometry_coefficient_generic(lat, lon, fixture_cfg)



def resolve_avlite_equivalent_config(device_id, loc, per_device_config=None):
    fixture_cfg = resolve_avlite_fixture(device_id, per_device_config)
    lat = float(loc["lat"])
    lon = float(loc["lon"])

    family, coeff_data = _resolve_geometry_coefficient(lat, lon, fixture_cfg)

    total_nominal_wp = float(fixture_cfg["pv_total_wp"])
    annual_coefficient = float(coeff_data["coefficient"])
    effective_wp = max(0.0, total_nominal_wp * annual_coefficient)
    aspect = _equator_facing_aspect(lat)

    equivalent_pct = annual_coefficient * 100.0

    avlite_meta = {
        "dataset_note": (
            "Avlite annual geometry coefficient was calculated with PVGIS Grid-Connected PV yearly electricity output "
            "and applied to the real nominal PV power before passing the resolved equivalent single panel into the "
            "standard off-grid simulator path."
        ),
        "device_family": family,
        "geometry_method": coeff_data["method"],
        "physical_panel_geometry": fixture_cfg["panel_geometry"],
        "panel_count": fixture_cfg["panel_count"],
        "total_nominal_wp": total_nominal_wp,
        "annual_geometry_coefficient": annual_coefficient,
        "effective_pv_used_for_offgrid": effective_wp,
        "geometry_inputs": coeff_data["geometry_inputs"],
        "reference_input": coeff_data["reference_input"],
        "geometry_annual_gen_wh_year": coeff_data["geometry_annual_gen_wh_year"],
        "reference_annual_gen_wh_year": coeff_data["reference_annual_gen_wh_year"],
        "grid_pv_loss_pct": GRID_PV_LOSS_PCT,
        "grid_pv_tech": GRID_PV_TECH,
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
        "pv": effective_wp,
        "batt_std": fixture_cfg["batt_nominal_wh"],
        "batt": fixture_cfg["batt_nominal_wh"],
        "battery_mode": "Built-in",
        "fixed": True,
        "tilt_options": [float(REFERENCE_TILT_DEG)],
        "tilt": float(REFERENCE_TILT_DEG),
        "equivalent_aspect": float(aspect),
        "avlite_meta": avlite_meta,

        # explicit UI/report transparency fields
        "panel_count": fixture_cfg["panel_count"],
        "panel_list": [{
            "name": p["name"],
            "wp": float(p["wp"]),
            "tilt": float(p["tilt"]),
            "aspect": float(p["aspect"]),
        } for p in fixture_cfg["panels"]],
        "total_nominal_wp": total_nominal_wp,

        # simulation value actually used
        "equivalent_panel_wp": effective_wp,
        "equivalent_panel_tilt": float(REFERENCE_TILT_DEG),
        "equivalent_panel_aspect": float(aspect),
        "equivalent_pct_of_physical_nominal": equivalent_pct,

        # annual transparency values
        "annual_geometry_coefficient": annual_coefficient,
        "annual_geometry_pct": equivalent_pct,
        "effective_pv_used_for_offgrid": effective_wp,
        "geometry_method": coeff_data["method"],
        "geometry_annual_gen_wh_year": float(coeff_data["geometry_annual_gen_wh_year"]),
        "reference_annual_gen_wh_year": float(coeff_data["reference_annual_gen_wh_year"]),

        "physical_panel_geometry": fixture_cfg["panel_geometry"],
        "certified_intensity": fixture_cfg["certified_intensity"],
        "source_note": fixture_cfg["source_note"],
    }
    return resolved
