from datetime import UTC
import math
import re
from pvgis_client import pvcalc_monthly_wh_per_day
from core.i18n import get_report_i18n, month_label, normalize_language, t
from core.intensity import format_intensity_summary
from core.time_utils import format_timestamp, now_local, now_utc

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _plain_text(value: str) -> str:
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def _short_name(result_key: str, r: dict) -> str:
    label = (r.get("name") or result_key or "").strip()
    lamp_variant = (r.get("lamp_variant") or "").strip()
    engine = (r.get("engine") or "").strip()
    if label:
        if engine and engine != "BUILT-IN" and engine not in label:
            return f"{label} + {engine}"
        return label
    code = (r.get("device_code") or "").strip()
    if lamp_variant and code:
        return f"{code} / {lamp_variant}"
    if code and engine and engine != "BUILT-IN":
        return f"{code} + {engine}"
    if code:
        return code
    if "—" in result_key:
        return result_key.split("—", 1)[-1].strip()
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


def _classify_result_row(r: dict) -> str:
    raw = str((r or {}).get("status", "")).upper().strip()
    if raw in {"PASS", "FAIL", "NEAR THRESHOLD"}:
        return raw
    return _classify(_annual_days(r))


def _overall_case(pass_count: int, near_count: int, fail_count: int, total: int, language: str = "en") -> tuple[str, str, str]:
    if pass_count == total:
        options = {
            "en": ("All evaluated devices support the required operating profile.", "The evaluated configurations remain free from battery depletion under the defined operating profile.", "PASS"),
            "es": ("Todos los dispositivos evaluados respaldan el perfil operativo requerido.", "Las configuraciones evaluadas permanecen libres de agotamiento de batería bajo el perfil operativo definido.", "PASS"),
            "fr": ("Tous les dispositifs évalués soutiennent le profil d’exploitation requis.", "Les configurations évaluées restent sans déplétion de batterie sous le profil d’exploitation défini.", "PASS"),
        }
        return options.get(language, options["en"])
    if fail_count == 0 and near_count > 0:
        options = {
            "en": ("The system is close to full compliance.", "Most evaluated configurations support the required operating profile, but limited battery depletion remains in some cases.", "NEAR THRESHOLD"),
            "es": ("El sistema está cerca del cumplimiento total.", "La mayoría de las configuraciones evaluadas respaldan el perfil operativo requerido, pero en algunos casos persiste una depleción limitada de batería.", "NEAR THRESHOLD"),
            "fr": ("Le système est proche de la conformité complète.", "La plupart des configurations évaluées soutiennent le profil d’exploitation requis, mais une déplétion limitée de batterie subsiste dans certains cas.", "NEAR THRESHOLD"),
        }
        return options.get(language, options["en"])
    if pass_count >= 1 and fail_count >= 1:
        options = {
            "en": (
                "Some selected devices meet the required operating profile.",
                f"{pass_count} of {total} selected devices support the operating profile. The system is not fully compliant because at least one device remains below requirement.",
                "NEAR THRESHOLD",
            ),
            "es": (
                "Algunos dispositivos seleccionados cumplen el perfil operativo requerido.",
                f"{pass_count} de {total} dispositivos seleccionados soportan el perfil operativo. El sistema no es totalmente conforme porque al menos un dispositivo permanece por debajo del requisito.",
                "NEAR THRESHOLD",
            ),
            "fr": (
                "Certains dispositifs sélectionnés respectent le profil d’exploitation requis.",
                f"{pass_count} dispositifs sur {total} soutiennent le profil d’exploitation. Le système n’est pas entièrement conforme car au moins un dispositif reste en dessous de l’exigence.",
                "NEAR THRESHOLD",
            ),
        }
        return options.get(language, options["en"])
    options = {
        "en": ("The evaluated configurations do not support the required operating profile without battery depletion.", "Multiple configurations experience battery depletion during the year and may not sustain the required operating profile reliably.", "FAIL"),
        "es": ("Las configuraciones evaluadas no respaldan el perfil operativo requerido sin agotamiento de batería.", "Varias configuraciones experimentan depleción de batería durante el año y pueden no sostener de forma fiable el perfil operativo requerido.", "FAIL"),
        "fr": ("Les configurations évaluées ne soutiennent pas le profil d’exploitation requis sans déplétion de batterie.", "Plusieurs configurations subissent une déplétion de batterie au cours de l’année et peuvent ne pas maintenir de façon fiable le profil d’exploitation requis.", "FAIL"),
    }
    return options.get(language, options["en"])


def _device_interpretation(name: str, days: int, cls: str, language: str = "en") -> str:
    if cls == "PASS":
        return {
            "en": f"{name} maintains required operation throughout the year.",
            "es": f"{name} mantiene el funcionamiento requerido durante todo el año.",
            "fr": f"{name} maintient le fonctionnement requis tout au long de l’année.",
        }.get(language, f"{name} maintains required operation throughout the year.")
    if cls == "NEAR THRESHOLD":
        return {
            "en": f"{name} is near the compliance threshold and should be reviewed carefully for low-margin months.",
            "es": f"{name} está cerca del umbral de conformidad y debe revisarse cuidadosamente en los meses de menor margen.",
            "fr": f"{name} est proche du seuil de conformité et doit être examiné attentivement pour les mois à faible marge.",
        }.get(language, f"{name} is near the compliance threshold and should be reviewed carefully for low-margin months.")
    return {
        "en": f"{name} does not sustain required operation under annual worst-case conditions.",
        "es": f"{name} no sostiene la operación requerida en las condiciones anuales más desfavorables.",
        "fr": f"{name} ne maintient pas le fonctionnement requis dans les conditions annuelles les plus défavorables.",
    }.get(language, f"{name} does not sustain required operation under annual worst-case conditions.")


