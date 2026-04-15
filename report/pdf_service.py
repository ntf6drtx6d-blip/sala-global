from __future__ import annotations

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from playwright.async_api import async_playwright


HOST = os.environ.get("PDF_SERVICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", os.environ.get("PDF_SERVICE_PORT", "8765")))


def _prepare_env() -> None:
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")


async def _render_pdf_bytes(html: str) -> bytes:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        await page.emulate_media(media="print")
        await page.wait_for_load_state("networkidle")
        await page.evaluate(
            """
            async () => {
              if (document.fonts && document.fonts.ready) {
                await document.fonts.ready;
              }
              const images = Array.from(document.images || []);
              await Promise.all(images.map(img => {
                if (img.complete) return Promise.resolve();
                return new Promise(resolve => {
                  img.addEventListener('load', resolve, { once: true });
                  img.addEventListener('error', resolve, { once: true });
                });
              }));
              const charts = Array.from(document.querySelectorAll('.plotly-chart .plotly-graph-div'));
              if (charts.length && !window.Plotly) {
                throw new Error('Plotly charts were not initialized before PDF export.');
              }
              if (charts.length) {
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              }
            }
            """
        )
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "12mm", "right": "12mm", "bottom": "14mm", "left": "12mm"},
        )
        await browser.close()
        return pdf_bytes


class PdfHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/render":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            html = payload["html"]
            if not isinstance(html, str) or not html.strip():
                raise ValueError("Field 'html' must be a non-empty string.")
            pdf_bytes = asyncio.run(_render_pdf_bytes(html))
        except Exception as exc:  # noqa: BLE001
            body = str(exc).encode("utf-8", errors="replace")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404, "Not found")
            return
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[pdf-service] {fmt % args}\n")


def main() -> int:
    _prepare_env()
    server = HTTPServer((HOST, PORT), PdfHandler)
    print(f"PDF service listening on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
