import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from core.i18n import t


def render_folium_map(fmap, *, height: int, key: str, returned_objects=None, interactive: bool = False):
    returned_objects = returned_objects or []
    try:
        return st_folium(
            fmap,
            width=None,
            height=height,
            returned_objects=returned_objects,
            key=key,
        )
    except Exception:
        lang = st.session_state.get("language", "en")
        components.html(fmap._repr_html_(), height=height + 8, scrolling=False)
        if interactive:
            st.warning(
                t("ui.map_component_fallback_interactive", lang)
            )
        else:
            st.caption(t("ui.map_component_fallback_static", lang))
        return {}
