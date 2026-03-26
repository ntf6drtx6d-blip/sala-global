import time
import requests
import streamlit as st


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _normalize_query(q: str) -> str:
    return " ".join((q or "").strip().lower().split())


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def cached_nominatim_search(query: str):
    q = _normalize_query(query)
    if not q:
        return []

    headers = {
        "User-Agent": "SALA-Feasibility-Study/1.0 (contact: support@sala-global.com)"
    }
    params = {
        "q": q,
        "format": "jsonv2",
        "limit": 1,
    }

    for attempt in range(3):
        resp = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue

        resp.raise_for_status()

    raise requests.HTTPError(f"429 Too Many Requests from Nominatim for query: {q}")


def search_airport(query: str):
    results = cached_nominatim_search(query)
    if not results:
        return None

    place = results[0]
    display_name = place.get("display_name", query)

    country = "-"
    parts = [p.strip() for p in display_name.split(",") if p.strip()]
    if parts:
        country = parts[-1]

    return {
        "label": place.get("name") or query.strip() or display_name,
        "lat": float(place["lat"]),
        "lon": float(place["lon"]),
        "display_name": display_name,
        "country": country,
        "raw": place,
    }
