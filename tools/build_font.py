"""Turn photographed/scanned handwriting sheets into a real .ttf.

Pipeline: locate the 4 registration marks -> homography to a canonical page
raster -> slice cells straight from the manifest geometry (never by contour
detection, so the char<->cell pairing is structural, not guessed) ->
background-normalise + threshold -> potrace -> cubic->quadratic -> glyf.

Verification is a set-equality assertion between "cells that had ink" and
"codepoints in the finished cmap", plus a rendered proof PNG a human reads.

Usage:
    python build_font.py --manifest template/manifest.json \\
        --sheet S1=scans/S1.jpg --out build/MyHand.ttf --family "My Hand"
"""

import argparse
import json
import os
import sys

import cv2
import numpy as np
import potrace
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

PX_PER_MM = 12.0          # canonical page raster resolution
UPM = 1000                # font units per em
ASCENT, DESCENT = 880, -120
BLANK_INK_RATIO = 0.004   # below this fraction of dark pixels -> cell is empty
MIN_BLOB_PX = 12          # drop specks smaller than this (printer dither, dust)
MIN_STROKE_FRAC = 0.0075  # thinnest believable stroke half-width, as a
                          # fraction of cell size. Median distance-transform
                          # half-width is quantised to whole px on a 199px
                          # cell: 1px = 0.005, 2px = 0.010, 3px = 0.015. The
                          # authentic artefact (per-cell normalise, see
                          # test_hollow_guard Part B) measures 1px; a fine
                          # gel/ballpoint hand (0010Phoon, 0005MissHo, 908
                          # cells each, 09-19) measures 2px. The old 0.012 sat
                          # between 2px and 3px and flagged every thin-pen
                          # participant as hollow. 0.0075 sits between 1px and
                          # 2px, i.e. mid-step, so quantisation cannot flip it.
MAX_EDGE_FRAC = 0.60      # ...second, independent hollow tell: share of ink
                          # that vanishes under one 3x3 erosion (~2/width).
                          # Measured 09-19: hollow fixture 0.47-0.85, synthetic
                          # outline 0.99-1.0, thin pens max 0.56, thick 0.33.
                          # Catches a 2px outline (half-width 0.010, which the
                          # stroke test alone would pass). ponytail: 0.56 vs
                          # 0.60 is a thin margin for a still-finer pen; raise
                          # PX_PER_MM (recalibrating every px constant) if one
                          # ever trips it.
HOLLOW_FRACTION = 0.10    # this share of cells too thin -> fail the build

PROOF_LINES = [
    "南华独中，是我的学校。",
    "我们的老师说，中文字很美。",
    "这个字是我自己写出来的！",
]


# --------------------------------------------------------------- page finding
def find_marks(gray, page_mm, mark_side_mm):
    """Return the 4 registration-mark centres in TL,TR,BR,BL order (px)."""
    h, w = gray.shape
    norm = normalise(gray)
    _, bw = cv2.threshold(norm, 110, 255, cv2.THRESH_BINARY_INV)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Expected mark area as a fraction of the page; the photo may be cropped
    # tight or loose, so allow a wide band and rely on squareness + fill.
    frac = (mark_side_mm ** 2) / (page_mm[0] * page_mm[1])
    page_px = float(w * h)
    cands = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 40:
            continue
        if not (0.15 * frac * page_px < area < 8.0 * frac * page_px):
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        if cw == 0 or ch == 0:
            continue
        ar = cw / float(ch)
        fill = area / float(cw * ch)
        if not (0.7 < ar < 1.4 and fill > 0.80):
            continue
        cands.append((area, x + cw / 2.0, y + ch / 2.0))

    if len(cands) < 4:
        raise SystemExit(
            f"registration marks: found {len(cands)} square candidates, need 4. "
            "Re-shoot the sheet with all four corner squares fully in frame, "
            "flat, and evenly lit."
        )

    # The 4 marks are the extreme corners among the candidates.
    pts = np.array([[cx, cy] for _, cx, cy in cands], dtype=np.float64)
    s, d = pts[:, 0] + pts[:, 1], pts[:, 0] - pts[:, 1]
    idx = [int(np.argmin(s)), int(np.argmax(d)),
           int(np.argmax(s)), int(np.argmin(d))]
    if len(set(idx)) != 4:
        raise SystemExit("registration marks: corner assignment ambiguous; "
                         "photo is probably rotated more than ~40 degrees.")
    quad = pts[idx]

    # Sanity: the mark quad's aspect must match the page's mark rectangle.
    exp = ((page_mm[1] - 2 * 16.0) / (page_mm[0] - 2 * 16.0))
    got_w = np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])
    got_h = np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])
    got = got_h / max(got_w, 1e-6)
    if not (0.72 * exp < got < 1.28 * exp):
        raise SystemExit(
            f"registration marks: quad aspect {got:.3f} vs expected {exp:.3f}. "
            "Wrong sheet, upside-down photo, or a mark was mistaken for ink."
        )
    return quad


