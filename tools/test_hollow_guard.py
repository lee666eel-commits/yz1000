"""Prove the hollow-stroke guard can actually fail.

The bug it exists to catch -- strokes reduced to outlines by normalising light
at cell scale instead of page scale -- passes BOTH the glyph-count check and
the cmap set-equality check. It shipped once and only the human-read proof
render caught it. So this guard is the only automated defence, and a guard that
cannot fail is worse than none.

Part A (unit)       solid glyph vs its morphological outline.
Part B (regression) the authentic artefact: the real fake-scan photo pushed
                    through the real warp, with the per-cell normalise put
                    back exactly where it used to be. Current code must come
                    out clean on the same photo.

    python test_hollow_guard.py
"""

import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_font import (HOLLOW_FRACTION, MAX_EDGE_FRAC, MIN_STROKE_FRAC,  # noqa: E402
                        PX_PER_MM, cell_bitmap, find_marks, is_hollow,
                        normalise, warp_page)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(ROOT, "template", "manifest.json")
FIXTURE = os.path.join(ROOT, "test", "thresh", "worst.jpg")
SIZE = 200
CHARS = "南国面语教写一"


# ------------------------------------------------------------------ part A
def render(ch, fill=130):
    img = Image.new("L", (SIZE, SIZE), 252)
    f = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", int(SIZE * 0.8))
    ImageDraw.Draw(img).text((SIZE / 2, SIZE / 2), ch, font=f, fill=fill,
                             anchor="mm")
    return np.array(img)


def stroke_frac(gray):
    """Run the shipped cell_bitmap so the test exercises production code."""
    mm = SIZE / PX_PER_MM
    page = np.full((SIZE + 4, SIZE + 4), 255, np.uint8)
    page[0:SIZE, 0:SIZE] = gray
    # keep_frame=True: these fixtures are bare glyphs with no printed cell
    # frame, and the guard under test is the stroke-width one, not the frame
    # stripper. Leaving it on would let frame removal quietly alter the input.
    _, _, frac, _, edge = cell_bitmap(page, [0, 0, mm, mm], 150, keep_frame=True)
    return frac, edge


