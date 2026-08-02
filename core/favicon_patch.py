# core/favicon_patch.py
#
# Safari-specific favicon fix.
#
# Streamlit sets the browser-tab icon two ways:
#   1. A static <link rel="shortcut icon" href="./favicon.png"> baked into
#      its own bundled index.html, pointing at streamlit/static/favicon.png
#      (Streamlit's own logo by default).
#   2. A JS-driven override after the app loads, which rewrites that <link>
#      tag's href to a hashed /media/<hash>.png URL derived from the
#      `page_icon` passed to st.set_page_config().
#
# Chrome picks up (2) fine. Safari has a long-standing, still-unresolved
# upstream bug (streamlit/streamlit #2514, #6137, #8362, #11069) where it
# only honors the favicon present in the INITIAL document and ignores the
# later JS-driven swap - so Safari users only ever see Streamlit's default
# logo, never SALA's.
#
# There's no supported hook to change what (1) points to. The practical
# fix is to overwrite the actual bytes of the bundled favicon.png with
# SALA's own icon, so the tag Safari already reads correctly shows the
# right image without depending on the JS override at all. This runs once
# per process start (Render gives every deploy a fresh container) and is a
# cheap no-op if already applied.

from __future__ import annotations

import logging
import shutil
from pathlib import Path

_logger = logging.getLogger(__name__)


def apply_sala_favicon(source_favicon_path: Path) -> None:
    try:
        import streamlit

        target = Path(streamlit.__file__).resolve().parent / "static" / "favicon.png"
        source = Path(source_favicon_path)
        if not source.exists() or not target.exists():
            return
        if target.read_bytes() == source.read_bytes():
            return  # already patched in this container
        shutil.copyfile(source, target)
    except Exception:
        _logger.exception("Could not patch Streamlit's bundled favicon; continuing without it.")
