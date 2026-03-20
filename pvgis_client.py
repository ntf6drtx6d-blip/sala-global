# pvgis_client.py
import os, json, time, math, hashlib
from pathlib import Path

# External deps used at runtime by main/simulate; keep imports local in request functions
# so the module can be imported even if requests isn't installed yet.

# ---------- Simple location parser (coords-first) ----------
def parse_location_input(city_or_coords: str, country: str = "") -> dict:
    """
    Accepts either 'lat, lon' or a city name. For robustness in offline/scripted use
    we fully support coordinates. If a city name (no comma) is given, we return an error
    so the caller can prompt the user to enter coordinates.
    Returns dict with keys: lat, lon, name, display, label, country.
    """
    s = (city_or_coords or "").strip()
    ctry = (country or "").strip()

    def _mk(lat, lon, name=None, display=None):
        lab = f"{lat:.4f}, {lon:.4f}"
        return {"lat": float(lat), "lon": float(lon),
                "name": name, "display": display, "label": lab,
                "country": ctry}

    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        if len(parts) == 2:
            try:
                lat = float(parts[0]); lon = float(parts[1])
                return _mk(lat, lon)
            except Exception:
                pass
    # If we got here, treat as unsupported city-only input
    raise ValueError("Please enter coordinates as 'lat, lon' (e.g., 45.043, 1.490).")

# ---------- Local cache helpers used by simulate.py ----------
from utils import CACHE_PATH as _CACHE_PATH  # ~/.pvgis_cache.json

def load_cache() -> dict:
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text())
    except Exception:
        pass
    return {}

def save_cache(cache: dict):
    try:
        _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    except Exception:
        pass

# ---------- Robust PVGIS HTTP helpers ----------
def _pvgis_session():
    import requests
    from urllib3.util import Retry
    from requests.adapters import HTTPAdapter

    s = requests.Session()
    retries = Retry(
        total=6, read=6, connect=6,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.headers.update({
        "User-Agent": "S4GA-PVCalc/1.0 (+contact: supportsales@solutions4ga.com)",
        "Accept": "application/json, */*;q=0.1",
    })
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def _cache_file_for(key: str) -> Path:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    base = Path.home() / ".cache" / "s4ga_pvgis"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{h}.json"

def _cached_get_json(url: str, params: dict, ttl_hours: int = 720):
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    cp = _cache_file_for(key)

    # serve cached
    if cp.exists():
        age_h = (time.time() - cp.stat().st_mtime) / 3600.0
        if age_h < ttl_hours:
            try:
                return json.loads(cp.read_text())
            except Exception:
                pass

    s = _pvgis_session()
    r = s.get(url, params=params, timeout=30)
    r.raise_for_status()
    try:
        data = r.json()
    except Exception as e:
        # PVGIS sometimes returns an HTML error page with 200 OK
        head = r.text[:300].lower()
        if "<html" in head or "rate limit" in head or "error" in head:
            raise RuntimeError("PVGIS returned non-JSON (likely rate-limited).") from e
        raise

    # write cache (best effort)
    try:
        cp.write_text(json.dumps(data))
    except Exception:
        pass

    return data

# ---------- PVcalc: monthly Wh/day for given PV size, tilt, aspect ----------
def _parse_monthly_wh_per_day_from_pvgis(data: dict):
    """
    Parse PVcalc JSON and return a list of 12 values (Wh/day) for the configured system.
    PVcalc monthly output contains 'E_d' [kWh/day]. Convert to Wh/day.
    """
    try:
        monthly = data["outputs"]["monthly"]
    except Exception:
        # Some versions nest under outputs.monthly.fixed or similar; try to find a monthly list
        monthly = None
        out = data.get("outputs", {})
        for v in out.values():
            if isinstance(v, list) and len(v) == 12 and isinstance(v[0], dict):
                monthly = v; break
    if not monthly or len(monthly) != 12:
        raise ValueError("Unexpected PVcalc JSON: monthly array missing/invalid")

    wh = []
    for m in monthly:
        # Try common keys in PVcalc monthly output
        # E_d: average daily energy production [kWh/day]
        ed = m.get("E_d")
        if ed is None:
            ed = m.get("E_d_fixed") or m.get("E_d_tot")
        val = float(ed) * 1000.0 if ed is not None else 0.0
        wh.append(max(0.0, val))
    return wh

def pvcalc_monthly_wh_per_day(lat, lon, pv_wp, tilt_deg, aspect_deg):
    """
    Calls PVGIS PVcalc and returns a list of 12 floats: Wh/day for the *given PV size*.
    Arguments:
      - pv_wp: PV size in Wp (e.g., 185) — we pass peakpower in kW to PVcalc.
      - tilt_deg: plane tilt [deg]; aspect: azimuth [deg], 0=south, 90=west, -90=east.
    Uses dataset order: env S4GA_PVGIS_DATASET -> SARAH2 -> ERA5.
    Uses system losses from env S4GA_PVCALC_LOSS (default 14%).
    """
    base_url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"

    # Dataset preference
    order = []
    env_ds = os.getenv("S4GA_PVGIS_DATASET")
    if env_ds: order.append(env_ds)
    for d in ("PVGIS-SARAH2", "PVGIS-ERA5"):
        if d not in order: order.append(d)

    # Inputs
    peak_kw = max(0.05, float(pv_wp) / 1000.0)
    angle = float(tilt_deg)
    aspect = float(aspect_deg)
    loss = float(os.getenv("S4GA_PVCALC_LOSS", "14"))

    common = dict(
        lat=float(lat), lon=float(lon),
        peakpower=peak_kw, loss=loss,
        angle=angle, aspect=aspect,
        usehorizon=1, mountingplace="free",
        optimalangles=0, outputformat="json",
    )

    last_err = None
    for raddb in order:
        try:
            data = _cached_get_json(base_url, {**common, "raddatabase": raddb}, ttl_hours=720)
            return _parse_monthly_wh_per_day_from_pvgis(data)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"PVGIS PVcalc failed for datasets {order}. Last error: {last_err}")