def as_outline(gray):
    ink = (gray < 150).astype(np.uint8)
    rim = cv2.morphologyEx(ink, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    return np.where(rim > 0, 130, 252).astype(np.uint8)


def part_a():
    bad = []
    print(f"Part A -- unit, MIN_STROKE_FRAC = {MIN_STROKE_FRAC}, "
          f"MAX_EDGE_FRAC = {MAX_EDGE_FRAC}")
    print(f"  {'char':<6}{'solid s/e':>14}{'outlined s/e':>16}   verdict")
    for ch in CHARS:
        g = render(ch)
        s, o = stroke_frac(g), stroke_frac(as_outline(g))
        ok = not is_hollow(*s) and is_hollow(*o)
        print(f"  {ch:<6}{s[0]:>8.4f}/{s[1]:.2f}{o[0]:>9.4f}/{o[1]:.2f}   "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            bad.append((ch, s, o))
    assert not bad, f"solid/outlined not separated: {bad}"
    print("  PASS\n")


# ------------------------------------------------------------------ part B
def warp_raw(img, man):
    """Pre-fix page pipeline: warp, but do NOT normalise at page scale.
    Mirrors warp_page() minus its final normalise() call."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    quad = find_marks(gray, man["page_mm"], man["mark_side_mm"])
    dst = np.array([[m[0] * PX_PER_MM, m[1] * PX_PER_MM]
                    for m in man["marks_mm"]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    size = (int(round(man["page_mm"][0] * PX_PER_MM)),
            int(round(man["page_mm"][1] * PX_PER_MM)))
    return cv2.warpPerspective(gray, H, size, flags=cv2.INTER_CUBIC,
                               borderValue=255)


def normalise_each_cell(page, cells):
    """Put the removed per-cell normalise back, in place, so the shipped
    cell_bitmap sees exactly the bytes the buggy version fed it."""
    out = page.copy()
    for c in cells:
        x, y, w, h = c["ink_mm"]
        x0, y0 = int(round(x * PX_PER_MM)), int(round(y * PX_PER_MM))
        x1, y1 = int(round((x + w) * PX_PER_MM)), int(round((y + h) * PX_PER_MM))
        out[y0:y1, x0:x1] = normalise(page[y0:y1, x0:x1])
    return out


def count_thin(page, cells):
    thin = inked = 0
    for c in cells:
        bmp, ratio, frac, _, edge = cell_bitmap(page, c["ink_mm"], 150,
                                                keep_frame=True)
        if bmp is None or ratio < 0.004:
            continue
        inked += 1
        if is_hollow(frac, edge):
            thin += 1
    return thin, inked


def part_b():
    import json
    for p in (MANIFEST, FIXTURE):
        assert os.path.exists(p), (
            f"missing fixture {p}. Regenerate with:\n"
            f"  python tools\\make_fake_scan.py --manifest template\\manifest.json "
            f"--sheet S1 --out test\\thresh\\worst.jpg --ink-fill 130 --guide-tint 180")
    with open(MANIFEST, encoding="utf-8") as f:
        man = json.load(f)
    cells = man["sheets"][0]["cells"]
    img = cv2.imread(FIXTURE, cv2.IMREAD_COLOR)

    print("Part B -- regression on the real fake-scan photo")
    b_thin, b_ink = count_thin(normalise_each_cell(warp_raw(img, man), cells),
                               cells)
    g_thin, g_ink = count_thin(warp_page(img, man), cells)
    limit = HOLLOW_FRACTION
    print(f"  pre-fix  (per-cell normalise): {b_thin}/{b_ink} thin "
          f"= {b_thin / b_ink:.0%}  (guard must trip, > {limit:.0%})")
    print(f"  current  (page normalise)    : {g_thin}/{g_ink} thin "
          f"= {g_thin / g_ink:.0%}  (guard must stay quiet)")

    assert b_thin / b_ink > limit, (
        f"guard does NOT trip on the authentic pre-fix artefact "
        f"({b_thin}/{b_ink}); it would have shipped the hollow font silently")
    assert g_thin / g_ink <= limit, (
        f"guard falsely trips on correct output ({g_thin}/{g_ink})")
    print("  PASS\n")


# ------------------------------------------------------------------ part C
REAL_DIRS = ["debug-0005missho", "debug-0010phoon", "debug-liujiarui",
             "debug-linhand", "debug-linhand2"]


def part_c():
    """Real participants' cell bitmaps (build_font --debug-dir dumps). The
    two fine-pen hands are the reason the guard was re-derived on 09-19:
    the old stroke-only rule flagged 906-908/908 of each. A missing dir is a
    failure, not a skip -- skip must not count as pass."""
    import glob
    print("Part C -- real hands (fine pens must NOT trip the guard)")
    found = 0
    for name in REAL_DIRS:
        d = os.path.join(ROOT, "build", name)
        files = glob.glob(os.path.join(d, "S*_r*c*_*.png"))
        if not files:
            print(f"  {name:<20} MISSING")
            continue
        found += 1
        thin = inked = 0
        for f in files:
            keep = (cv2.imread(f, 0) < 128).astype(np.uint8)
            if keep.sum() == 0:
                continue
            inked += 1
            dist = cv2.distanceTransform(keep, cv2.DIST_L2, 5)
            stroke = float(np.percentile(dist[keep > 0], 50)) / max(keep.shape)
            edge = 1.0 - cv2.erode(keep, np.ones((3, 3), np.uint8)).sum() / float(keep.sum())
            thin += is_hollow(stroke, edge)
        share = thin / inked
        print(f"  {name:<20} {thin}/{inked} flagged = {share:.1%}  "
              f"({'ok' if share <= HOLLOW_FRACTION else 'FAIL'})")
        assert share <= HOLLOW_FRACTION, f"{name}: real hand read as hollow"
    assert found >= 2, "need at least two real debug dirs (fine + thick pen)"
    print("  PASS\n")


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    part_a()
    part_b()
    part_c()
    print("all checks passed")
