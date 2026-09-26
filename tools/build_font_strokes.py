"""Turn captured stylus strokes (writer.html output) into a .ttf.

Almost none of the photo pipeline applies here. There are no registration
marks, no homography, no lighting normalisation and no ink threshold, because
the geometry arrives exact instead of being recovered from a picture. Above
all, the character<->codepoint pairing is structural: the page named the
character and stored the strokes under its codepoint, so the mis-pairing
failure the paper route has to defend against cannot occur.

Strokes are rasterised at 2x and then traced, rather than offset into
variable-width outlines directly. The usual objection to rasterise-then-trace
is that it reintroduces threshold and resampling error -- but there is no
lighting, no threshold ambiguity and no perspective here, so the only cost is
~0.5 font units of quantisation, while direct ribbon offsetting would mean new
self-intersection and cusp handling to get wrong.

    python build_font_strokes.py --strokes strokes\\strokes-ab12cd34.json \\
        --out build\\LinPen.ttf --family "Lin Pen"
"""

import argparse
import json
import math
import os
import sys

import cv2
import numpy as np

from build_font import build_ttf, render_proof, trace_to_glyph

SCALE = 2                 # raster at 2x the logical box, for sub-unit edges

# Width check, NOT the paper route's MIN_STROKE_FRAC. That constant (0.012) was
# calibrated against ~199px photographed cells to catch strokes hollowed out by
# cell-scale light normalisation. Neither half transfers: this route has no
# thresholding stage that could hollow anything, and its box is 1000 units, so
# reusing 0.012 fails every correct capture (measured 0.0095 at width 34).
#
# What is worth asserting here is that rasterisation actually happened at the
# width the capture declared. For a stroke of width W the distance-to-edge is
# roughly uniform across the cross-section, so its median is ~W/4; the raster
# scale cancels, leaving an expected median fraction of base_w/(4*box). Stroke
# junctions and round caps push real glyphs above that, never far below it.
WIDTH_LO, WIDTH_HI = 0.6, 2.5     # multiples of the expected median


ROUND_NIB = {"type": "round", "nib_angle_deg": 0.0, "nib_ratio": 1.0,
             "press": [0.55, 0.9]}


def _nib_basis(nib):
    ang = math.radians(float(nib.get("nib_angle_deg", 0.0)))
    ratio = float(nib.get("nib_ratio", 1.0))
    pa, pb = [float(v) for v in nib.get("press", ROUND_NIB["press"])]
    e1 = (math.cos(ang), math.sin(ang))
    return ang, ratio, pa, pb, e1, (-e1[1], e1[0])


