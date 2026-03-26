query = airport_query.strip()
if not query:
    st.session_state.search_message = "Please enter an airport name."
    st.rerun()

normalized_query = " ".join(query.lower().split())
last_query = st.session_state.get("last_airport_query")

if last_query == normalized_query and st.session_state.get("study_point_confirmed"):
    st.session_state.search_message = "This airport is already loaded."
    st.rerun()

try:
    result = search_airport(query)

    if not result:
        st.session_state.search_message = f"No result found for '{query}'."
        st.rerun()

    st.session_state.airport_label = query or result["label"]
    st.session_state.airport_query = query or result["label"]
    st.session_state.lat = result["lat"]
    st.session_state.lon = result["lon"]
    st.session_state.airport_country = result.get("country", "-")
    st.session_state.study_point_confirmed = True
    st.session_state.last_airport_query = normalized_query
    st.session_state.search_message = f"Found: {result['display_name']}"
    st.session_state.map_click_info = (
        f"Study point set to {st.session_state.airport_label} "
        f"({result['lat']:.6f}, {result['lon']:.6f})"
    )

    if st.session_state.get("operating_profile_mode") == "Dusk to dawn":
        _apply_operating_profile()

    _refresh_study_ready()
    st.rerun()

except Exception as e:
    if "RATE_LIMIT_429" in str(e):
        st.session_state.search_message = (
            "Search is temporarily rate-limited by the map service. "
            "Please wait a moment and try again."
        )
    else:
        st.session_state.search_message = f"Search error: {e}"
    st.rerun()
