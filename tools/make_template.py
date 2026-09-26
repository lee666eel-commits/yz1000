"""Generate printable handwriting-sample sheets (HTML) + a JSON manifest.

The manifest is the ground truth for slicing: it records the registration-mark
centres and every cell rect in page millimetres, so build_font.py never has to
guess which cell holds which character.

Usage:
    python make_template.py --out D:\\handwriting-font\\template
    python make_template.py --chars-file mychars.txt --out ... --tier 1000
"""

import argparse
import json
import os

# --- page geometry, all millimetres --------------------------------------
PAGE_W, PAGE_H = 210.0, 297.0
MARK = 8.0                      # registration square, side length
MARK_INSET = 16.0               # centre distance from page edge
GRID_X0, GRID_Y0 = 16.0, 32.0
CELL = 17.8
COLS, ROWS = 10, 12
CELL_INSET = 0.6                # writing area is inset from the printed rule

# Marks in fixed TL, TR, BR, BL order -- build_font.py relies on this order.
MARKS_MM = [
    (MARK_INSET, MARK_INSET),
    (PAGE_W - MARK_INSET, MARK_INSET),
    (PAGE_W - MARK_INSET, PAGE_H - MARK_INSET),
    (MARK_INSET, PAGE_H - MARK_INSET),
]

# Pilot set: identity + punctuation first, then descending frequency.
# Truncated to --count, deduped, order preserved.
PILOT_CHARS = (
    "南华独中林子策学校教师生"
    "。，、？！："
    "的一是了我不人在他有这个上们来到时大地为说国年着就那和要出也得里后自"
    "以会可下而过天去能对小多然于心么之都好看起发当没成只如事把还用样道想"
    "作种开总从无情己面最但现前些所同日手又行意动方期头经长回位分爱老因很"
    "给名法间知世什两次使身高已进话常活正感文字写体"
)


def build_charset(chars, count):
    seen, out = set(), []
    for ch in chars:
        if ch.isspace() or ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    return out[:count] if count else out


# --- v2 (mofont style) ------------------------------------------------------
# Red rules, the way a Chinese 字帖 is printed, and no traceable character in
# the cell -- a printed 范字 gets copied, and what comes out is the printed
# face rather than his hand. The character to write is named in a gutter above
# its cell instead. The colour is not decoration either: red rules sit near
# white in the red channel, so the grid can be dropped at slicing time instead
# of being fought with a threshold. Registration marks stay BLACK, since that
# is what the corner detector looks for.
LABEL_MM = 4.4                  # gutter above each cell, holds the small label
# rgba alpha, not a lighter hex: the red-channel isolation in build_font.py
# reads these against white paper, so lower alpha = the printed pixel is
# already closer to white before strip_frame/guide_band ever runs. Visible
# to the eye while writing, weak enough that scan residue mostly disappears
# on its own instead of needing the post-hoc cleanup passes.
GRID_RED = "rgba(226,59,50,0.55)"
CROSS_RED = "rgba(226,59,50,0.30)"
WATERMARK_TEXT = "遗字千金 · 林子策手写字型工程 · 版权所有 未经授权不得外传/仿制"
SIGNATURE_PATH = (r"C:\Users\lee66\Desktop\000.通用素材与文件"
                   r"\签名与盖章\班导师林子策签名.png")


