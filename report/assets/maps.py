from pathlib import Path
import os
import tempfile

import requests
from PIL import Image as PILImage, ImageDraw
import matplotlib.pyplot as plt


def _save_bytes_to_tmp(content: bytes) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    Path(tmp.name).write_bytes(content)
    return tmp.name


def _fallback_map(lat: float, lon: float, width: int = 700, height: int = 380) -> str:
    img = PILImage.new("RGB", (width, height), (244, 247, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle((1, 1, width - 2, height - 2), outline=(210, 218, 226), width=2)

    # simple cross grid so the fallback does not look empty
    for x in range(0, width, max(1, width // 6)):
        draw.line((x, 0, x, height), fill=(228, 233, 238), width=1)
    for y in range(0, height, max(1, height // 4)):
        draw.line((0, y, width, y), fill=(228, 233, 238), width=1)

    cx, cy = width // 2, height // 2
    draw.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(220, 38, 38), outline=(255, 255, 255), width=2)
    draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), outline=(220, 38, 38), width=2)

    txt = f"Study point\n{lat:.6f}, {lon:.6f}"
    draw.text((18, 18), txt, fill=(55, 65, 81))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name, format="PNG")
    return tmp.name


def _google_static_map(lat: float, lon: float, width: int, height: int, zoom: int) -> str | None:
    api_key = os.environ.get("GOOGLE_STATIC_MAPS_API_KEY")
    if not api_key:
        return None
    url = (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lon}"
        f"&zoom={zoom}"
        f"&size={width}x{height}"
        "&scale=2"
        "&maptype=roadmap"
        f"&markers=color:red|{lat},{lon}"
        f"&key={api_key}"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    if resp.content:
        return _save_bytes_to_tmp(resp.content)
    return None


def _mapbox_static_map(lat: float, lon: float, width: int, height: int, zoom: int) -> str | None:
    token = os.environ.get("MAPBOX_STATIC_MAPS_TOKEN")
    if not token:
        return None
    url = (
        "https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/"
        f"pin-s+e11d48({lon},{lat})/{lon},{lat},{zoom},0/{width}x{height}"
        f"?access_token={token}"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    if resp.content:
        return _save_bytes_to_tmp(resp.content)
    return None


def generate_static_map(lat: float, lon: float, width: int = 700, height: int = 380, zoom: int = 9):
    zoom = min(max(int(zoom), 10), 12)
    try:
        for provider in (_google_static_map, _mapbox_static_map):
            path = provider(lat, lon, width, height, zoom)
            if path:
                return path
    except Exception:
        pass

    url = (
        "https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lon}&zoom={zoom}&size={width}x{height}"
        f"&markers={lat},{lon},red-pushpin"
    )
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "SALA-Feasibility-Study/1.0"})
        resp.raise_for_status()
        if resp.content:
            return _save_bytes_to_tmp(resp.content)
    except Exception:
        pass

    # second fallback: matplotlib so there is always a visible point
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.set_facecolor("#F8FAFC")
        ax.scatter([lon], [lat], s=150, c="#DC2626", edgecolors="white", linewidths=1.4, zorder=3)
        ax.annotate(f"{lat:.4f}, {lon:.4f}", (lon, lat), xytext=(8, 8), textcoords="offset points")
        ax.set_title("Study point")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout()
        fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return tmp.name
    except Exception:
        return _fallback_map(lat, lon, width=width, height=height)
