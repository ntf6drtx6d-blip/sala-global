from __future__ import annotations

import os
from pathlib import Path

import requests


PDF_SERVICE_URL = os.environ.get("PDF_SERVICE_URL", "http://127.0.0.1:8765/render")
PDF_SERVICE_TIMEOUT = 180


def render_pdf(html: str, output_path: str | Path):
    output = Path(output_path)
    try:
        response = requests.post(
            PDF_SERVICE_URL,
            json={"html": html},
            timeout=PDF_SERVICE_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            "Playwright PDF service is not reachable. "
            "Start it with: .venv/bin/python report/pdf_service.py"
        ) from exc

    if response.status_code != 200:
        details = response.text.strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Playwright PDF render failed: {details}")

    output.write_bytes(response.content)
