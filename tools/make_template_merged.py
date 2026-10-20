"""Generate the merged 996-char sheet (ext900 + latin-punct, deduped) with a
logo block, a signature, and an info footer on the last page.

    python tools/make_template_merged.py --out template-merged

Grid geometry matches template-1k (10 cols x 11 rows, cell 17.8mm, pitch
22.2mm, origin 16,32mm) so build_font.py's existing slicer needs no changes.
The only new thing per page: the top-left 2x2 cells are reserved for the
logo image instead of characters, and a signature image sits in the header
band (no cell reserved -- it never overlaps the grid).
"""
import argparse
import base64
import json
import os
import sys

PAGE_W, PAGE_H = 210.0, 297.0
MARK = 8.0
MARK_INSET = 16.0
GRID_X0, GRID_Y0 = 16.0, 32.0
CELL = 17.8
PITCH = 22.2
COLS, ROWS = 10, 11
LOGO_COLS, LOGO_ROWS = 2, 2
CELL_INSET = 0.6

MARKS_MM = [
    (MARK_INSET, MARK_INSET),
    (PAGE_W - MARK_INSET, MARK_INSET),
    (PAGE_W - MARK_INSET, PAGE_H - MARK_INSET),
    (MARK_INSET, PAGE_H - MARK_INSET),
]

GRID_RED = "#e23b32"
CROSS_RED = "rgba(226,59,50,0.30)"


def data_uri(path):
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/{ext};base64,{b64}"


def load_merged_charset(base_file, extra_file):
    with open(base_file, encoding="utf-8") as f:
        base = [c for c in f.read() if not c.isspace()]
    with open(extra_file, encoding="utf-8") as f:
        extra = [c for c in f.read() if not c.isspace()]
    seen = set(base)
    merged = list(base)
    for c in extra:
        if c not in seen:
            seen.add(c)
            merged.append(c)
    return merged


def row_cols(r):
    """Column range available for characters on row r (logo eats the
    top-left LOGO_COLS x LOGO_ROWS block)."""
    start = LOGO_COLS if r < LOGO_ROWS else 0
    return list(range(start, COLS))


def per_page_capacity():
    return sum(len(row_cols(r)) for r in range(ROWS))


def cell_xy(r, c):
    # columns sit flush against each other (no label gutter sideways);
    # rows use PITCH because each row needs room for the label above it.
    return GRID_X0 + c * CELL, GRID_Y0 + r * PITCH


GRID_WIDTH_MM = COLS * CELL  # 178mm: 16..194, flush with the side marks