def _result_display_label(cls: str) -> str:
    if cls == "PASS":
        return "PASS"
    if cls == "NEAR THRESHOLD":
        return "NEAR THRESHOLD"
    return "FAIL"


def _result_detail_label(cls: str, language: str = "en") -> str:
    if cls == "PASS":
        return {
            "en": "System maintains required operation throughout the year",
            "es": "El sistema mantiene la operación requerida durante todo el año",
            "fr": "Le système maintient le fonctionnement requis tout au long de l’année",
        }.get(language, "System maintains required operation throughout the year")
    if cls == "NEAR THRESHOLD":
        return {
            "en": "System is near the compliance threshold",
            "es": "El sistema está cerca del umbral de conformidad",
            "fr": "Le système est proche du seuil de conformité",
        }.get(language, "System is near the compliance threshold")
    return {
        "en": "System does not sustain required operation under annual worst-case conditions",
        "es": "El sistema no sostiene la operación requerida en las condiciones anuales más desfavorables",
        "fr": "Le système ne maintient pas le fonctionnement requis dans les conditions annuelles les plus défavorables",
    }.get(language, "System does not sustain required operation under annual worst-case conditions")


def _result_kpi_label(cls: str, language: str = "en") -> str:
    if cls == "PASS":
        return t("ui.pass", language)
    if cls == "NEAR THRESHOLD":
        return t("ui.near_threshold", language)
    return t("ui.fail", language)


def _net_margin_pct(r: dict) -> float:
    generated = list(r.get("charge_day_pct_by_month") or [])
    discharge_day = float(r.get("discharge_pct_per_day", 0) or 0)
    if not generated:
        return 0.0
    return min(float(g) - discharge_day for g in generated)


def _usable_to_total_pct(r: dict, usable_pct: float | None) -> float | None:
    if usable_pct is None:
        return None
    cutoff = float(r.get("cutoff_pct", 0) or 0)
    usable_share = max(0.0, 1.0 - cutoff / 100.0)
    return cutoff + max(float(usable_pct), 0.0) * usable_share


def _hours_from_total_pct(r: dict, total_pct: float | None) -> float | None:
    if total_pct is None:
        return None
    batt_wh = float(r.get("batt", 0) or 0)
    power_w = max(float(r.get("power", 0) or 0), 0.001)
    return batt_wh * float(total_pct) / 100.0 / power_w


def _battery_autonomy_hours(r: dict) -> float | None:
    try:
        batt_wh = float(r.get("batt", 0) or 0)
        power_w = max(float(r.get("power", 0) or 0), 0.001)
        return batt_wh * 0.70 / power_w
    except Exception:
        return None


def _intensity_summary(r: dict, language: str = "en") -> str:
    return format_intensity_summary(
        intensity_mode=r.get("intensity_mode", "fixed"),
        intensity_pct=r.get("intensity_pct", 100.0),
        mixed_share_pct=r.get("mixed_share_pct", 50.0),
        mixed_intensity_a=r.get("mixed_intensity_a", 30.0),
        mixed_intensity_b=r.get("mixed_intensity_b", 100.0),
        effective_intensity_pct=r.get("effective_intensity_pct", r.get("intensity_pct", 100.0)),
        language=language,
    )




def _row_solar_resource_wh_day(r: dict) -> list[float]:
    values = list(r.get("monthly_solar_resource_wh_day") or [])[:12]
    values = values + [0.0] * max(0, 12 - len(values))
    if any(float(v) > 0 for v in values):
        return values

    meta = r.get("pvgis_meta") or {}
    lat = meta.get("lat")
    lon = meta.get("lon")
    pv = r.get("pv")
    tilt = r.get("tilt") if r.get("tilt") is not None else meta.get("slope")
    azim = r.get("azim") if r.get("azim") is not None else meta.get("aspect")
    try:
        if lat is not None and lon is not None and pv is not None and tilt is not None and azim is not None:
            regen = pvcalc_monthly_wh_per_day(
                lat=float(lat),
                lon=float(lon),
                pv_wp=float(pv),
                tilt_deg=float(tilt),
                aspect_deg=float(azim),
            )
            regen = list(regen or [])[:12]
            regen = regen + [0.0] * max(0, 12 - len(regen))
            if any(float(v) > 0 for v in regen):
                return regen
    except Exception:
        pass

    fallback = list(r.get("monthly_generation_wh_day") or [])[:12]
    fallback = fallback + [0.0] * max(0, 12 - len(fallback))
    return fallback