def normalise(gray):
    """Flatten uneven lighting: divide by a heavily blurred copy of itself.

    MUST be applied at page scale, never per cell. The blur radius has to be
    far larger than a pen stroke is wide; on a ~200px cell crop the radius
    lands near the stroke width and the division hollows the strokes out into
    thin outlines -- which still passes glyph-count and cmap checks, so the
    only thing that catches it is the proof render (or hole_count below).
    """
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=max(gray.shape) / 30.0)
    bg = np.clip(bg, 1, 255).astype(np.float32)
    out = gray.astype(np.float32) / bg * 200.0
    return np.clip(out, 0, 255).astype(np.uint8)


def to_ink(img, manifest):
    """Single channel where the printed grid is faint and the writing is not.

    A red 字帖 rule is not a light artefact in greyscale -- #e23b32 converts to
    about 108, DARKER than the grey rules of the v1 sheet -- so a red sheet read
    the ordinary way would leak more grid into the crops, not less. Read the red
    channel instead: red ink sits near white there, black ink does not. Mark
    detection keeps using greyscale, because the marks are black either way.
    """
    if img.ndim != 3:
        return img
    if manifest.get("grid_color") == "red":
        return img[:, :, 2]                    # OpenCV is BGR
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def warp_page(img, manifest):
    page_mm = manifest["page_mm"]
    mono = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gray = to_ink(img, manifest)
    quad = find_marks(mono, page_mm, manifest["mark_side_mm"])
    dst = np.array([[m[0] * PX_PER_MM, m[1] * PX_PER_MM]
                    for m in manifest["marks_mm"]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    size = (int(round(page_mm[0] * PX_PER_MM)), int(round(page_mm[1] * PX_PER_MM)))
    page = cv2.warpPerspective(gray, H, size, flags=cv2.INTER_CUBIC,
                               borderValue=255)
    return normalise(page)          # page scale only -- see normalise() docstring


EDGE_BAND_FRAC = 0.06     # a row/col this close to the crop edge may be the
                          # printed cell frame rather than handwriting
EDGE_LINE_FILL = 0.70     # ...and this full means it IS the frame
FRAME_THIN_PX = 8         # frame fragment: never thicker than this (a real pen
                          # stroke measures ~5px full width on a 199px cell, so
                          # this alone is NOT enough -- see is_frame_fragment)
FRAME_LONG_FRAC = 0.5     # ...spans at least half the cell...
GUIDE_BAND_PX = 6         # a blob must lie within this many px of a 米字格
                          # centre guide line (horiz/vert/2 diagonals) to be
                          # eligible as guide residue -- see is_guide_fragment
GUIDE_MAX_AREA = 40       # ...and be no bigger than this. A blanket erase of
                          # the guide band was tried and measured 574-638 of
                          # 908 real cells (LiuJiaRui, 09-07) going hollow --
                          # Chinese strokes routinely run horizontal/vertical/
                          # 45deg, i.e. exactly along these lines, so cutting
                          # the band unconditionally guts real ink. Gating on
                          # area first is what makes this safe: a printed
                          # guide dash is a few px long, nowhere near the size
                          # of an actual stroke segment, so no real ink blob
                          # can ever be small enough to qualify.
GUIDE_COVER_FRAC = 0.6    # ...and be almost entirely inside the band, not
                          # just clipping it in passing


def is_frame_fragment(st, shape):
    """True for an isolated thin line hugging one edge of the cell.

    Catches the slanted cell-frame segments that strip_frame() misses: the
    warp is never perfectly square, so a vertical frame line clips through
    only part of the crop, and it arrives BROKEN -- measured on 里, the
    right-hand frame survived as several short blobs, none of them half a
    cell tall. So length is not usable as the test.

    What is usable: the blob lies ENTIRELY inside a thin band at the very
    edge, and is thinner than a pen stroke across the band's axis. A real
    stroke of the character either reaches inward past the band or is joined
    to the rest of the character (one blob), so neither form qualifies.
    """
    h, w = shape
    x, y = st[cv2.CC_STAT_LEFT], st[cv2.CC_STAT_TOP]
    bw_, bh_ = st[cv2.CC_STAT_WIDTH], st[cv2.CC_STAT_HEIGHT]
    band_r, band_c = max(1, int(h * EDGE_BAND_FRAC)), max(1, int(w * EDGE_BAND_FRAC))
    vertical = bw_ <= FRAME_THIN_PX and (x + bw_ <= band_c or x >= w - band_c)
    horizontal = bh_ <= FRAME_THIN_PX and (y + bh_ <= band_r or y >= h - band_r)
    return vertical or horizontal


def strip_frame(bw):
    """Erase printed cell-frame lines that leaked into the crop.

    The manifest already insets the ink box 0.6mm inside the frame, but the
    page-scale warp leaves a few px of residual offset, so on the first real
    photo 22 of 100 cells still caught the line above them (top 22, bottom 2,
    sides 0 -- the offset is systematic, not random).

    Only rows/cols inside a thin edge band are eligible, so a genuine
    horizontal stroke in the middle of the cell (一 二 三) is never touched.
    """
    h, w = bw.shape
    band_r, band_c = max(1, int(h * EDGE_BAND_FRAC)), max(1, int(w * EDGE_BAND_FRAC))
    for r in list(range(band_r)) + list(range(h - band_r, h)):
        if bw[r, :].mean() > EDGE_LINE_FILL:
            bw[r, :] = 0
    for c in list(range(band_c)) + list(range(w - band_c, w)):
        if bw[:, c].mean() > EDGE_LINE_FILL:
            bw[:, c] = 0
    return bw


def guide_band(shape, band_px=GUIDE_BAND_PX):
    """Boolean mask: True within band_px of a 米字格 centre guide line.

    The four guide lines (horizontal, vertical, both diagonals) all pass
    through the cell centre, printed red like the outer frame. red-channel
    reading in to_ink() washes out the solid parts, but the dashed rule's
    anti-aliased edges survive thresholding as small broken dashes strung
    along the line -- measured on a real photo (LiuJiaRui, 09-07): visible
    as faint dashes scattered near several characters in `_proof.png`.
    """
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    diag = max(float(np.hypot(cx, cy)), 1e-6)
    d_h = np.abs(yy - cy)
    d_v = np.abs(xx - cx)
    d_d1 = np.abs((yy - cy) * cx - (xx - cx) * cy) / diag
    d_d2 = np.abs((yy - cy) * cx + (xx - cx) * cy) / diag
    return (d_h <= band_px) | (d_v <= band_px) | (d_d1 <= band_px) | (d_d2 <= band_px)


def is_guide_fragment(mask_i, band, area):
    """True for a small blob that sits almost entirely on a guide line.

    Area-gated, not just position-gated: a first version erased the whole
    guide band unconditionally and measured 574-638 of 908 real LiuJiaRui
    cells going hollow, because Chinese strokes routinely run horizontal,
    vertical, or at 45 degrees -- exactly along these lines -- so cutting
    the band blind guts real ink wherever a stroke happens to follow it.
    A printed guide dash is only a few px across; no real stroke segment is
    ever that small, so gating on area first means this can never touch
    genuine handwriting no matter how it's oriented.
    """
    if area > GUIDE_MAX_AREA:
        return False
    covered = float((mask_i & band).sum()) / area
    return covered >= GUIDE_COVER_FRAC


# ------------------------------------------------------------------- ink -> bmp
def cell_bitmap(page, ink_mm, thresh, keep_frame=False):
    x, y, w, h = ink_mm
    x0, y0 = int(round(x * PX_PER_MM)), int(round(y * PX_PER_MM))
    x1, y1 = int(round((x + w) * PX_PER_MM)), int(round((y + h) * PX_PER_MM))
    crop = page[y0:y1, x0:x1]        # page is already light-normalised
    if crop.size == 0:
        return None, 0.0, 0, 0, 0.0
    bw = (crop < thresh).astype(np.uint8)
    if not keep_frame:
        bw = strip_frame(bw)

    # Kill specks: printed guide-glyph residue, dust, paper texture.
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    band = None if keep_frame else guide_band(bw.shape)
    keep = np.zeros_like(bw)
    frags = 0
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < MIN_BLOB_PX:
            continue
        if not keep_frame:
            if is_frame_fragment(stats[i], bw.shape):
                frags += 1
                continue
            if is_guide_fragment(lab == i, band, area):
                frags += 1
                continue
        keep[lab == i] = 1
    ratio = keep.sum() / float(keep.size)

    # Hollow/over-thinned stroke detector, measured as stroke half-width via
    # the distance transform. Counting enclosed background regions does NOT
    # work here: real hollowing is patchy, so the background leaks through the
    # gaps and the region count stays deceptively low (measured: solid 1-6 vs
    # outlined 4-7, no separation). Stroke width separates them cleanly and is
    # immune to those gaps. Needed because a hollowed sheet still yields a
    # perfectly correct glyph count and cmap -- see test_hollow_guard.py.
    if keep.sum() == 0:
        return keep, ratio, 0.0, frags, 0.0
    dist = cv2.distanceTransform(keep, cv2.DIST_L2, 5)
    # Median, not p95. Measured on the hollow-vs-correct fixture pair, per cell,
    # as a fraction of cell size:
    #     p50   hollow max 0.0100 | correct min 0.0141   <- separates
    #     p95   hollow max 0.0201 | correct min 0.0250   <- both above 0.012
    # p95 reads the thickest 5% of the ink, so a patchy hollow glyph with a few
    # surviving solid blobs scores clean; the median reads the typical stroke.
    half = float(np.percentile(dist[keep > 0], 50))
    edge = 1.0 - cv2.erode(keep, np.ones((3, 3), np.uint8)).sum() / float(keep.sum())
    return keep, ratio, half / max(keep.shape), frags, edge


def is_hollow(stroke, edge, min_stroke=MIN_STROKE_FRAC):
    """Either tell fires -> the cell is outlines, not solid ink."""
    return stroke < min_stroke or edge > MAX_EDGE_FRAC


def trace_to_glyph(bmp, reverse):
    """potrace the bitmap, emit a TrueType glyph in font units."""
    h, w = bmp.shape
    # potracer traces the False region, so ink must be fed in inverted --
    # verified: a solid True square yields the whole frame plus a hole, while
    # the inverted array yields the square alone, outer contour positive-area
    # in image coords, i.e. clockwise once y is flipped, which is what glyf wants.
    path = potrace.Bitmap(~bmp.astype(bool)).trace(
        turdsize=2, alphamax=1.0, opttolerance=0.2)

    pen = TTGlyphPen(None)
    qpen = Cu2QuPen(pen, max_err=1.0, reverse_direction=reverse)

    def P(p):
        px, py = (p.x, p.y) if hasattr(p, "x") else (p[0], p[1])
        # bitmap is y-down and inset-normalised; map the cell frame (NOT the
        # ink bbox) onto the em box, so per-character size/position variance
        # -- the thing that makes it read as handwriting -- survives.
        return (px / w * UPM, ASCENT - (py / h) * UPM)

    n = 0
    for curve in path:
        qpen.moveTo(P(curve.start_point))
        for seg in curve.segments:
            if seg.is_corner:
                qpen.lineTo(P(seg.c))
                qpen.lineTo(P(seg.end_point))
            else:
                qpen.curveTo(P(seg.c1), P(seg.c2), P(seg.end_point))
        qpen.closePath()
        n += 1
    if n == 0:
        return None
    return pen.glyph()


# ----------------------------------------------------------------- font build
def build_ttf(glyphs, family, style, out):
    names = sorted(glyphs)
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder([".notdef"] + names)
    fb.setupCharacterMap({int(n[3:], 16): n for n in names})

    empty = TTGlyphPen(None).glyph()
    gset = {".notdef": empty}
    gset.update(glyphs)
    fb.setupGlyf(gset)

    # CJK is monospaced full-width: every advance is one em. Layout is then
    # correct for free -- no kerning, no per-glyph width tuning.
    fb.setupHorizontalMetrics({n: (UPM, 0) for n in gset})
    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
    ps = f"{family}-{style}".replace(" ", "")
    fb.setupNameTable({
        "familyName": family, "styleName": style,
        "uniqueFontIdentifier": f"{family} {style} 1.0",
        "fullName": f"{family} {style}", "version": "1.0",
        "psName": ps,
    })
    fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=DESCENT, sTypoLineGap=0,
                usWinAscent=ASCENT, usWinDescent=-DESCENT,
                achVendID="HAND", fsType=0)
    fb.setupPost()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fb.save(out)
    return fb.font


def render_proof(ttf, chars, png):
    from PIL import Image, ImageDraw, ImageFont
    have = set(chars)
    lines = [l for l in PROOF_LINES if set(l) <= have]
    dropped = [l for l in PROOF_LINES if set(l) > have]

    size, pad, cols = 64, 24, 12
    grid = [chars[i:i + cols] for i in range(0, len(chars), cols)]
    rows = len(lines) + 1 + len(grid)
    W = pad * 2 + cols * (size + 8)
    Him = pad * 2 + rows * (size + 18)
    img = Image.new("L", (W, Him), 255)
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype(ttf, size)

    y = pad
    for l in lines:
        dr.text((pad, y), l, font=f, fill=0)
        y += size + 18
    y += 18
    for row in grid:
        dr.text((pad, y), "".join(row), font=f, fill=0)
        y += size + 18
    os.makedirs(os.path.dirname(os.path.abspath(png)), exist_ok=True)
    img.save(png)
    return lines, dropped


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sheet", action="append", required=True,
                    metavar="ID=PATH", help="repeat per sheet, e.g. -S S1=a.jpg")
    ap.add_argument("--out", required=True, help="output .ttf path")
    ap.add_argument("--family", default="Handwriting Pilot")
    ap.add_argument("--style", default="Regular")
    ap.add_argument("--ink-thresh", type=int, default=150,
                    help="0-255 on the light-normalised crop; raise if strokes "
                         "break up, lower if printed guide grey survives")
    ap.add_argument("--min-stroke", type=float, default=MIN_STROKE_FRAC,
                    help="thinnest believable stroke half-width as a fraction "
                         "of cell size. Lower it only if a genuinely very fine "
                         "pen is being wrongly reported hollow -- check the "
                         "proof render before you touch it")
    ap.add_argument("--reverse-contours", action="store_true",
                    help="use if the proof render shows filled-in counters")
    ap.add_argument("--keep-frame", action="store_true",
                    help="do not erase printed cell-frame lines that leaked "
                         "into a cell (escape hatch; see strip_frame)")
    ap.add_argument("--debug-dir", help="dump warped pages and cell bitmaps")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        man = json.load(f)
    sheets = {s["id"]: s for s in man["sheets"]}

    given = {}
    for spec in args.sheet:
        if "=" not in spec:
            raise SystemExit(f"--sheet needs ID=PATH, got {spec!r}")
        sid, path = spec.split("=", 1)
        if sid not in sheets:
            raise SystemExit(f"sheet id {sid!r} not in manifest "
                             f"({', '.join(sheets)})")
        given[sid] = path

    if args.debug_dir:
        os.makedirs(args.debug_dir, exist_ok=True)

    glyphs, inked, blank, failed, hollow, framed = {}, [], [], [], [], []
    for sid, path in given.items():
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise SystemExit(f"cannot read image: {path}")
        page = warp_page(img, man)
        if args.debug_dir:
            cv2.imwrite(os.path.join(args.debug_dir, f"{sid}_warped.png"), page)

        for c in sheets[sid]["cells"]:
            bmp, ratio, stroke, frags, edge = cell_bitmap(page, c["ink_mm"],
                                                          args.ink_thresh,
                                                          args.keep_frame)
            if frags:
                framed.append((c["char"], frags))
            if bmp is None or ratio < BLANK_INK_RATIO:
                blank.append((sid, c["char"], round(ratio, 5)))
                continue
            if is_hollow(stroke, edge, args.min_stroke):
                hollow.append((c["char"], round(stroke, 4), round(float(edge), 2)))
            g = trace_to_glyph(bmp, args.reverse_contours)
            if g is None:
                failed.append((sid, c["char"], "trace produced no contour"))
                continue
            name = "uni%04X" % c["cp"]
            if name in glyphs:
                failed.append((sid, c["char"], "duplicate codepoint across sheets"))
                continue
            glyphs[name] = g
            inked.append(c["char"])
            if args.debug_dir:
                cv2.imwrite(os.path.join(args.debug_dir,
                                         f"{sid}_r{c['row']}c{c['col']}_{c['cp']:04X}.png"),
                            (1 - bmp) * 255)

    if not glyphs:
        raise SystemExit("no glyphs traced -- every cell read as blank. "
                         "Check --ink-thresh and the debug dump.")

    font = build_ttf(glyphs, args.family, args.style, args.out)

    # ---- verification: measured, not derived -----------------------------
    order = [g for g in font.getGlyphOrder() if g != ".notdef"]
    cmap = set(font.getBestCmap())
    want = {ord(ch) for ch in inked}
    ok = True
    if cmap != want:
        ok = False
        print(f"FAIL cmap/ink set mismatch: only-in-cmap={sorted(cmap - want)} "
              f"only-in-ink={sorted(want - cmap)}", file=sys.stderr)
    if len(order) != len(inked):
        ok = False
        print(f"FAIL glyph count {len(order)} != inked cells {len(inked)}",
              file=sys.stderr)
    if len(hollow) > HOLLOW_FRACTION * len(inked):
        ok = False
        print(f"FAIL {len(hollow)}/{len(inked)} cells read as outlines: stroke "
              f"half-width < {args.min_stroke} or edge share > {MAX_EDGE_FRAC} "
              f"(worst (char, stroke, edge): "
              f"{sorted(hollow, key=lambda h: h[1])[:6]}). Strokes came out as "
              f"outlines or fragments, not solids -- raise --ink-thresh, or the "
              f"photo is washed out / out of focus.", file=sys.stderr)

    png = os.path.splitext(args.out)[0] + "_proof.png"
    lines, dropped = render_proof(args.out, inked, png)

    print(f"\nttf     : {args.out}")
    print(f"proof   : {png}")
    print(f"glyphs  : {len(order)} (measured from getGlyphOrder)")
    print(f"blank   : {len(blank)} cells skipped"
          + (f" -> {[b[1] for b in blank]}" if blank else ""))
    print(f"failed  : {len(failed)}" + (f" -> {failed}" if failed else ""))
    print(f"hollow  : {len(hollow)} cells (stroke < {args.min_stroke} or "
          f"edge > {MAX_EDGE_FRAC}; (char, stroke, edge))"
          + (f" -> {sorted(hollow, key=lambda h: h[1])[:8]}" if hollow else ""))
    print(f"framed  : {sum(f[1] for f in framed)} frame fragments erased "
          f"in {len(framed)} cells" + (f" -> {[f[0] for f in framed][:12]}"
                                       if framed else "")
          + "  (--keep-frame to disable)")
    print(f"proof lines rendered: {len(lines)}"
          + (f", dropped (chars not in font): {dropped}" if dropped else ""))
    print("verify  : " + ("cmap == inked set, counts agree" if ok else "MISMATCH"))
    print("\nNow LOOK at the proof PNG. A font that installs is not evidence; "
          "a proof sheet where every character is the right character is.")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
