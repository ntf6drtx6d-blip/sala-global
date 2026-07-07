import csv
import io
import time
import re
import requests
import streamlit as st

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
_MIN_DELAY_SECONDS = 1.2

COUNTRY_NAME_TO_CODE = {
    "australia": "au",
    "canada": "ca",
    "colombia": "co",
    "greece": "gr",
    "new zealand": "nz",
    "peru": "pe",
    "spain": "es",
    "united kingdom": "gb",
    "uk": "gb",
    "united states": "us",
    "usa": "us",
}

GENERIC_AIRPORT_TOKENS = {
    "airport",
    "airports",
    "aerodrome",
    "airfield",
    "airstrip",
    "base",
    "international",
    "regional",
    "municipal",
}


def _normalize_query(q: str) -> str:
    return " ".join((q or "").strip().lower().split())


def _tokenize(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", (value or "").lower()) if token}


def _is_airport_query(normalized_query: str) -> bool:
    tokens = _tokenize(normalized_query)
    if tokens.intersection({"airport", "airports", "aerodrome", "airfield", "airstrip"}):
        return True
    if _extract_icao_code(normalized_query):
        return True
    return any(re.fullmatch(r"[a-z]{3}", token) for token in tokens)


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
            if match not in {"BASE", "SALA", "PVGI", "PAPI"}:
                return match
    return None


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 7)
def _cached_airports():
    headers = {
        "User-Agent": "SALA-Feasibility-Study/1.0 (contact: support@sala-global.com)"
    }
    response = requests.get(OURAIRPORTS_URL, headers=headers, timeout=15)
    response.raise_for_status()
    reader = csv.DictReader(io.StringIO(response.text))
    return [row for row in reader if row.get("latitude_deg") and row.get("longitude_deg")]


def _airport_display_name(row):
    parts = [
        row.get("name"),
        row.get("municipality"),
        row.get("iso_country"),
    ]
    return ", ".join(str(part).strip() for part in parts if str(part or "").strip())


def _airport_code(row):
    return (
        row.get("gps_code")
        or row.get("ident")
        or row.get("local_code")
        or row.get("iata_code")
        or ""
    )


def _score_airport(row, normalized_query: str):
    query = normalized_query.strip().lower()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0

    code_values = [
        row.get("ident"),
        row.get("gps_code"),
        row.get("iata_code"),
        row.get("local_code"),
    ]
    code_values = [str(value or "").strip().lower() for value in code_values if str(value or "").strip()]
    if query in code_values:
        return 1000

    name = str(row.get("name") or "").strip().lower()
    municipality = str(row.get("municipality") or "").strip().lower()
    country = str(row.get("iso_country") or "").strip().lower()
    country_names = [name for name, code in COUNTRY_NAME_TO_CODE.items() if code == country]
    haystack = " ".join([name, municipality, country, *country_names, *code_values])
    haystack_tokens = _tokenize(haystack)
    identity_tokens = _tokenize(" ".join([name, municipality, *code_values]))
    country_query_tokens = {
        token
        for country_name in COUNTRY_NAME_TO_CODE
        for token in _tokenize(country_name)
    }
    requested_country_codes = {
        code
        for country_name, code in COUNTRY_NAME_TO_CODE.items()
        if _tokenize(country_name).issubset(query_tokens)
    }
    specific_query_tokens = query_tokens - GENERIC_AIRPORT_TOKENS - country_query_tokens
    if specific_query_tokens and not specific_query_tokens.intersection(identity_tokens):
        return 0

    score = 0
    if query == name:
        score += 500
    elif name.startswith(query):
        score += 350
    elif query in name:
        score += 250

    specific_matches = specific_query_tokens.intersection(identity_tokens)
    score += len(specific_matches) * 80

    if country in requested_country_codes:
        score += 150

    if query_tokens.issubset(haystack_tokens):
        score += 180 + len(query_tokens) * 10
    else:
        score += len(query_tokens.intersection(haystack_tokens)) * 20

    airport_type = str(row.get("type") or "")
    if airport_type == "large_airport":
        score += 350
    elif airport_type == "medium_airport":
        score += 250
    elif airport_type == "small_airport":
        score += 20
    elif airport_type in {"closed", "heliport"}:
        score -= 250
    if row.get("scheduled_service") == "yes":
        score += 250

    return score


def _lookup_airport_database(normalized_query: str):
    try:
        airports = _cached_airports()
    except Exception:
        return None

    best = None
    best_score = 0
    for row in airports:
        score = _score_airport(row, normalized_query)
        if score > best_score:
            best = row
            best_score = score

    if not best or best_score < 180:
        return None

    display_name = _airport_display_name(best)
    return {
        "label": best.get("name") or normalized_query,
        "display_name": display_name or normalized_query,
        "lat": float(best["latitude_deg"]),
        "lon": float(best["longitude_deg"]),
        "country": best.get("iso_country") or "-",
        "icao": _extract_icao_code(best.get("gps_code"), best.get("ident"), display_name),
        "raw": best,
        "source": "ourairports",
    }


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

    airport_match = _lookup_airport_database(normalized_query)
    if airport_match:
        return airport_match

    if _is_airport_query(normalized_query):
        return None

    _rate_limit()
    try:
        results = _cached_lookup(normalized_query)
    except requests.HTTPError as exc:
        if "RATE_LIMIT_429" in str(exc) or "429" in str(exc):
            return None
        raise

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