def _suppress_zero_blackout_worst_month(r: dict) -> bool:
    empty_days = list(r.get("empty_battery_days_by_month") or [])[:12]
    empty_days = empty_days + [0] * max(0, 12 - len(empty_days))
    if any(float(v) > 0 for v in empty_days):
        return False
    hours = [float(v) for v in (list(r.get("hours") or [])[:12] + [0.0] * 12)[:12]]
    if not hours:
        return False
    # If the device is capped at 24h/day for the entire year and never hits
    # blackout, showing a "worst month" is not meaningful to users.
    return min(hours) >= 23.95

CONTINUOUS_HOURS_THRESHOLD = 23.95

# Presentation order for every device list in the report: runway lights
# first (elevated before inset, edge before threshold/end), then the
# approach-slope indicators, guidance signs, runway guard lights and
# finally the wind direction indicator. Anything not covered by the rule
# (taxiway/approach/obstruction variants, third-party fixtures) sorts
# after, keeping its existing relative order.
_DEVICE_GROUP_RUNWAY = 0
_DEVICE_GROUP_PAPI = 1
_DEVICE_GROUP_SIGN = 2
_DEVICE_GROUP_RGL = 3
_DEVICE_GROUP_WDI = 4
_DEVICE_GROUP_OTHER = 5


def _device_sort_key(device: dict) -> tuple:
    code = str(device.get("device_code") or "").upper()
    variant = str(device.get("lamp_variant") or "").lower()

    if code in {"PAPI", "A-PAPI"}:
        # A-PAPI is the abbreviated variant; keep PAPI first.
        return (_DEVICE_GROUP_PAPI, 0 if code == "PAPI" else 1, 0, device.get("name", ""))
    if code.startswith("SIGN-"):
        size_rank = {"SIGN-L": 0, "SIGN-M": 1, "SIGN-S": 2}.get(code, 3)
        return (_DEVICE_GROUP_SIGN, size_rank, 0, device.get("name", ""))
    if code == "RGL":
        return (_DEVICE_GROUP_RGL, 0, 0, device.get("name", ""))
    if code == "WDI":
        return (_DEVICE_GROUP_WDI, 0, 0, device.get("name", ""))

    if "runway" in variant:
        # SP-200 is the inset fixture; every other runway light is elevated.
        mount_rank = 1 if code == "SP-200" else 0
        if "edge" in variant:
            position_rank = 0
        elif "threshold" in variant or "end" in variant:
            position_rank = 1
        else:
            position_rank = 2
        return (_DEVICE_GROUP_RUNWAY, mount_rank, position_rank, device.get("name", ""))

    return (_DEVICE_GROUP_OTHER, 0, 0, device.get("name", ""))


def _recommended_action(r: dict, required_hours: float, i18n: dict) -> tuple:
    """What would actually close the gap for a device that falls short,
    returned as (action, reason).

    Only names things that exist: the solar engine tiers by their real
    product names, and the extended-battery option the configurator itself
    offers as a battery mode. It deliberately does NOT concatenate the two
    into a product name like "SE COMPACT Extended", which is not a product
    S4GA sells.

    Which lever helps depends on what is binding. If the battery alone
    already carries past the requested hours, storage is not the
    constraint - the system cannot recharge that much per day - and more
    battery would change almost nothing; more panel is what is needed.
    """
    lower_intensity = (i18n["report.rec_lower_intensity"], i18n["report.rec_reason_builtin"])

    if str(r.get("system_type_raw") or r.get("system_type") or "") != "external_engine":
        return lower_intensity

    from core.catalog import get_cached_runtime_catalog

    try:
        _devices, engines = get_cached_runtime_catalog()
    except Exception:
        return lower_intensity

    engine_key = r.get("engine_key")
    engine = engines.get(engine_key) if engine_key else None
    if not engine:
        return lower_intensity

    autonomy = r.get("battery_autonomy_hours")
    # Tolerance so a battery that exactly covers the requirement isn't
    # called short by floating-point noise (0.7 * capacity / load lands a
    # fraction under the target often enough to matter).
    storage_is_short = autonomy is not None and float(autonomy) < float(required_hours) - 1e-6
    can_extend = str(r.get("battery_mode") or "Std") == "Std" and engine.get("batt_ext")

    if storage_is_short and can_extend:
        return (i18n["report.rec_extended_battery"], i18n["report.rec_reason_storage"])

    for candidate in sorted(engines.values(), key=lambda e: float(e.get("pv") or 0)):
        if float(candidate.get("pv") or 0) > float(engine.get("pv") or 0):
            name = candidate.get("short_name") or ""
            return (
                i18n["report.rec_larger_engine"].replace("{engine}", name),
                i18n["report.rec_reason_recharge"],
            )

    # Already on the largest engine.
    if can_extend:
        return (i18n["report.rec_extended_battery"], i18n["report.rec_reason_storage"])
    return lower_intensity


def _capability_hours(r: dict) -> float | None:
    """Hours/day this device sustains in its weakest month, i.e. every day
    of the year, with no battery depletion.

    core/simulate.py derives each month's value by binary-searching the
    largest daily energy budget at which PVGIS reports zero empty-battery
    days, so the minimum across the year is a verified figure rather than
    an extrapolation. Returns None when the simulation produced no monthly
    hours (e.g. a PVGIS failure), so callers can omit the claim instead of
    printing a misleading zero.
    """
    hours = [float(v) for v in (r.get("hours") or [])]
    if not hours:
        return None
    return min(hours)


