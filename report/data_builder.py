from datetime import UTC
import math
from core.i18n import get_report_i18n, month_label, normalize_language, t
from core.intensity import format_intensity_summary
from core.time_utils import format_timestamp, now_local, now_utc

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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


def _weakest_month_metrics(r: dict) -> tuple[int, float | None, float | None]:
    generated = list(r.get("charge_day_pct_by_month") or [])[:12]
    generated = generated + [0.0] * max(0, 12 - len(generated))
    discharge = [float(r.get("discharge_pct_per_day", 0) or 0)] * 12
    empty_days = list(r.get("empty_battery_days_by_month") or [])[:12]
    empty_days = empty_days + [0] * max(0, 12 - len(empty_days))
    margins = [float(g) - float(d) for g, d in zip(generated, discharge)]

    weakest_idx = 0
    if any(float(v) > 0 for v in empty_days):
        weakest_idx = max(range(12), key=lambda i: float(empty_days[i]))
    elif margins:
        weakest_idx = min(range(12), key=lambda i: margins[i])

    preclip_median = list(r.get("soc_monthly_preclip_median") or r.get("soc_monthly_median") or [])[:12]
    cycle_min = list(r.get("soc_monthly_cycle_min") or r.get("soc_monthly_preclip_min") or r.get("soc_monthly_min") or [])[:12]
    preclip_median = preclip_median + [None] * max(0, 12 - len(preclip_median))
    cycle_min = cycle_min + [None] * max(0, 12 - len(cycle_min))
    annual_lowest_idx = min(range(12), key=lambda i: 999 if cycle_min[i] is None else float(cycle_min[i])) if cycle_min else weakest_idx
    return (
        weakest_idx,
        _usable_to_total_pct(r, preclip_median[weakest_idx]),
        _usable_to_total_pct(r, cycle_min[annual_lowest_idx]),
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
        cls = _classify(annual_days)
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
            "required_hours": float(required_hours),
            "worst_blackout_risk": annual_days,
            "weakest_month_idx": weakest_month_idx,
            "weakest_month_label": month_label(MONTHS[weakest_month_idx], language),
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

    devices.sort(key=lambda x: ({"FAIL": 0, "NEAR THRESHOLD": 1, "PASS": 2}[x["result_class"]], -x["annual_blackout_days"], x["name"]))

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
                blackout_card_helper += f" {t('ui.worst_month_only', language, month=single_worst_month)}"
        else:
            blackout_card_helper = t("ui.worst_month_only", language, month=single_worst_month) if single_worst_month else t("ui.single_device_blackout_summary", language)
    else:
        blackout_card_helper = (
            f"{worst_blackout_device_pct:.1f}% of the year. "
            + t("ui.worst_device_named", language, device=worst_blackout_device_name)
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

    total_pages = 5 + len(devices)

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
