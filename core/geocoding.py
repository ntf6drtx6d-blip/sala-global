import time
import re
import requests
import streamlit as st

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_MIN_DELAY_SECONDS = 1.2


def _normalize_query(q: str) -> str:
    return " ".join((q or "").strip().lower().split())


def _rate_limit():
    last_ts = st.session_state.get("_nominatim_last_call_ts", 0.0)
    now = time.time()
    elapsed = now - last_ts
    if elapsed < _MIN_DELAY_SECONDS:
        time.sleep(_MIN_DELAY_SECONDS - elapsed)
    st.session_state["_nominatim_last_call_ts"] = time.time()


def _extract_icao_code(*values):
    for value in values:
        text = str(value or "")
        for match in re.findall(r"\b[A-Z]{4}\b", text.upper()):
            if match not in {"SALA", "PVGI", "PAPI"}:
                return match
    return None


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def _cached_lookup(normalized_query: str):
    headers = {
        "User-Agent": "SALA-Feasibility-Study/1.0 (contact: support@sala-global.com)"
    }
    params = {
        "q": normalized_query,
        "format": "jsonv2",
        "limit": 1,
    }

    response = requests.get(
        NOMINATIM_URL,
        params=params,
        headers=headers,
        timeout=12,
    )

    if response.status_code == 429:
        raise requests.HTTPError("RATE_LIMIT_429")

    response.raise_for_status()
    return response.json()


def search_airport(query: str):
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return None

    _rate_limit()
    results = _cached_lookup(normalized_query)

    if not results:
        return None

    place = results[0]
    display_name = place.get("display_name", query)

    parts = [p.strip() for p in display_name.split(",") if p.strip()]
    country = parts[-1] if parts else "-"

    return {
        "label": place.get("name") or query.strip(),
        "display_name": display_name,
        "lat": float(place["lat"]),
        "lon": float(place["lon"]),
        "country": country,
        "icao": _extract_icao_code(query, display_name, place.get("name")),
        "raw": place,
    }