# ---------- SHScalc: monthly off-grid metrics (needs f_e) ----------
def _parse_shs_monthly(data: dict):
    """
    Parse SHScalc JSON into a list[12] of dicts that include at least 'f_e'.
    The API returns per-month metrics; field names vary slightly by version.
    We normalize to include 'f_e' (fraction of days with empty battery).
    """
    try:
        monthly = data["outputs"]["monthly"]
    except Exception:
        monthly = None
        out = data.get("outputs", {})
        for v in out.values():
            if isinstance(v, list) and len(v) == 12 and isinstance(v[0], dict):
                monthly = v; break
    if not monthly or len(monthly) != 12:
        raise ValueError("Unexpected SHScalc JSON: monthly array missing/invalid")

    norm = []
    for m in monthly:
        fe = None
        for k in ("f_e", "f_b", "f_loss", "f_def", "f_deficit"):
            if k in m:
                fe = m[k]; break
        if fe is None:
            # derive from 'empty_battery_days' if present
            ebd = m.get("empty_battery_days")
            days = m.get("n_days") or m.get("days") or 30
            fe = float(ebd) / float(days) if ebd is not None else 0.0
        try:
            fe = float(fe)
        except Exception:
            fe = 0.0
        nm = dict(m)
        nm["f_e"] = fe
        norm.append(nm)
    return norm

def shs_monthly(lat, lon, pv_wp, batt_wh, cons_wh_day, tilt_deg, aspect_deg, cutoff_pct=40):
    """
    Calls PVGIS SHScalc and returns a list of 12 dicts incl. 'f_e' per month.
    Arguments:
      - pv_wp: Wp (peak power in W)  → SHScalc 'peakpower' expects W
      - batt_wh: battery capacity in Wh → SHScalc 'batterysize'
      - cons_wh_day: consumption Wh/day → SHScalc 'consumptionday'
      - tilt_deg / aspect_deg as for PVcalc
      - cutoff_pct: battery cutoff (%), default 40 matching PVGIS example
    """
    base_url = "https://re.jrc.ec.europa.eu/api/v5_2/SHScalc"

    order = []
    env_ds = os.getenv("S4GA_PVGIS_DATASET")
    if env_ds: order.append(env_ds)
    for d in ("PVGIS-SARAH2", "PVGIS-ERA5"):
        if d not in order: order.append(d)

    common = dict(
        lat=float(lat), lon=float(lon),
        peakpower=max(1.0, float(pv_wp)),              # W
        batterysize=max(10.0, float(batt_wh)),         # Wh
        consumptionday=max(0.0, float(cons_wh_day)),   # Wh/day
        cutoff=max(0.0, min(90.0, float(cutoff_pct))),
        angle=float(tilt_deg),
        aspect=float(aspect_deg),
        usehorizon=1,
        outputformat="json",
    )

    last_err = None
    for raddb in order:
        try:
            data = _cached_get_json(base_url, {**common, "raddatabase": raddb}, ttl_hours=720)
            return _parse_shs_monthly(data)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"PVGIS SHScalc failed for datasets {order}. Last error: {last_err}")