def raster(strokes, box, base_w, pad=0, nib=None):
    """Draw one glyph's strokes into a boolean bitmap the size of the box.

    Width is modulated per segment by pen pressure -- that variation is the
    whole reason a stylus capture reads as handwriting instead of as a
    constant-width monoline -- and, for a nib with ratio < 1, by the DIRECTION
    of travel, which is what separates a 钢笔 from a felt tip. This is the same
    formula make_spen_page.py draws with, and captures carry the parameters, so
    the .ttf cannot drift from what was under the pen while writing.
    """
    ang, ratio, pa, pb, e1, e2 = _nib_basis(nib or ROUND_NIB)
    n = int(box * SCALE)
    img = np.zeros((n, n), np.uint8)

    # cv2 takes integer coordinates, so hand it fixed-point ones: rounding
    # centres to whole pixels shifts the ink half a pixel against the canvas
    # implementation, which is a real (if small) divergence between what was
    # written and what gets built.
    SUB = 4
    K = 1 << SUB

    def px(p):
        return (int(round(p[0] * SCALE * K)), int(round(p[1] * SCALE * K)))

    def nib_len(p):
        return max(1.0, base_w * (pa + pb * float(p)) * SCALE)

    def half(p, nx, ny):                 # support radius along the unit normal
        a = nib_len(p) / 2.0
        u = a * (nx * e1[0] + ny * e1[1])
        v = a * ratio * (nx * e2[0] + ny * e2[1])
        return math.hypot(u, v)

    def blob(p):                         # joins, and the angled ends
        a = max(1.0, nib_len(p[2]) / 2)
        cv2.ellipse(img, px(p), (int(round(a * K)), max(1, int(round(a * ratio * K)))),
                    math.degrees(ang), 0, 360, 255, -1, cv2.LINE_AA, SUB)

    for s in strokes:
        if not s:
            continue
        if len(s) == 1:
            blob(s[0])
            continue
        for a, b in zip(s, s[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            ha, hb = half(a[2], nx, ny), half(b[2], nx, ny)
            quad = (np.array([
                [a[0] * SCALE + nx * ha, a[1] * SCALE + ny * ha],
                [b[0] * SCALE + nx * hb, b[1] * SCALE + ny * hb],
                [b[0] * SCALE - nx * hb, b[1] * SCALE - ny * hb],
                [a[0] * SCALE - nx * ha, a[1] * SCALE - ny * ha],
            ]) * K).round().astype(np.int32)
            cv2.fillConvexPoly(img, quad, 255, cv2.LINE_AA, SUB)
        for p in s:
            blob(p)
    return img > 127


def mean_width(strokes, base_w, nib):
    """Ink width this nib actually lays down on these strokes.

    The width guard compares the rasterised median against an expectation. With
    a directional nib that expectation is no longer base_w -- a 撇 under a
    40-degree nib is a fraction of it -- so derive it from the strokes' own
    travel directions. Reusing the round-nib constant here would fail every
    correct capture, exactly the way MIN_STROKE_FRAC did when it was carried
    over from the paper route.
    """
    _, ratio, pa, pb, e1, e2 = _nib_basis(nib or ROUND_NIB)
    tot, cnt = 0.0, 0
    for s in strokes:
        for a, b in zip(s, s[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy)
            if ln < 1e-6:
                continue
            nx, ny = -dy / ln, dx / ln
            r = base_w * (pa + pb * (float(a[2]) + float(b[2])) / 2.0) / 2.0
            u = r * (nx * e1[0] + ny * e1[1])
            v = r * ratio * (nx * e2[0] + ny * e2[1])
            tot += 2.0 * math.hypot(u, v)
            cnt += 1
    return tot / cnt if cnt else base_w


def stroke_frac(bmp):
    if not bmp.any():
        return 0.0
    d = cv2.distanceTransform(bmp.astype(np.uint8), cv2.DIST_L2, 5)
    return float(np.percentile(d[bmp], 50)) / max(bmp.shape)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strokes", required=True, help="writer.html .json output")
    ap.add_argument("--out", required=True)
    ap.add_argument("--family", default="Pen Hand")
    ap.add_argument("--style", default="Regular")
    ap.add_argument("--width", type=float,
                    help="stroke width in em/1000 units. Defaults to the value "
                         "the capture page recorded, which is what you saw "
                         "while writing -- only override to re-weight the font.")
    ap.add_argument("--reverse-contours", action="store_true")
    ap.add_argument("--debug-dir")
    args = ap.parse_args()

    with open(args.strokes, encoding="utf-8") as f:
        data = json.load(f)
    box = float(data.get("box", 1000))
    base_w = args.width if args.width else float(data.get("base_width", 34))
    src = data["glyphs"]
    if not src:
        raise SystemExit(f"{args.strokes} contains no glyphs")
    if args.debug_dir:
        os.makedirs(args.debug_dir, exist_ok=True)

    nib = data.get("pen_model") or ROUND_NIB
    glyphs, chars, thin, empty, fracs = {}, [], [], [], []
    finger = []
    for cp_s, g in src.items():
        cp = int(cp_s)
        ch = g.get("char") or chr(cp)
        if ch != chr(cp):
            raise SystemExit(f"corrupt capture: codepoint {cp} labelled {ch!r}")
        # per glyph, because a directional nib lays down different amounts of
        # ink depending on which way its strokes run
        expect = mean_width(g["strokes"], base_w, nib) / (4.0 * box)
        bmp = raster(g["strokes"], box, base_w, nib=nib)
        if not bmp.any():
            empty.append(ch)
            continue
        gl = trace_to_glyph(bmp, args.reverse_contours)
        if gl is None:
            empty.append(ch)
            continue
        f = stroke_frac(bmp)
        fracs.append(f)
        if not (WIDTH_LO * expect <= f <= WIDTH_HI * expect):
            thin.append((ch, round(f, 4), round(expect, 4)))
        glyphs["uni%04X" % cp] = gl
        chars.append(ch)
        if not g.get("pen"):
            finger.append(ch)
        if args.debug_dir:
            cv2.imwrite(os.path.join(args.debug_dir, f"{cp:04X}.png"),
                        (~bmp).astype(np.uint8) * 255)

    if not glyphs:
        raise SystemExit("every glyph rasterised empty -- check --width")

    font = build_ttf(glyphs, args.family, args.style, args.out)

    order = [g for g in font.getGlyphOrder() if g != ".notdef"]
    cmap = set(font.getBestCmap())
    want = {ord(c) for c in chars}
    ok = True
    if cmap != want:
        ok = False
        print(f"FAIL cmap/captured set mismatch: "
              f"only-in-cmap={sorted(cmap - want)} "
              f"only-in-capture={sorted(want - cmap)}", file=sys.stderr)
    if len(order) != len(chars):
        ok = False
        print(f"FAIL glyph count {len(order)} != captured {len(chars)}",
              file=sys.stderr)
    if thin:
        ok = False
        print(f"FAIL {len(thin)} glyphs rasterised at the wrong width "
              f"(char, measured, expected): {thin[:8]}"
              f" -- allowed {WIDTH_LO:g}..{WIDTH_HI:g}x the expected median for "
              f"base width {base_w} through a "
              f"{nib.get('type', 'round')} nib. Rasterisation and the declared "
              f"width disagree.", file=sys.stderr)

    png = os.path.splitext(args.out)[0] + "_proof.png"
    lines, dropped = render_proof(args.out, chars, png)

    print(f"\nttf     : {args.out}")
    print(f"proof   : {png}")
    print(f"glyphs  : {len(order)} (measured from getGlyphOrder)")
    print(f"width   : {base_w} em/1000 units"
          + ("" if args.width else " (from the capture)")
          + f"; measured median {min(fracs):.4f}..{max(fracs):.4f}")
    print(f"nib     : {nib.get('type', 'round')} "
          f"angle={nib.get('nib_angle_deg', 0)} ratio={nib.get('nib_ratio', 1)}"
          + ("" if data.get("pen_model") else "  (capture predates pen_model; "
                                              "assumed the old round tip)"))
    if data.get("cell_px"):
        # px is what the page measured; the mm is CSS's nominal 96dpi guess and
        # is exactly why the writer gets a slider instead of a calibrated scale
        print(f"written : {data['cell_px']}px cells "
              f"(nominal ~{data.get('cell_mm', '?')}mm, not a measured one), "
              + ("直书" if data.get("vertical") else "横书")
              + "  <- the size the hand actually worked at")
    print(f"empty   : {len(empty)}" + (f" -> {empty}" if empty else ""))
    print(f"stylus  : {len(chars) - len(finger)}/{len(chars)} written with a pen"
          + (f"; no pressure signal on {finger[:8]}" if finger else ""))
    print(f"proof lines rendered: {len(lines)}"
          + (f", dropped: {dropped}" if dropped else ""))
    print("verify  : " + ("cmap == captured set, counts agree"
                          if ok else "MISMATCH"))
    print("\nPairing is structural on this route, so the proof PNG is about "
          "letterform quality, not identity. Still read it.")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
