
# ui/result_helpers.py

import math
import streamlit as st
from core.i18n import month_label, month_labels, t


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_required_hours(hours: float) -> str:
    lang = st.session_state.get("language", "en")
    return f"{math.ceil(float(hours))} {t('ui.hours_per_day_unit', lang)}"


def format_achievable_hours(hours: float) -> str:
    lang = st.session_state.get("language", "en")
    return f"{math.floor(float(hours))} {t('ui.hours_per_day_unit', lang)}"


def format_battery_hours(hours: float) -> str:
    h = float(hours)
    whole = int(h)
    minutes = int(round((h - whole) * 60))
    if minutes == 60:
        whole += 1
        minutes = 0
    if minutes == 0:
        return f"{whole}h"
    return f"{whole}h {minutes:02d}m"


def format_energy_wh(val: float) -> str:
    try:
        return f"{float(val):.1f} Wh"
    except Exception:
        return "N/A"


def format_percent(val: float, digits: int = 0) -> str:
    try:
        return f"{float(val):.{digits}f}%"
    except Exception:
        return "N/A"


def operating_mode_name() -> str:
    lang = st.session_state.get("language", "en")
    mode = st.session_state.get("operating_profile_mode", t("ui.mode_custom", lang))
    if mode in {"24/7", t("ui.mode_247", lang)}:
        return {
            "en": "24/7 operation",
            "es": "Operación 24/7",
            "fr": "Exploitation 24/7",
        }.get(lang, "24/7 operation")
    if mode in {"Dusk to dawn", t("ui.mode_dusk", lang)}:
        return {
            "en": "Dusk-to-Dawn",
            "es": "De anochecer a amanecer",
            "fr": "Du crépuscule à l’aube",
        }.get(lang, "Dusk-to-Dawn")
    return {
        "en": "Custom operation",
        "es": "Operación personalizada",
        "fr": "Exploitation personnalisée",
    }.get(lang, "Custom operation")


def operating_window_example(hours_value: float) -> str:
    h = max(0.0, min(float(hours_value), 24.0))
    if h >= 24:
        return "00:00–24:00"

    end_hour = 6.0
    start_hour = (end_hour - h) % 24

    def fmt(x: float) -> str:
        whole = int(x) % 24
        minutes = int(round((x - int(x)) * 60))
        if minutes == 60:
            whole = (whole + 1) % 24
            minutes = 0
        return f"{whole:02d}:{minutes:02d}"

    return f"{fmt(start_hour)}–{fmt(end_hour)}"


def short_device_label(full_name: str) -> str:
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def annual_empty_battery_stats(results: dict):
    worst_name = None
    worst_pct = None
    worst_days = None

    for device_name, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is None:
            continue
        try:
            pct = float(pct)
        except Exception:
            continue

        days = annual_blackout_days_from_row(r)

        if worst_pct is None or pct > worst_pct:
            worst_pct = pct
            worst_name = short_device_label(device_name)
            worst_days = days

    if worst_pct is None:
        return None, None, None

    return worst_days, worst_pct, worst_name


def count_device_statuses(results: dict):
    total = len(results)
    passed = 0

    for _, r in results.items():
        if r.get("status") == "PASS":
            passed += 1

    failed = total - passed
    return total, passed, failed


def overall_state(results: dict):
    total, passed, failed = count_device_statuses(results)

    if total == 0:
        return "unknown"
    if passed == total:
        return "all_pass"
    if failed == total:
        return "none_pass"
    return "mixed"


def battery_reserve_hours(result_row: dict):
    try:
        batt = float(result_row.get("batt", 0))
        power = max(float(result_row.get("power", 0.01)), 0.01)
        return batt * 0.70 / power
    except Exception:
        return None


def device_blackout_days(result_row: dict):
    return annual_blackout_days_from_row(result_row)


def annual_blackout_days_from_row(result_row: dict):
    try:
        monthly_days = result_row.get("empty_battery_days_by_month")
        if isinstance(monthly_days, (list, tuple)):
            values = [float(v) for v in monthly_days if v is not None]
            if values:
                return int(round(sum(values)))
        pct = result_row.get("overall_empty_battery_pct")
        if pct is None:
            return None
        return round(365 * float(pct) / 100.0)
    except Exception:
        return None


def overall_conclusion_text(results: dict) -> str:
    state = overall_state(results)
    total, _, _ = count_device_statuses(results)
    lang = st.session_state.get("language", "en")

    if total == 1:
        if state == "all_pass":
            return {
                "en": "The selected device meets the required operating profile.",
                "es": "El dispositivo seleccionado cumple el perfil operativo requerido.",
                "fr": "Le dispositif sélectionné respecte le profil d’exploitation requis.",
            }.get(lang, "The selected device meets the required operating profile.")
        if state == "none_pass":
            return {
                "en": "The selected device does not meet the required operating profile.",
                "es": "El dispositivo seleccionado no cumple el perfil operativo requerido.",
                "fr": "Le dispositif sélectionné ne respecte pas le profil d’exploitation requis.",
            }.get(lang, "The selected device does not meet the required operating profile.")
        return {
            "en": "The selected device could not be fully assessed.",
            "es": "No se pudo evaluar completamente el dispositivo seleccionado.",
            "fr": "Le dispositif sélectionné n’a pas pu être évalué complètement.",
        }.get(lang, "The selected device could not be fully assessed.")

    if state == "all_pass":
        return {
            "en": "All selected devices meet the required operating profile.",
            "es": "Todos los dispositivos seleccionados cumplen el perfil operativo requerido.",
            "fr": "Tous les dispositifs sélectionnés respectent le profil d’exploitation requis.",
        }.get(lang, "All selected devices meet the required operating profile.")
    if state == "none_pass":
        return {
            "en": "None of the selected devices meet the required operating profile.",
            "es": "Ninguno de los dispositivos seleccionados cumple el perfil operativo requerido.",
            "fr": "Aucun des dispositifs sélectionnés ne respecte le profil d’exploitation requis.",
        }.get(lang, "None of the selected devices meet the required operating profile.")
    if state == "mixed":
        return {
            "en": "Some selected devices meet the required operating profile.",
            "es": "Algunos dispositivos seleccionados cumplen el perfil operativo requerido.",
            "fr": "Certains dispositifs sélectionnés respectent le profil d’exploitation requis.",
        }.get(lang, "Some selected devices meet the required operating profile.")
    return {
        "en": "The selected device set could not be fully assessed.",
        "es": "El conjunto de dispositivos seleccionado no pudo evaluarse completamente.",
        "fr": "L’ensemble de dispositifs sélectionné n’a pas pu être évalué complètement.",
    }.get(lang, "The selected device set could not be fully assessed.")