_AXIS_EDGE_PCT = 12.0


def _requirement_label_placement(required_hours: float) -> dict:
    """Where to anchor the requirement label on the 0-24h axis, and which
    end label it makes redundant.

    Centring the label on its position works in the middle of the axis but
    collides at the extremes - a 24 h/day requirement puts it at 100%,
    where half of it overflows the track and covers the "24h" end label.
    """
    pct = max(0.0, min(required_hours / 24.0, 1.0)) * 100.0
    if pct >= 100.0 - _AXIS_EDGE_PCT:
        return {
            "requirement_label_align": "end",
            "show_axis_start_label": True,
            "show_axis_end_label": False,
        }
    if pct <= _AXIS_EDGE_PCT:
        return {
            "requirement_label_align": "start",
            "show_axis_start_label": False,
            "show_axis_end_label": True,
        }
    return {
        "requirement_label_align": "middle",
        "show_axis_start_label": True,
        "show_axis_end_label": True,
    }


def _attach_gauge_fields(devices: list, required_hours: float) -> None:
    """Percentages for page 1's 0-24h gauge, computed per device from real
    simulated hours - never carried over from a design mock.

    guaranteed = the worst month's sustainable hours (what the device
    delivers every day of the year); reserve = how much further the
    battery alone can carry it on an occasional basis. Both are expressed
    against the same fixed 24h axis so every bar is directly comparable.
    """
    for device in devices:
        capability = device.get("capability_hours")
        guaranteed_pct = 0.0 if capability is None else max(0.0, min(capability / 24.0, 1.0)) * 100.0

        autonomy = device.get("battery_autonomy_hours")
        autonomy_pct = 0.0 if autonomy is None else max(0.0, min(float(autonomy) / 24.0, 1.0)) * 100.0
        # The reserve is drawn as an extension of the guaranteed segment,
        # so it only exists where the battery reaches beyond it. Nothing to
        # draw once the guaranteed segment already fills the axis.
        reserve_pct = max(0.0, autonomy_pct - guaranteed_pct)

        meets = capability is not None and capability >= required_hours - 1e-6
        device["guaranteed_pct"] = guaranteed_pct
        device["reserve_pct"] = reserve_pct
        device["meets_requirement"] = meets


def _build_recommendations(devices: list, required_hours: float, i18n: dict) -> list:
    """One entry per device that falls short of the requested profile.

    Kept off page 1 on purpose: page 1 answers "does this work", and a
    column of remedies there reads as a list of things wrong with the
    proposal. These belong later in the document, once the reader has the
    per-device detail to interpret them.
    """
    rows = []
    for device in devices:
        if device.get("meets_requirement"):
            continue
        capability = device.get("capability_hours")
        action, reason = _recommended_action(device, required_hours, i18n)
        rows.append({
            "name": device["name"],
            "capability_hours": capability,
            "shortfall_hours": (required_hours - capability) if capability is not None else None,
            "action": action,
            "reason": reason,
        })
    return rows


def _capability_summary(devices: list, required_hours: float, language: str) -> dict:
    """Fleet-level capability for the report's headline.

    Uses the weakest device, because the installation as a whole is only
    sustainable to the point where its least capable device still is -
    the same basis as the fleet PASS/FAIL. Per-device figures are shown on
    each device's own page so a strong device isn't judged by this number.
    """
    values = [d["capability_hours"] for d in devices if d.get("capability_hours") is not None]
    capability = min(values) if values else None

    if capability is None:
        return {
            "fleet_capability_hours": None,
            "fleet_capability_display": None,
            "fleet_capability_is_continuous": False,
            "fleet_capability_margin_ratio": None,
            "fleet_capability_show_margin": False,
        }

    # hours/day is capped at 24 in the simulation, so a system that
    # comfortably runs around the clock reports a margin of exactly zero.
    # Presenting that as "1.0x margin" would read as barely scraping by -
    # the opposite of the truth - so continuous operation is labelled
    # instead of given a multiplier.
    is_continuous = capability >= CONTINUOUS_HOURS_THRESHOLD
    ratio = (capability / required_hours) if required_hours > 0 else None

    return {
        "fleet_capability_hours": capability,
        "fleet_capability_display": f"{capability:.1f} {t('ui.hours_per_day_unit', language)}",
        "fleet_capability_is_continuous": is_continuous,
        "fleet_capability_margin_ratio": ratio,
        # Below ~1.2x the multiplier adds nothing and risks looking
        # precarious; the PASS verdict and zero blackout days carry the
        # page in that case.
        "fleet_capability_show_margin": bool(
            not is_continuous and ratio is not None and ratio >= 1.2
        ),
    }