def signature_data_uri():
    """Base64 data: URI for the real signature PNG, or None if it's missing --
    the sheet must still print with the text watermark alone rather than crash."""
    import base64
    try:
        with open(SIGNATURE_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except OSError:
        return None


def watermark_html():
    uri = signature_data_uri()
    sig = (f'<img class="wm-sig" src="{uri}" alt="signature">' if uri else "")
    return f'<div class="wm">{sig}<span>{WATERMARK_TEXT}</span></div>'


def sheet_html_v2(sheet_id, cells, total_sheets, sheet_no, note):
    parts = []
    for x, y in MARKS_MM:
        parts.append(f'<div class="mark" style="left:{x - MARK / 2:.2f}mm;'
                     f'top:{y - MARK / 2:.2f}mm"></div>')
    for c in cells:
        x, y = c["cell_mm"][0], c["cell_mm"][1]
        parts.append(
            f'<div class="lab" style="left:{x:.2f}mm;top:{y - LABEL_MM:.2f}mm">'
            f'{c["char"]}</div>'
            f'<div class="cell" style="left:{x:.2f}mm;top:{y:.2f}mm">'
            f'<i class="h"></i><i class="v"></i>'
            f'<i class="d1"></i><i class="d2"></i></div>'
        )
    boxes = "\n".join(parts)
    return f"""<meta charset="utf-8">
<title>{sheet_id}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  /* overflow + a hair under the page height: Chrome spills a second, blank
     page if the body reaches exactly 297mm */
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
  /* 米字格 diagonals: a full-width rule through the middle, rotated about its
     own centre and stretched to the diagonal. The cell clips the ends. */
  .d1, .d2 {{ left: 0; top: 50%; width: 100%;
              border-top: 0.2mm dashed {CROSS_RED};
              transform-origin: 50% 50%; }}
  .d1 {{ transform: rotate(45deg) scaleX(1.4143); }}
  .d2 {{ transform: rotate(-45deg) scaleX(1.4143); }}
  .lab {{ position: absolute; width: {CELL}mm; height: {LABEL_MM}mm;
          color: {GRID_RED}; font-size: 3.1mm; line-height: {LABEL_MM}mm;
          text-align: center; }}
  .hdr {{ position: absolute; left: {GRID_X0}mm; top: 20mm;
          width: {COLS * CELL}mm; color: #666; font-size: 3.2mm;
          display: flex; justify-content: space-between; }}
  .wm {{ position: absolute; left: 0; bottom: 3mm; width: {PAGE_W}mm;
         display: flex; align-items: center; justify-content: center; gap: 2mm;
         color: #b0b0b0; font-size: 2.6mm;
         font-family: sans-serif; letter-spacing: 0.3mm; }}
  .wm-sig {{ height: 6mm; width: auto; opacity: 0.55; }}
</style>
<div class="hdr"><span>{sheet_id} &nbsp; ({sheet_no}/{total_sheets})</span>
<span>{note}</span></div>
{boxes}
{watermark_html()}
"""


def sheet_html(sheet_id, cells, tint, total_sheets, sheet_no):
    """One A4 page. Marks and rules use borders/text, never background-color,
    so the sheet prints correctly even with Chrome's 'Background graphics' off."""
    parts = []
    for x, y in MARKS_MM:
        parts.append(
            f'<div class="mark" style="left:{x - MARK / 2:.2f}mm;'
            f'top:{y - MARK / 2:.2f}mm"></div>'
        )
    for c in cells:
        x, y = c["cell_mm"][0], c["cell_mm"][1]
        parts.append(
            f'<div class="cell" style="left:{x:.2f}mm;top:{y:.2f}mm">'
            f'<span class="guide">{c["char"]}</span></div>'
        )
    boxes = "\n".join(parts)
    return f"""<meta charset="utf-8">
<title>{sheet_id}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{ width: {PAGE_W}mm; height: {PAGE_H}mm; position: relative;
          font-family: "KaiTi","Kaiti SC","STKaiti","SimSun",serif; }}
  .mark {{ position: absolute; width: {MARK}mm; height: {MARK}mm;
           box-sizing: border-box; border: {MARK / 2}mm solid #000; }}
  .cell {{ position: absolute; width: {CELL}mm; height: {CELL}mm;
           box-sizing: border-box; border: 0.25mm solid #b4b4b4;
           display: flex; align-items: center; justify-content: center; }}
  .guide {{ color: {tint}; font-size: {CELL * 0.78:.2f}mm; line-height: 1; }}
  .hdr {{ position: absolute; left: {GRID_X0}mm; top: 22mm;
          width: {COLS * CELL}mm; color: #808080; font-size: 3.4mm;
          font-family: sans-serif; display: flex;
          justify-content: space-between; }}
  .wm {{ position: absolute; left: 0; bottom: 4mm; width: {PAGE_W}mm;
         display: flex; align-items: center; justify-content: center; gap: 2mm;
         color: #b0b0b0; font-size: 2.6mm;
         font-family: sans-serif; letter-spacing: 0.3mm; }}
  .wm-sig {{ height: 6mm; width: auto; opacity: 0.55; }}
</style>
<div class="hdr"><span>{sheet_id} &nbsp; ({sheet_no}/{total_sheets})</span>
<span>黑色签字笔 / 黑色细字笔，压过灰字，勿用铅笔或浅色笔</span></div>
{boxes}
{watermark_html()}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--chars-file", help="UTF-8 file of characters to include")
    ap.add_argument("--count", type=int, default=100,
                    help="max characters (0 = all). Default 100 = pilot.")
    ap.add_argument("--tint", default="#d0d0d0",
                    help="guide-character grey. Lighten if it survives thresholding.")
    ap.add_argument("--prefix", default="S", help="sheet id prefix")
    ap.add_argument("--style", choices=("guide", "mofont"), default="guide",
                    help="guide = the original grey traceable character in the "
                         "cell. mofont = red 字帖 rules, no traceable glyph, "
                         "the character named in a gutter above its cell.")
    ap.add_argument("--note",
                    default="黑色签字笔或钢笔，照你平常的写法写，不必写满格",
                    help="the line printed at the top of the sheet")
    args = ap.parse_args()

    if args.chars_file:
        with open(args.chars_file, encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = PILOT_CHARS
    charset = build_charset(raw, args.count)

    # the label gutter makes each row taller, so fewer rows fit on the page
    pitch = CELL + LABEL_MM if args.style == "mofont" else CELL
    rows = ROWS if args.style == "guide" else int((PAGE_H - GRID_Y0 - 20) / pitch)
    per_sheet = COLS * rows
    n_sheets = max(1, -(-len(charset) // per_sheet))
    os.makedirs(args.out, exist_ok=True)

    manifest = {
        "page_mm": [PAGE_W, PAGE_H],
        "marks_mm": [list(m) for m in MARKS_MM],
        "mark_side_mm": MARK,
        "cell_mm": CELL,
        "grid": {"cols": COLS, "rows": rows,
                 "x0": GRID_X0, "y0": GRID_Y0, "pitch_mm": pitch},
        # slicing can drop the printed grid via the red channel instead of
        # relying on a threshold; absent on v1 sheets, whose rules are grey
        "grid_color": "red" if args.style == "mofont" else "grey",
        "sheets": [],
    }

    i = 0
    for s in range(n_sheets):
        sid = f"{args.prefix}{s + 1}"
        cells = []
        for r in range(rows):
            for c in range(COLS):
                if i >= len(charset):
                    break
                x = GRID_X0 + c * CELL
                y = GRID_Y0 + r * pitch
                ch = charset[i]
                cells.append({
                    "row": r, "col": c, "char": ch, "cp": ord(ch),
                    "cell_mm": [x, y, CELL, CELL],
                    "ink_mm": [x + CELL_INSET, y + CELL_INSET,
                               CELL - 2 * CELL_INSET, CELL - 2 * CELL_INSET],
                })
                i += 1
        html = (sheet_html_v2(sid, cells, n_sheets, s + 1, args.note)
                if args.style == "mofont"
                else sheet_html(sid, cells, args.tint, n_sheets, s + 1))
        path = os.path.join(args.out, f"{sid}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        manifest["sheets"].append({"id": sid, "html": f"{sid}.html",
                                   "cells": cells})
        print(f"{path}  {len(cells)} cells")

    mpath = os.path.join(args.out, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    filled = sum(len(s["cells"]) for s in manifest["sheets"])
    blanks = n_sheets * per_sheet - filled
    print(f"manifest: {mpath}")
    print(f"chars={filled}  sheets={n_sheets}  blank cells={blanks}")


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
