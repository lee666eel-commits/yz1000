"""Two-page A4 sheet: the core 100 汉字 (chars-core100.txt) + Latin/digits/punctuation + free cells.

    python tools/make_template_core.py --out template-core
    python tools/render_sheet.py template-core/C1.html   (and C2.html)

Why (10-14, 林子策): 1000-char stacks put people off; the fine-tune test showed 50-100 real glyphs
already carry the hand, more makes it uniform. And a participant's L1 sheet showed what writers could not
tell from the old sheet -- half- or full-width punctuation? where in the cell? which side is an open
quote? where does a descender go? So this sheet answers those ON the paper:
  - every punctuation cell is labelled with its name (句号。/ 英文句点 .) and carries a faint example
    in the right position; Latin cells carry 4-line guides (cap / x-height / baseline / descender),
    with one faint example ('g') showing a descender.
  - no 米字格 in Latin/punct cells: a centred dot sat on the guide cross and was erased as residue.
  - guides/examples are printed so light (#f6cfcb, ~214 grey) that a black-and-white print still
    reads as paper to build_font.py (ink threshold 150), not only the red channel of a colour print.
Half-width ? ! ; : ( ) ' " are NOT written separately: merge_latin.py derives them from the
full-width glyphs, which in handwriting are the same shapes (fewer cells, no "which one?" question).
Cell positions/pitch are template-merged's (cell size 16.8 not 17.8, see CELL); build_font.py reads the
manifest, so it slices either version.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_template_merged import (CELL, CELL_INSET, COLS, GRID_RED, CROSS_RED, GRID_WIDTH_MM, GRID_X0,
                                  GRID_Y0, LOGO_COLS, LOGO_ROWS, MARK, MARKS_MM, PAGE_H, PAGE_W, PITCH,
                                  ROWS, cell_xy, data_uri, row_cols)

GUIDE = "#f6cfcb"   # light enough to be paper in a grey print, see docstring
# 2026-10-20: the 3.1mm red YaHei label was too small to read reliably -- writers copied the wrong character
# (found when finished fonts were checked glyph by glyph). Labels are now 5mm black 楷体; to make room the cell
# shrinks 17.8 -> 16.8mm while the pitch (and so cell positions and per-page capacity) stays the same.
CELL = 16.8
LAB_H = PITCH - CELL - 0.2   # label band above each cell, 0.2mm clear of the row above
LATIN = [chr(c) for c in range(0x41, 0x5B)] + [chr(c) for c in range(0x61, 0x7B)] + list("0123456789")
# (char, label); the faint in-cell example shows WHERE it goes, see example_svg
HALF = [(".", "英文句点"), (",", "英文逗号"), ("-", "连字号"),
        ("/", "斜线"), ("@", "@"), ("%", "%")]
FULL = [("，", "逗号"), ("。", "句号"), ("、", "顿号"), ("；", "分号"),
        ("：", "冒号"), ("？", "问号"), ("！", "叹号"),
        ("“", "左引号"), ("”", "右引号"), ("‘", "左单引号"), ("’", "右单引号"),
        ("（", "左括号"), ("）", "右括号"), ("《", "左书名号"), ("》", "右书名号"),
        ("—", "破折号"), ("…", "省略号")]
# Latin 4-line guide, fraction of cell height from the top
CAP, XH, BASE, DESC = 0.22, 0.44, 0.70, 0.88


def lay(chars, start_row=0):
    """chars -> [(row, col, item)] flowing through the writable columns."""
    out, r, it = [], start_row, iter(chars)
    while r < ROWS:
        for c in row_cols(r):
            try:
                out.append((r, c, next(it)))
            except StopIteration:
                return out, r
        r += 1
    raise SystemExit("does not fit on one page")


def example_svg(ch, latin_like):
    """faint example drawn with SVG <text>, whose y IS the baseline -- so a Latin/half-width example sits
    exactly on the printed baseline, and a full-width mark keeps the in-em position the font gives it
    (，。、 bottom-left, “ right-top ...), which is the convention we want the writer to copy."""
    if latin_like:   # cap height of YaHei ~0.72em -> size so caps span CAP..BASE
        size = (BASE - CAP) * 100 / 0.72
        x, y, anchor = 50, BASE * 100, "middle"
    else:            # full em box, CJK baseline ~0.88em down
        size, x, y, anchor = 92, 4, 84, "start"
    t = ch.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<svg class="ex" viewBox="0 0 100 100" preserveAspectRatio="none">'
            f'<text x="{x}" y="{y:.1f}" font-size="{size:.1f}" text-anchor="{anchor}" fill="{GUIDE}">{t}</text></svg>')


def cell_div(x, y, kind, ex=None):
    inner = ""
    if kind == "hanzi":
        inner = '<i class="h"></i><i class="v"></i><i class="d1"></i><i class="d2"></i>'
    elif kind in ("latin", "half"):
        inner = "".join(f'<i class="g{n}" style="top:{f * 100:.0f}%"></i>'
                        for n, f in (("c", CAP), ("x", XH), ("b", BASE), ("d", DESC)))
    if ex:
        inner += example_svg(ex, kind in ("latin", "half"))
    return (f'<div class="cell {kind}" style="left:{x:.2f}mm;top:{y:.2f}mm">{inner}</div>')


CSS = f"""
  @page {{ size: A4; margin: 0; }}
  html, body {{ margin: 0; padding: 0; overflow: hidden; }}
  body {{ width: {PAGE_W}mm; height: {PAGE_H - 0.4:.1f}mm; position: relative;
          font-family: "Microsoft YaHei","Noto Sans CJK SC",sans-serif; }}
  .mark {{ position: absolute; width: {MARK}mm; height: {MARK}mm; box-sizing: border-box;
           border: {MARK / 2}mm solid #000; }}
  .cell {{ position: absolute; width: {CELL}mm; height: {CELL}mm; box-sizing: border-box;
           border: 0.3mm solid {GRID_RED}; overflow: hidden; }}
  .cell i {{ position: absolute; display: block; }}
  .h {{ left: 0; top: 50%; width: 100%; border-top: 0.2mm dashed {CROSS_RED}; }}
  .v {{ top: 0; left: 50%; height: 100%; border-left: 0.2mm dashed {CROSS_RED}; }}
  .d1, .d2 {{ left: 0; top: 50%; width: 100%; border-top: 0.2mm dashed {CROSS_RED}; transform-origin: 50% 50%; }}
  .d1 {{ transform: rotate(45deg) scaleX(1.4143); }}
  .d2 {{ transform: rotate(-45deg) scaleX(1.4143); }}
  .gc, .gx, .gb, .gd {{ left: 0; width: 100%; height: 0; }}
  .gc, .gd {{ border-top: 0.2mm dashed {GUIDE}; }}
  .gx {{ border-top: 0.2mm dashed {GUIDE}; }}
  .gb {{ border-top: 0.35mm solid {GUIDE}; }}
  .ex {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; }}
  .lab {{ position: absolute; width: {CELL}mm; height: {LAB_H:.1f}mm; color: #111; font-size: 5mm;
          font-family: "KaiTi","STKaiti","楷体",serif; line-height: {LAB_H:.1f}mm; text-align: center; white-space: nowrap; }}
  .lab.small {{ font-size: 3.2mm; }}
  .hdr {{ position: absolute; left: 22mm; top: 18.4mm; width: 166mm; color: #555;  /* clear of the corner marks:
          text touching a mark merges with it and find_marks() falls back to the red logo tile (measured 10-14) */
          font-size: 3.1mm; line-height: 4.2mm; }}
  .hdr b {{ color: #222; }}
  .logo {{ position: absolute; object-fit: contain; }}
  .cell.free {{ border-color: #7a8fa6; }}
  .free i {{ border-color: rgba(122,143,166,0.30) !important; }}
  .note {{ position: absolute; left: {GRID_X0}mm; width: {GRID_WIDTH_MM}mm; color: #7a8fa6; font-size: 3.1mm; }}
  .line {{ position: absolute; left: {GRID_X0}mm; width: {GRID_WIDTH_MM}mm; height: 0; border-top: 0.25mm solid #999; }}
  .foot {{ position: absolute; left: {GRID_X0}mm; width: {GRID_WIDTH_MM}mm; top: {PAGE_H - 24.5:.1f}mm;
           color: #444; font-size: 2.7mm; text-align: center; }}
"""


def page(pid, no, n, hdr, body, logo_uri, foot=""):
    marks = "".join(f'<div class="mark" style="left:{x - MARK / 2:.2f}mm;top:{y - MARK / 2:.2f}mm"></div>'
                    for x, y in MARKS_MM)
    lx, ly = cell_xy(0, 0)
    logo = (f'<img class="logo" style="left:{lx:.2f}mm;top:{ly:.2f}mm;width:{LOGO_COLS * CELL:.2f}mm;'
            f'height:{LOGO_ROWS * PITCH - (PITCH - CELL):.2f}mm" src="{logo_uri}">')
    foot = f'<div class="foot">{foot}</div>' if foot else ""
    return (f'<meta charset="utf-8"><title>{pid}</title><style>{CSS}</style>'
            f'<div class="hdr">{pid} ({no}/{n}) &nbsp; {hdr}</div>{marks}{logo}{body}{foot}')


def cell_rec(r, c, ch):
    x, y = cell_xy(r, c)
    return {"row": r, "col": c, "char": ch, "cp": ord(ch), "cell_mm": [x, y, CELL, CELL],
            "ink_mm": [x + CELL_INSET, y + CELL_INSET, CELL - 2 * CELL_INSET, CELL - 2 * CELL_INSET]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--chars", default="chars-core100.txt")
    ap.add_argument("--logo", default="assets/logo.png")
    ap.add_argument("--email", default="lucaslimzzzce@gmail.com")
    ap.add_argument("--site", default="https://claude.ai/artifact/H7z5UYD9AtNKYRfByZrAfi")
    ap.add_argument("--font-link", default="", help="leave empty until a real package exists")
    a = ap.parse_args()

    hanzi = [c for c in open(a.chars, encoding="utf-8").read() if not c.isspace()]
    assert len(hanzi) == len(set(hanzi)) <= 106, len(hanzi)
    logo = data_uri(a.logo)
    os.makedirs(a.out, exist_ok=True)
    sheets = []

    # ---- C1: the core hanzi
    placed, _ = lay(hanzi)
    body, cells = [], []
    for r, c, ch in placed:
        x, y = cell_xy(r, c)
        body.append(f'<div class="lab" style="left:{x:.2f}mm;top:{y - LAB_H - 0.1:.2f}mm">{ch}</div>' + cell_div(x, y, "hanzi"))
        cells.append(cell_rec(r, c, ch))
    hdr1 = ("<b>黑色签字笔，照你平常写字的样子写</b>，不必写满格；写错了在格子旁边重写一个即可，别涂黑。<br>"
            "第一个字「永」包含了八种基本笔画（永字八法），请认真写。")
    open(f"{a.out}/C1.html", "w", encoding="utf-8").write(page("C1", 1, 2, hdr1, "".join(body), logo))
    sheets.append({"id": "C1", "html": "C1.html", "cells": cells, "free_cells": []})

    # ---- C2: Latin + digits + half-width + full-width punctuation, then free cells
    items = [(ch, ch) for ch in LATIN] + HALF + FULL
    placed, last = lay(items)
    body, cells = [], []
    for r, c, (ch, label) in placed:
        x, y = cell_xy(r, c)
        latin = ch in LATIN
        kind = "latin" if latin else ("half" if ord(ch) < 0x80 else "punct")
        lab = label if label == ch else f"{label} {ch}"
        body.append(f'<div class="lab{"" if latin else " small"}" style="left:{x:.2f}mm;top:{y - LAB_H - 0.1:.2f}mm">{lab}</div>')
        body.append(cell_div(x, y, kind, "g" if ch == "g" else (None if latin else ch)))
        cells.append(cell_rec(r, c, ch))
    free_row = last + 1
    free = []
    if free_row < ROWS:
        nx, ny = cell_xy(free_row, 0)
        body.append(f'<div class="note" style="top:{ny - 4.4:.2f}mm">自由字：随你发挥，想加什么字都行（例如你的名字）</div>')
        for c in row_cols(free_row):
            x, y = cell_xy(free_row, c)
            body.append(cell_div(x, y, "hanzi free"))
            free.append({"row": free_row, "col": c, "cell_mm": [x, y, CELL, CELL]})
        if free_row + 1 < ROWS:
            ty = GRID_Y0 + (free_row + 1) * PITCH
            body.append(f'<div class="note" style="top:{ty - 4.4:.2f}mm;color:#666">请用正楷把上面的自由字再写一遍，方便辨认：</div>')
            body += [f'<div class="line" style="top:{ty + 6 + k * 5.5:.2f}mm"></div>' for k in range(2)]
    hdr2 = ("<b>英文字母</b>照格内淡红线写：大写顶到最上线，小写 g j p q y 的尾巴伸到最下线（看「g」那格示范）。<br>"
            "<b>标点</b>格上写了名称，照格内淡红示范的<b>位置</b>写（例：句号、逗号靠左下，左引号靠右上）。")
    foot = f"{a.email} &nbsp;|&nbsp; {a.site} &nbsp;|&nbsp; " + (
        f"字体包：{a.font_link}" if a.font_link else "字体包制作中，完成后另行公布下载链接")
    open(f"{a.out}/C2.html", "w", encoding="utf-8").write(page("C2", 2, 2, hdr2, "".join(body), logo, foot))
    sheets.append({"id": "C2", "html": "C2.html", "cells": cells, "free_cells": free})

    man = {"page_mm": [PAGE_W, PAGE_H], "marks_mm": [list(m) for m in MARKS_MM], "mark_side_mm": MARK,
           "cell_mm": CELL, "grid": {"cols": COLS, "rows": ROWS, "x0": GRID_X0, "y0": GRID_Y0, "pitch_mm": PITCH},
           "grid_color": "red",
           "logo_block": {"rows": LOGO_ROWS, "cols": LOGO_COLS, "note": "top-left cells reserved for logo"},
           "sheets": sheets}
    json.dump(man, open(f"{a.out}/manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n1, n2 = len(sheets[0]["cells"]), len(sheets[1]["cells"])
    assert n1 == len(hanzi) and n2 == len(LATIN) + len(HALF) + len(FULL), (n1, n2)
    print(f"C1 {n1} hanzi | C2 {n2} latin/punct + {len(free)} free cells | manifest written (measured)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
