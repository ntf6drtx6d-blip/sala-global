# utils.py
import os, io, math, time, json, re
from pathlib import Path

# ---- third-party ----
import requests
from PIL import Image, ImageDraw, ImageFilter

# ---- constants ----
UA = {"User-Agent": "S4GA-feasibility/4.3"}  # чемний UA до OSM/PVGIS
OSM_TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

CACHE_PATH = Path.home() / ".pvgis_cache.json"

# --------------------------------------------------
# Basic formatting helpers
# --------------------------------------------------
def fmt_dec(x):
    """Format number like 6.0 -> '6', 6.5 -> '6.5'."""
    return f"{x:.1f}".rstrip("0").rstrip(".")

def sanitize_for_file(s: str) -> str:
    """
    Перетворити текст на безпечну назву файлу: пробіли -> '_', тільки [A-Za-z0-9_.-]
    Порожній результат -> 'Location'
    """
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-\.]", "", s)
    return s or "Location"

def ensure_unique_path(base_path: Path) -> Path:
    """
    Якщо файл вже існує, додати _v2, _v3, ... Повертає неіснуючий шлях.
    """
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    n = 2
    while True:
        p = base_path.with_name(f"{stem}_v{n}{suffix}")
        if not p.exists():
            return p
        n += 1

def normalize_azimuth(a):
    """
    Привести азимут до [0, 360), PVGIS-конвенція: 0° = South, 180° = North.
    Повертає float або None якщо невалідно.
    """
    try:
        a = float(a)
    except Exception:
        return None
    a = a % 360.0
    if abs(a - 360.0) < 1e-6 or abs(a) < 1e-6:
        return 0.0
    return a

# --------------------------------------------------
# Networking helper with retries
# --------------------------------------------------
def retry_get(url, params=None, tries=3, timeout=20, stream=False, headers=None):
    """
    Надійний GET із бектреком; кидає RuntimeError, якщо не вдалося.
    """
    last = None
    headers = headers or UA
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout, stream=stream)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = str(e)
        time.sleep(0.6 * (i + 1))
    raise RuntimeError(last or "request failed")

# --------------------------------------------------
# Map math
# --------------------------------------------------
def _lonlat_to_pixel(lon, lat, z):
    """Web Mercator → global pixel coords @ zoom z."""
    s = 256 * (2 ** z)
    x = (lon + 180.0) / 360.0
    siny = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    y = 0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)
    return x * s, y * s

def _tile_url(z, x, y):
    return OSM_TILE.format(z=z, x=x, y=y)

# --------------------------------------------------
# Map rendering (robust; never breaks PDF)
# --------------------------------------------------
def build_map_image(lat, lon, zoom=6, px_width=2000, px_height=1300, draw_pin=True, pin_scale=2.0):
    """
    Склеює тайли OSM у PNG. Якщо мережа/OSM недоступні — підставляє сірі тайли.
    Завжди повертає валідний PNG (BytesIO).
    """
    try:
        cx, cy = _lonlat_to_pixel(lon, lat, zoom)
        half_w, half_h = px_width / 2, px_height / 2
        left   = int((cx - half_w) // 256)
        right  = int((cx + half_w) // 256)
        top    = int((cy - half_h) // 256)
        bottom = int((cy + half_h) // 256)

        out = Image.new("RGBA", (px_width, px_height), (240, 244, 247, 255))

        for tx in range(left, right + 1):
            for ty in range(top, bottom + 1):
                url = _tile_url(zoom, tx, ty)
                try:
                    r = retry_get(url, timeout=15, stream=True, headers=UA)
                    tile = Image.open(io.BytesIO(r.content)).convert("RGBA")
                except Exception:
                    # soft fallback tile (не падаємо)
                    tile = Image.new("RGBA", (256, 256), (220, 224, 229, 255))
                px = int(tx * 256 - (cx - half_w))
                py = int(ty * 256 - (cy - half_h))
                out.alpha_composite(tile, (px, py))

        if draw_pin:
            pin_x = int(half_w)
            pin_y = int(half_h)
            d = ImageDraw.Draw(out)
            base_red, base_halo = 15, 22
            r_red  = int(base_red  * pin_scale)
            r_halo = int(base_halo * pin_scale)
            d.ellipse((pin_x - r_halo, pin_y - r_halo, pin_x + r_halo, pin_y + r_halo), fill=(255, 255, 255, 235))
            d.ellipse((pin_x - r_red,  pin_y - r_red,  pin_x + r_red,  pin_y + r_red),  fill=(220,  40,  40, 255))

        bio = io.BytesIO()
        out.save(bio, "PNG")
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"[WARN] build_map_image absolute fallback: {e}")
        out = Image.new("RGBA", (px_width, px_height), (240, 244, 247, 255))
        bio = io.BytesIO(); out.save(bio, "PNG"); bio.seek(0)
        return bio

def add_round_corners_and_shadow(png_bytes, radius=14, shadow=10):
    """
    Округлення кутів + м'яка тінь для красивої картки.
    """
    im = Image.open(io.BytesIO(png_bytes.getvalue())).convert("RGBA")
    w, h = im.size

    # rounded mask
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    im = Image.composite(im, Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask)

    # soft shadow canvas
    sh = Image.new("RGBA", (w + shadow * 2, h + shadow * 2), (0, 0, 0, 0))
    blur = Image.new("L", (w, h), 0)
    ImageDraw.Draw(blur).rounded_rectangle((0, 0, w, h), radius=radius, fill=180)
    blur = blur.filter(ImageFilter.GaussianBlur(radius=shadow / 2))
    sh.paste((0, 0, 0, 60), (shadow, shadow), blur)
    sh.alpha_composite(im, (shadow, shadow))

    out = io.BytesIO()
    sh.save(out, "PNG")
    out.seek(0)
    return out