def _weakest_month_metrics(r: dict) -> tuple[int, float | None, float | None]:
    solar_resource = _row_solar_resource_wh_day(r)
    hours = list(r.get("hours") or [])[:12]
    hours = hours + [0.0] * max(0, 12 - len(hours))
    generated = list(r.get("charge_day_pct_by_month") or [])[:12]
    generated = generated + [0.0] * max(0, 12 - len(generated))
    discharge = [float(r.get("discharge_pct_per_day", 0) or 0)] * 12
    empty_days = list(r.get("empty_battery_days_by_month") or [])[:12]
    empty_days = empty_days + [0] * max(0, 12 - len(empty_days))
    margins = [float(g) - float(d) for g, d in zip(generated, discharge)]

    weakest_idx = 0
    if any(float(v) > 0 for v in empty_days):
        max_days = max(float(v) for v in empty_days)
        candidates = [i for i in range(12) if float(empty_days[i]) == max_days]
        weakest_idx = min(
            candidates,
            key=lambda i: (
                float(solar_resource[i]),
                float(hours[i]) if hours else float("inf"),
                float(margins[i]) if margins else float("inf"),
                i,
            ),
        )
    elif solar_resource and any(float(v) > 0 for v in solar_resource):
        weakest_idx = min(
            range(12),
            key=lambda i: (
                float(solar_resource[i]),
                float(hours[i]) if hours else float("inf"),
                float(margins[i]) if margins else float("inf"),
                i,
            ),
        )
    elif hours and any(float(v) > 0 for v in hours):
        weakest_idx = min(range(12), key=lambda i: (float(hours[i]), i))
    elif margins:
        weakest_idx = min(range(12), key=lambda i: (margins[i], i))

    preclip_median = list(r.get("soc_monthly_preclip_median") or r.get("soc_monthly_median") or [])[:12]
    cycle_min = list(r.get("soc_monthly_cycle_min") or r.get("soc_monthly_preclip_min") or r.get("soc_monthly_min") or [])[:12]
    fullness_proxy = list(r.get("soc_monthly_fullness_proxy") or [])[:12]
    preclip_median = preclip_median + [None] * max(0, 12 - len(preclip_median))
    cycle_min = cycle_min + [None] * max(0, 12 - len(cycle_min))
    fullness_proxy = fullness_proxy + [None] * max(0, 12 - len(fullness_proxy))
    annual_total_min = []
    for i in range(12):
        cycle_total = _usable_to_total_pct(r, cycle_min[i]) if cycle_min[i] is not None else None
        proxy_total = _usable_to_total_pct(r, fullness_proxy[i]) if fullness_proxy[i] is not None else None
        candidates = [v for v in [cycle_total, proxy_total] if v is not None]
        annual_total_min.append(min(candidates) if candidates else None)
    if any(float(v) > 0 for v in empty_days):
        annual_lowest_idx = min(
            range(12),
            key=lambda i: 999 if annual_total_min[i] is None else float(annual_total_min[i]),
        ) if annual_total_min else weakest_idx
    else:
        # For zero-blackout studies, use the actual weakest operating month rather than
        # the explanatory reserve walk, which starts in January at 100% and can bias the label.
        annual_lowest_idx = weakest_idx
    return (
        weakest_idx,
        _usable_to_total_pct(r, preclip_median[weakest_idx]),
        annual_total_min[annual_lowest_idx],
        annual_lowest_idx,
    )


def _reserve_span_pct(r: dict) -> float:
    reserve = [float(v) for v in (r.get("soc_monthly_end") or r.get("soc_monthly_avg") or []) if v is not None]
    if not reserve:
        return 0.0
    return max(reserve) - min(reserve)


def _panel_count(r: dict) -> int:
    try:
        if str(r.get("system_type", "")).lower() != "avlite_fixture":
            return 1
        panel_list = r.get("panel_list", []) or []
        if panel_list:
            return len(panel_list)
        return int(r.get("panel_count", 0) or 0)
    except Exception:
        return 0


def _solar_configuration_summary(r: dict, language: str = "en") -> str:
    count = _panel_count(r)
    geometry = str(r.get("physical_panel_geometry") or "").strip()
    if count <= 1:
        return {"en": "single panel", "es": "panel único", "fr": "panneau unique"}.get(language, "single panel")
    if geometry:
        normalized = geometry.lower()
        if normalized == "two opposite angled panels":
            return t("ui.two_opposite_angled_panels", language)
        return normalized
    if count == 2:
        return {"en": "two panels", "es": "dos paneles", "fr": "deux panneaux"}.get(language, "two panels")
    if count == 4:
        return {"en": "four vertical panels", "es": "cuatro paneles verticales", "fr": "quatre panneaux verticaux"}.get(language, "four vertical panels")
    return f"{count} panels"


def _normal_panel_orientation_deg(r: dict, aspect_key: str = "azim") -> float:
    try:
        pvgis_aspect = float(r.get(aspect_key, r.get("azim", 0.0)) or 0.0)
    except Exception:
        pvgis_aspect = 0.0
    return (pvgis_aspect + 180.0) % 360.0