def overall_interpretation_text(results: dict) -> str:
    total, passed, _ = count_device_statuses(results)
    state = overall_state(results)
    lang = st.session_state.get("language", "en")

    if total == 1:
        if state == "all_pass":
            return {
                "en": "The selected operating profile is supported year-round.",
                "es": "El perfil operativo seleccionado está respaldado durante todo el año.",
                "fr": "Le profil d’exploitation sélectionné est assuré toute l’année.",
            }.get(lang, "The selected operating profile is supported year-round.")
        if state == "none_pass":
            return {
                "en": "The selected device does not support the selected operating profile year-round.",
                "es": "El dispositivo seleccionado no soporta el perfil operativo seleccionado durante todo el año.",
                "fr": "Le dispositif sélectionné ne soutient pas le profil d’exploitation sélectionné toute l’année.",
            }.get(lang, "The selected device does not support the selected operating profile year-round.")
        return {
            "en": "The selected device could not be fully assessed.",
            "es": "No se pudo evaluar completamente el dispositivo seleccionado.",
            "fr": "Le dispositif sélectionné n’a pas pu être évalué complètement.",
        }.get(lang, "The selected device could not be fully assessed.")

    if state == "all_pass":
        return {
            "en": "The selected operating profile is supported year-round by all selected devices.",
            "es": "El perfil operativo seleccionado está respaldado durante todo el año por todos los dispositivos seleccionados.",
            "fr": "Le profil d’exploitation sélectionné est assuré toute l’année par tous les dispositifs sélectionnés.",
        }.get(lang, "The selected operating profile is supported year-round by all selected devices.")

    if state == "none_pass":
        return {
            "en": "No selected device supports the selected operating profile year-round.",
            "es": "Ningún dispositivo seleccionado soporta el perfil operativo seleccionado durante todo el año.",
            "fr": "Aucun dispositif sélectionné ne soutient le profil d’exploitation sélectionné toute l’année.",
        }.get(lang, "No selected device supports the selected operating profile year-round.")

    if state == "mixed":
        messages = {
            "en": f"{passed} of {total} selected devices support the operating profile. The system is not fully compliant because at least one device remains below requirement.",
            "es": f"{passed} de {total} dispositivos seleccionados soportan el perfil operativo. El sistema no es totalmente conforme porque al menos un dispositivo permanece por debajo del requisito.",
            "fr": f"{passed} dispositifs sur {total} soutiennent le profil d’exploitation. Le système n’est pas entièrement conforme car au moins un dispositif reste en dessous de l’exigence.",
        }
        return messages.get(lang, messages["en"])

    return {
        "en": "The selected device set could not be fully assessed.",
        "es": "El conjunto de dispositivos seleccionado no pudo evaluarse completamente.",
        "fr": "L’ensemble de dispositifs sélectionné n’a pas pu être évalué complètement.",
    }.get(lang, "The selected device set could not be fully assessed.")


def pvgis_to_compass(deg: float) -> float:
    return (float(deg) + 180.0) % 360.0


def azimuth_to_direction(compass_deg: float) -> str:
    deg = float(compass_deg) % 360.0

    if abs(deg - 0.0) < 1e-9:
        return "North"
    if abs(deg - 90.0) < 1e-9:
        return "East"
    if abs(deg - 180.0) < 1e-9:
        return "South"
    if abs(deg - 270.0) < 1e-9:
        return "West"

    if 45.0 <= deg < 135.0:
        return "East"
    if 135.0 <= deg < 225.0:
        return "South"
    if 225.0 <= deg < 315.0:
        return "West"
    return "North"


def format_panel_azimuth(deg: float) -> str:
    compass = pvgis_to_compass(deg)
    direction = azimuth_to_direction(compass)
    compass_rounded = int(round(compass)) % 360
    if compass_rounded == 360:
        compass_rounded = 0
    return f"{direction} ({compass_rounded}°)"


def format_panel_azimuths(panel_list):
    formatted = []
    seen = set()

    for panel in panel_list or []:
        try:
            label = format_panel_azimuth(float(panel.get("aspect", 0)))
        except Exception:
            continue
        if label not in seen:
            seen.add(label)
            formatted.append(label)

    def _sort_key(label: str):
        try:
            deg = int(label.split("(")[1].split("°")[0])
            return deg
        except Exception:
            return 999

    formatted.sort(key=_sort_key)
    return ", ".join(formatted) if formatted else "N/A"
