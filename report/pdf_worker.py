from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright


def _prepare_env() -> None:
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")


async def _render(html_path: str, output_path: str) -> None:
    html = Path(html_path).read_text(encoding="utf-8")
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
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "12mm", "right": "12mm", "bottom": "14mm", "left": "12mm"},
        )
        await browser.close()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: pdf_worker.py <html_path> <output_path>", file=sys.stderr)
        return 2
    _prepare_env()
    asyncio.run(_render(argv[1], argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