def _normal_panel_orientation_label(r: dict, aspect_key: str = "azim") -> str:
    compass_deg = _normal_panel_orientation_deg(r, aspect_key)
    directions = [
        (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
        (180, "S"), (225, "SW"), (270, "W"), (315, "NW"), (360, "N"),
    ]
    direction = min(directions, key=lambda item: abs(item[0] - compass_deg))[1]
    return f"{compass_deg:.0f}° {direction}"


def _lighting_input_source(r: dict) -> tuple[str, str, str]:
    if str(r.get("system_type", "")).lower() == "avlite_fixture":
        return (
            "Estimated by SALA",
            "Manufacturer: Avlite",
            "ICAO-compliant operating consumption is estimated by SALA from Avlite documentation and is not manufacturer-verified.",
        )
    return (
        "Verified by SALA",
        "Manufacturer: S4GA",
        "ICAO-compliant operating consumption is verified by SALA using S4GA device input data.",
    )


def _input_source_brand(r: dict) -> str:
    return "Avlite" if str(r.get("system_type", "")).lower() == "avlite_fixture" else "S4GA"


def _pvgis_dataset_display(raw_dataset: str) -> str:
    raw = str(raw_dataset or "PVGIS-SARAH3").strip()
    if not raw:
        return "PVGIS-SARAH3"
    cleaned = raw.replace("(fallback:", "/").replace("fallback:", "/").replace(")", "")
    return " ".join(cleaned.split())


def build_report_data(loc, required_hours, results, overall, user_name, user_organization="", language="en"):
    language = normalize_language(language)
    i18n = get_report_i18n(language)
    now_local_dt = now_local()
    now_utc_dt = now_utc()
    airport_name = (loc.get("label") or "Study point").strip()
    coords = f"{float(loc.get('lat', 0)):.6f}, {float(loc.get('lon', 0)):.6f}"

    devices = []
    pass_count = 0
    near_count = 0
    fail_count = 0
    max_blackout = 0
    overall_margin_pct = None
    worst_blackout_pct = 0.0
    worst_blackout_device_name = ""
    worst_blackout_device_pct = 0.0

    for result_key, r in results.items():
        short = _short_name(result_key, r)
        annual_days = _annual_days(r)
        cls = _classify_result_row(r)
        energy_margin_pct = _net_margin_pct(r)
        reserve_span_pct = _reserve_span_pct(r)
        weakest_month_idx, weakest_floor_total_pct, deepest_drop_total_pct, annual_lowest_month_idx = _weakest_month_metrics(r)
        overall_margin_pct = energy_margin_pct if overall_margin_pct is None else min(overall_margin_pct, energy_margin_pct)
        try:
            worst_blackout_pct = max(worst_blackout_pct, float(r.get("overall_empty_battery_pct", 0) or 0))
        except Exception:
            pass
        overall_empty_pct = float(r.get("overall_empty_battery_pct", 0) or 0)
        if cls == "PASS":
            pass_count += 1
        elif cls == "NEAR THRESHOLD":
            near_count += 1
        else:
            fail_count += 1

        prev_max_blackout = max_blackout
        max_blackout = max(max_blackout, annual_days)
        if annual_days > prev_max_blackout or (annual_days == prev_max_blackout and overall_empty_pct > worst_blackout_device_pct):
            worst_blackout_device_name = short
            worst_blackout_device_pct = overall_empty_pct

        devices.append({
            "name": short,
            "result_key": result_key,
            "annual_blackout_days": annual_days,
            "result_class": cls,
            "result_label": _result_display_label(cls),
            "result_detail_label": _result_detail_label(cls, language),
            "result_kpi_label": _result_kpi_label(cls, language),
            "system_type": r.get("system_type", ""),
            "cover_result_label": "SYSTEM IS FULLY ENERGY-SUSTAINABLE" if cls == "PASS" else cls,
            "monthly_blackout_days": list(r.get("empty_battery_days_by_month") or [0] * 12),
            "monthly_operating_hours": list(r.get("hours") or [0] * 12),
            # Worst month of the year - the hours/day this device sustains
            # every single day, including its weakest month. This is the
            # same quantity the PASS/FAIL test compares against the
            # requirement (see core/simulate.py: status is
            # min(hours) >= required_hrs), so it can never contradict the
            # verdict shown alongside it.
            "capability_hours": _capability_hours(r),
            "device_code": r.get("device_code", ""),
            "lamp_variant": r.get("lamp_variant"),
            "system_type_raw": r.get("system_type", ""),
            "engine_key": r.get("engine_key"),
            "battery_mode": r.get("battery_mode", "Std"),
            "interpretation_text": _device_interpretation(short, annual_days, cls, language),
            "dataset": (r.get("pvgis_meta") or {}).get("dataset", "PVGIS-SARAH3"),
            "energy_balance_margin_pct": energy_margin_pct,
            "lowest_usable_reserve_pct": float(r.get("lowest_usable_reserve_pct", 0) or 0),
            "reserve_span_pct": reserve_span_pct,
            "battery_type": r.get("battery_type", "N/A"),
            "battery_autonomy_hours": _battery_autonomy_hours(r),
            "total_battery_wh": float(r.get("batt", 0) or 0),
            "cutoff_pct": float(r.get("cutoff_pct", 0) or 0),
            "usable_battery_wh": float(r.get("usable_battery_wh", 0) or 0),
            "consumption_100_intensity_wh_per_hour": float(r.get("base_power_100", r.get("power", 0)) or 0),
            "required_hours": float(required_hours),
            "worst_blackout_risk": annual_days,
            "weakest_month_idx": weakest_month_idx,
            "weakest_month_label": "" if _suppress_zero_blackout_worst_month(r) else month_label(MONTHS[weakest_month_idx], language),
            "annual_lowest_month_idx": annual_lowest_month_idx,
            "annual_lowest_month_label": month_label(MONTHS[annual_lowest_month_idx], language),
            "typical_floor_total_pct": weakest_floor_total_pct,
            "deepest_drop_total_pct": deepest_drop_total_pct,
            "lowest_battery_state_pct": deepest_drop_total_pct,
            "simulation_intensity": _intensity_summary(r, language),
            "typical_floor_hours": _hours_from_total_pct(r, weakest_floor_total_pct),
            "deepest_drop_hours": _hours_from_total_pct(r, deepest_drop_total_pct),
            "generated_pct_per_day": list(r.get("charge_day_pct_by_month") or [0] * 12)[:12] + [0.0] * max(0, 12 - len(list(r.get("charge_day_pct_by_month") or [])[:12])),
            "consumed_pct_per_day": [float(r.get("discharge_pct_per_day", 0) or 0)] * 12,
            "empty_battery_days_chart": list(r.get("empty_battery_days_by_month") or [0] * 12)[:12] + [0] * max(0, 12 - len(list(r.get("empty_battery_days_by_month") or [])[:12])),
            "solar_configuration": _solar_configuration_summary(r, language),
            "is_single_panel": _panel_count(r) <= 1,
            "nominal_power_wp": float(r.get("total_nominal_wp", r.get("pv", 0)) or 0),
            "effective_power_wp": float(r.get("equivalent_panel_wp", r.get("pv", 0)) or 0),
            "effective_ratio_pct": float(r.get("equivalent_pct_of_physical_nominal", 0) or 0),
            "equivalent_tilt_deg": float(r.get("equivalent_panel_tilt", r.get("tilt", 0)) or 0),
            "single_panel_tilt_deg": float(r.get("tilt", r.get("equivalent_panel_tilt", 0)) or 0),
            "panel_orientation_deg": _normal_panel_orientation_deg(
                r,
                "azim" if _panel_count(r) <= 1 else "equivalent_panel_aspect",
            ),
            "panel_orientation_label": _normal_panel_orientation_label(
                r,
                "azim" if _panel_count(r) <= 1 else "equivalent_panel_aspect",
            ),
            "input_source_status": _lighting_input_source(r)[0],
            "input_source_label": _lighting_input_source(r)[1],
            "input_source_note": _lighting_input_source(r)[2],
            "input_source_brand": _input_source_brand(r),
            "faa_reference": r.get("faa_reference", "N/A"),
            "faa_3sunhours_compliant": bool(r.get("faa_3sunhours_compliant")),
            "faa_8h_compliant": bool(r.get("faa_8h_compliant")),
            "generated_consumed_close": False,
            "compact_chart_mode": False,
        })

    # Operational order (runway lights, PAPI, signs, RGL, WDI) rather than
    # worst-result-first: the reader looks devices up by what they are, and
    # a stable order also keeps page 1's chart aligned with the device
    # pages that follow.
    devices.sort(key=_device_sort_key)
    _attach_gauge_fields(devices, float(required_hours))
    recommendations = _build_recommendations(devices, float(required_hours), i18n)

    total = len(devices)
    title, text, overall_label = _overall_case(pass_count, near_count, fail_count, total, language)

    cover_verdict = overall_label if overall_label != "NEAR THRESHOLD" else "NEAR THRESHOLD"
    all_zero_blackout = total > 0 and all(d["annual_blackout_days"] == 0 for d in devices)
    reserve_flat = total > 0 and all(d["lowest_usable_reserve_pct"] >= 90 and d["reserve_span_pct"] <= 10 for d in devices)
    if overall_label == "PASS":
        title = t("report.cover_pass_title", language)
        text = t("report.cover_pass_text", language)
        cover_verdict = t("report.cover_pass_verdict", language)

    if total == 1:
        single_worst_month = devices[0]["weakest_month_label"] if devices else ""
        if max_blackout == 0:
            blackout_card_helper = t("ui.no_annual_blackout_expected", language)
            if single_worst_month:
                blackout_card_helper += f" {_plain_text(t('ui.worst_month_only', language, month=single_worst_month))}"
        else:
            blackout_card_helper = _plain_text(t("ui.worst_month_only", language, month=single_worst_month)) if single_worst_month else t("ui.single_device_blackout_summary", language)
    else:
        blackout_card_helper = (
            f"{worst_blackout_device_pct:.1f}% of the year. "
            + _plain_text(t("ui.worst_device_named", language, device=worst_blackout_device_name))
        ) if max_blackout > 0 and worst_blackout_device_name else t("ui.no_annual_blackout_expected", language)

    blackout_summary_rows = [
        {
            "name": d["name"],
            "annual_days": d["annual_blackout_days"],
            "share_pct": float(d["annual_blackout_days"]) / 365.0 * 100.0,
            "worst_month_label": d["weakest_month_label"],
        }
        for d in devices
    ]

    operating_profile_rows = [{
        "name": t("ui.defined_compliance_target", language),
        "is_target": True,
        "months": [
            {
                "hours": float(required_hours),
                "delta": 0.0,
            }
            for _ in range(12)
        ],
    }]
    for d in devices:
        operating_profile_rows.append({
            "name": d["name"],
            "is_target": False,
            "months": [
                {
                    "hours": float(hours),
                    "delta": float(hours) - float(required_hours),
                }
                for hours in d["monthly_operating_hours"]
            ],
        })

    # The recommendations page only exists when something falls short.
    total_pages = 5 + len(devices) + (1 if recommendations else 0)

    return {
        "language": language,
        "i18n": i18n,
        "airport_name": airport_name,
        "airport_icao": (str(loc.get("icao", "") or loc.get("airport_icao", "")).upper().strip()),
        "coordinates": coords,
        "date": format_timestamp(now_local_dt, include_seconds=False),
        "report_id": f"SALA-{now_utc_dt.strftime('%Y%m%d%H%M%S')}",
        "report_id_display": now_utc_dt.strftime("%Y%m%d%H%M%S"),
        "generated_by": user_name,
        "generated_for_organization": user_organization,
        "required_operation": f"{float(required_hours):.1f} {t('ui.hours_per_day_unit', language)}",
        "required_hours": float(required_hours),
        **_capability_summary(devices, float(required_hours), language),
        # Page 1 gauge geometry. The requirement tick sits on the same
        # fixed 0-24h axis as every bar, so it lines up by construction.
        "requirement_pct": max(0.0, min(float(required_hours) / 24.0, 1.0)) * 100.0,
        "requirement_hours_label": f"{float(required_hours):g}h",
        # A requirement at or near either end of the axis (24/7 operation
        # being the common case) would otherwise be centred on the axis
        # edge: half the label spills out of the track and lands on top of
        # the "0h"/"24h" end label. Anchor it inwards instead, and drop the
        # end label it duplicates.
        **_requirement_label_placement(float(required_hours)),
        "devices_meeting_requirement": sum(1 for d in devices if d.get("meets_requirement")),
        "recommendations": recommendations,
        # The "365 days / 24 hrs" claim is only true when no device runs
        # its battery down at any point in the year. Gate it on that
        # rather than printing it unconditionally.
        "show_availability_hero": bool(devices) and all(d["annual_blackout_days"] == 0 for d in devices),
        "devices": devices,
        "devices_total": total,
        "devices_pass_count": pass_count,
        "devices_near_count": near_count,
        "devices_fail_count": fail_count,
        "device_names": [d["name"] for d in devices],
        "contains_s4ga": any(d["input_source_brand"] == "S4GA" for d in devices),
        "contains_avlite": any(d["input_source_brand"] == "Avlite" for d in devices),
        "max_blackout_days": max_blackout,
        "worst_blackout_pct": float(worst_blackout_pct),
        "worst_blackout_device_name": worst_blackout_device_name,
        "worst_blackout_device_pct": worst_blackout_device_pct,
        "show_blackout_chart": max_blackout > 0,
        "show_profile_chart": not (all_zero_blackout and reserve_flat),
        "all_zero_blackout": all_zero_blackout,
        "reserve_flat": reserve_flat,
        "blackout_summary_rows": blackout_summary_rows,
        "operating_profile_rows": operating_profile_rows,
        "energy_balance_margin_pct": float(overall_margin_pct or 0.0),
        "overall_result_title": title,
        "overall_result_text": text,
        "overall_result_label": overall_label,
        "cover_verdict": cover_verdict,
        "cover_statement": text,
        "methodology_note": "Assessment based on PVGIS methodology developed by the Joint Research Centre (JRC), European Commission.",
        "pvgis_dataset": devices[0]["dataset"] if devices else "PVGIS-SARAH3",
        "pvgis_dataset_display": _pvgis_dataset_display(devices[0]["dataset"] if devices else "PVGIS-SARAH3"),
        "pvgis_primary_dataset": "PVGIS-SARAH3",
        "pvgis_secondary_dataset": "ERA5 meteorological database",
        "country": loc.get("country", ""),
        "lat": float(loc.get("lat", 0)),
        "lon": float(loc.get("lon", 0)),
        "cover_device_sources": [
            {
                "brand": "S4GA",
                "status": "Verified by SALA",
            }
            if any(d["input_source_brand"] == "S4GA" for d in devices) else None,
            {
                "brand": "Avlite",
                "status": "Estimated by SALA",
            }
            if any(d["input_source_brand"] == "Avlite" for d in devices) else None,
        ],
        "total_pages": total_pages,
        "footer_note": {
            "en": "Prepared using SALA standardized off-grid feasibility methodology based on PVGIS.",
            "es": "Preparado con la metodología estandarizada de viabilidad off-grid de SALA basada en PVGIS.",
            "fr": "Préparé selon la méthodologie normalisée de faisabilité hors réseau SALA basée sur PVGIS.",
        }.get(language, "Prepared using SALA standardized off-grid feasibility methodology based on PVGIS."),
        "blackout_card_helper": blackout_card_helper,
        "devices_meet_requirement_text": t(
            "report.devices_meet_requirement",
            language,
            passed=pass_count,
            total=total,
        ),
    }
