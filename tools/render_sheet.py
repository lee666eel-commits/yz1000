"""Render a template sheet to a printable PDF plus a preview PNG.

Chrome lays out the mm geometry the manifest declares, so what prints is what
the manifest says. CJK comes out as Type3 subsets -- fine for a laser printer,
not for a commercial press (see the 送印 notes before ever sending one out).

    python tools/render_sheet.py template-v2/S1.html
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def render(html_path):
    html_path = os.path.abspath(html_path)
    stem = os.path.splitext(html_path)[0]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1240, "height": 1754},
                        device_scale_factor=2)
        pg.goto("file:///" + html_path.replace("\\", "/"))
        pg.pdf(path=stem + ".pdf", format="A4", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        pg.screenshot(path=stem + "_preview.png", full_page=True)
        b.close()
    for f in (stem + ".pdf", stem + "_preview.png"):
        print(f"{f}  {os.path.getsize(f)} bytes")
    return stem + ".pdf"


if __name__ == "__main__":
    render(sys.argv[1])