def build_pages(charset, footer_lines):
    """Yield (cells, footer_rows_used) per page. footer_lines only get
    placed on the final page, after a blank row following the last char."""
    cap = per_page_capacity()
    n_pages = max(1, -(-len(charset) // cap))
    pages = []
    i = 0
    for p in range(n_pages):
        cells = []
        is_last = (p == n_pages - 1)
        last_row_used = -1
        for r in range(ROWS):
            for c in row_cols(r):
                if i >= len(charset):
                    break
                x, y = cell_xy(r, c)
                ch = charset[i]
                cells.append({
                    "row": r, "col": c, "char": ch, "cp": ord(ch),
                    "cell_mm": [x, y, CELL, CELL],
                    "ink_mm": [x + CELL_INSET, y + CELL_INSET,
                               CELL - 2 * CELL_INSET, CELL - 2 * CELL_INSET],
                })
                i += 1
                last_row_used = r
            if i >= len(charset):
                break
        footer = []
        free_cells = []
        redraw_row = None
        if is_last and i >= len(charset):
            blank_row = last_row_used + 2  # one full row skipped
            for k, line in enumerate(footer_lines):
                fr = blank_row + k
                if fr < ROWS:
                    footer.append((fr, line))
            free_start = blank_row + len(footer_lines)
            free_rows_available = ROWS - free_start
            # leave the last available row for the redraw-in-neat-script lines
            free_rows = max(0, free_rows_available - 1)
            for r in range(free_start, free_start + free_rows):
                for c in row_cols(r):
                    x, y = cell_xy(r, c)
                    free_cells.append({
                        "row": r, "col": c,
                        "cell_mm": [x, y, CELL, CELL],
                    })
            if free_rows_available > free_rows:
                redraw_row = free_start + free_rows
        pages.append((cells, footer, free_cells, redraw_row))
    return pages


def page_html(page_id, page_no, n_pages, cells, footer, free_cells,
              redraw_row, logo_uri):
    boxes = []
    for x, y in MARKS_MM:
        boxes.append(f'<div class="mark" style="left:{x - MARK / 2:.2f}mm;'
                      f'top:{y - MARK / 2:.2f}mm"></div>')
    for cel in cells:
        x, y = cel["cell_mm"][0], cel["cell_mm"][1]
        boxes.append(
            f'<div class="lab" style="left:{x:.2f}mm;top:{y - 4.4:.2f}mm">'
            f'{cel["char"]}</div>'
            f'<div class="cell" style="left:{x:.2f}mm;top:{y:.2f}mm">'
            f'<i class="h"></i><i class="v"></i>'
            f'<i class="d1"></i><i class="d2"></i></div>'
        )
    logo_x, logo_y = cell_xy(0, 0)
    logo_w = LOGO_COLS * CELL
    logo_h = LOGO_ROWS * PITCH - (PITCH - CELL)
    logo_html = (f'<img class="logo" style="left:{logo_x:.2f}mm;'
                 f'top:{logo_y:.2f}mm;width:{logo_w:.2f}mm;'
                 f'height:{logo_h:.2f}mm" src="{logo_uri}">')
    footer_html = "".join(
        f'<div class="footer-line" style="top:{GRID_Y0 + fr * PITCH + 6:.2f}mm">'
        f'{line}</div>'
        for fr, line in footer
    )
    free_html = ""
    if free_cells:
        note_y = free_cells[0]["cell_mm"][1] - 4.4
        free_html = (f'<div class="free-note" style="top:{note_y:.2f}mm">'
                     f'自由字：以下空格随你发挥，想加什么字都行</div>')
        for cel in free_cells:
            x, y = cel["cell_mm"][0], cel["cell_mm"][1]
            free_html += (
                f'<div class="cell free" style="left:{x:.2f}mm;top:{y:.2f}mm">'
                f'<i class="h"></i><i class="v"></i>'
                f'<i class="d1"></i><i class="d2"></i></div>'
            )
    redraw_html = ""
    if redraw_row is not None:
        top = GRID_Y0 + redraw_row * PITCH
        redraw_html = (
            f'<div class="redraw-note" style="top:{top:.2f}mm">'
            f'为了提高自由字的辨识率，请用正楷复写一遍</div>'
        )
        for k in range(3):
            line_y = top + 6 + k * 5.5
            redraw_html += (f'<div class="redraw-line" '
                             f'style="top:{line_y:.2f}mm"></div>')
    return f"""<meta charset="utf-8">
<title>{page_id}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  html, body {{ margin: 0; padding: 0; overflow: hidden; }}
  body {{ width: {PAGE_W}mm; height: {PAGE_H - 0.4:.1f}mm; position: relative;
          font-family: "Microsoft YaHei","Noto Sans CJK SC",sans-serif; }}
  .mark {{ position: absolute; width: {MARK}mm; height: {MARK}mm;
           box-sizing: border-box; border: {MARK / 2}mm solid #000; }}
  .cell {{ position: absolute; width: {CELL}mm; height: {CELL}mm;
           box-sizing: border-box; border: 0.3mm solid {GRID_RED};
           overflow: hidden; }}
  .cell i {{ position: absolute; display: block; }}
  .h {{ left: 0; top: 50%; width: 100%; border-top: 0.2mm dashed {CROSS_RED}; }}
  .v {{ top: 0; left: 50%; height: 100%; border-left: 0.2mm dashed {CROSS_RED}; }}
  .d1, .d2 {{ left: 0; top: 50%; width: 100%;
              border-top: 0.2mm dashed {CROSS_RED};
              transform-origin: 50% 50%; }}
  .d1 {{ transform: rotate(45deg) scaleX(1.4143); }}
  .d2 {{ transform: rotate(-45deg) scaleX(1.4143); }}
  .lab {{ position: absolute; width: {CELL}mm; height: 4.4mm;
          color: {GRID_RED}; font-size: 3.1mm; line-height: 4.4mm;
          text-align: center; }}
  .hdr {{ position: absolute; left: {GRID_X0}mm; top: 20mm;
          width: {GRID_WIDTH_MM}mm; color: #666; font-size: 3.2mm; }}
  .logo {{ position: absolute; object-fit: contain; }}
  .footer-line {{ position: absolute; left: {GRID_X0}mm;
                  width: {GRID_WIDTH_MM}mm;
                  color: #333; font-size: 3.6mm; text-align: center; }}
  .cell.free {{ border-color: #7a8fa6; }}
  .free .h, .free .v, .free .d1, .free .d2 {{ border-color: rgba(122,143,166,0.30); }}
  .free-note {{ position: absolute; left: {GRID_X0}mm;
                width: {GRID_WIDTH_MM}mm;
                color: #7a8fa6; font-size: 3.2mm; }}
  .redraw-note {{ position: absolute; left: {GRID_X0}mm;
                  width: {GRID_WIDTH_MM}mm;
                  color: #666; font-size: 3.2mm; }}
  .redraw-line {{ position: absolute; left: {GRID_X0}mm;
                  width: {GRID_WIDTH_MM}mm; height: 0;
                  border-top: 0.25mm solid #999; }}
</style>
<div class="hdr"><span>{page_id} &nbsp; ({page_no}/{n_pages})</span></div>
{logo_html}
{"".join(boxes)}
{footer_html}
{free_html}
{redraw_html}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-file", default="chars-ext900.txt")
    ap.add_argument("--extra-file", default="chars-latin-punct.txt")
    ap.add_argument("--logo", default="assets/logo.png")
    ap.add_argument("--email", default="lucaslimzzzce@gmail.com")
    ap.add_argument("--site", default="https://claude.ai/artifact/H7z5UYD9AtNKYRfByZrAfi")
    ap.add_argument("--font-link", default="",
                     help="leave empty until a verified, complete font "
                          "package actually exists to link to")
    ap.add_argument("--prefix", default="M")
    args = ap.parse_args()

    charset = load_merged_charset(args.base_file, args.extra_file)
    logo_uri = data_uri(args.logo)

    footer_lines = [f"{args.email} &nbsp;|&nbsp; {args.site}"]
    if args.font_link:
        footer_lines.append(f"字体包（含此份手写真迹）：{args.font_link}")
    else:
        footer_lines.append("字体包制作中，敬请期待——完成后另行公布下载链接")

    pages = build_pages(charset, footer_lines)
    n_pages = len(pages)
    os.makedirs(args.out, exist_ok=True)

    manifest = {
        "page_mm": [PAGE_W, PAGE_H],
        "marks_mm": [list(m) for m in MARKS_MM],
        "mark_side_mm": MARK,
        "cell_mm": CELL,
        "grid": {"cols": COLS, "rows": ROWS, "x0": GRID_X0, "y0": GRID_Y0,
                 "pitch_mm": PITCH},
        "grid_color": "red",
        "logo_block": {"rows": LOGO_ROWS, "cols": LOGO_COLS,
                        "note": "top-left cells reserved for logo, not writable"},
        "sheets": [],
    }

    for p, (cells, footer, free_cells, redraw_row) in enumerate(pages):
        pid = f"{args.prefix}{p + 1}"
        html = page_html(pid, p + 1, n_pages, cells, footer, free_cells,
                          redraw_row, logo_uri)
        path = os.path.join(args.out, f"{pid}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        manifest["sheets"].append({"id": pid, "html": f"{pid}.html",
                                    "cells": cells, "free_cells": free_cells})
        print(f"{path}  {len(cells)} cells  footer={len(footer)}  "
              f"free={len(free_cells)}  redraw={redraw_row is not None}")

    mpath = os.path.join(args.out, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    filled = sum(len(s["cells"]) for s in manifest["sheets"])
    print(f"manifest: {mpath}")
    print(f"chars={filled} (target {len(charset)})  pages={n_pages}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
