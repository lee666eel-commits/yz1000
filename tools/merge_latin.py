# Merge a hand-written Latin/digit/punct font (template-latin-punct L1 build) into a full CJK font,
# giving the ASCII glyphs proportional widths. build_font.py gives every glyph a fixed 1000-unit
# advance (CJK full width), so Latin text set in it reads like "A  B  C". This is the hmtx step
# the README lists as not done.
#   ASCII (U+0021-007E): glyph shifted so its left ink edge sits at --sb, advance = ink width + 2*sb.
#   Everything else (。，、：“”‘’—… etc.): kept full-width 1000, Chinese convention.
#   Codepoints the full font already has are NOT replaced (they are the same hand, written earlier).
#   Adds U+0020 space (--space units) if missing, so English words are separated in this font's own width.
# usage: python tools\merge_latin.py --full build\X-full.ttf --latin build\X-latin\X-latin.ttf --out build\X-full-latin.ttf
import argparse, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ap = argparse.ArgumentParser()
ap.add_argument("--full", required=True)
ap.add_argument("--latin", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--sb", type=int, default=50, help="side bearing for ASCII glyphs (font units)")
ap.add_argument("--space", type=int, default=300, help="advance of U+0020")
ap.add_argument("--keep-punct-position", action="store_true",
                help="do not move . , ， 。 、 to the baseline (see SEAT)")
ap.add_argument("--strip-lines", action="store_true",
                help="re-raster letters/digits and erase thin horizontal lines fused INTO a stroke (frame/guide lines a "
                     "filtered scan turned black; contour-level cleanup cannot separate them). Opt-in.")
a = ap.parse_args()
if os.path.exists(a.out):
    raise SystemExit(f"refusing to overwrite {a.out} -- pick a new name")



def drop_border_specks(g, band=100, max_side=200):
    """Remove small contours lying wholly inside the outer `band` of the 1000-unit cell: printed frame
    residue strip_frame missed (a participant's 'y', 10-13: a 120x60 sliver in the top-left corner). A tiny
    contour near the centre (a dot, a quote) is never touched. Returns the dropped bboxes."""
    if g.numberOfContours <= 1:
        return []
    coords, ends, flags = g.coordinates, g.endPtsOfContours, g.flags
    keep, gone, start = [], [], 0
    for e in ends:
        pts = coords[start:e + 1]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        small = (x1 - x0) <= max_side and (y1 - y0) <= max_side
        border = x1 <= band or x0 >= 1000 - band or y1 <= -120 + band or y0 >= 880 - band  # cell spans descent -120 .. ascent 880
        (gone if small and border else keep).append((start, e, (x0, x1, y0, y1)))
        start = e + 1
    if not gone or not keep:
        return []
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    nc, nf, ne = [], [], []
    for s, e, _ in keep:
        nc += list(coords[s:e + 1])
        nf += list(flags[s:e + 1])
        ne.append(len(nc) - 1)
    g.coordinates, g.flags, g.endPtsOfContours = GlyphCoordinates(nc), bytearray(nf) if isinstance(flags, bytearray) else __import__('array').array(flags.typecode, nf), ne
    g.numberOfContours = len(ne)
    return [b for _, _, b in gone]


GUIDE_TARGETS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@%#&【】（）《》")


def drop_guide_residue(g):
    """Remove printed 米字格 / frame residue that survived build_font (a CamScanner 'enhanced' scan turns the
    red guides near-black, 林子策 10-14). Measured shapes, glyph units (cell = -120..880):
      horizontal guide dashes : h <= 22, w <= 70, centred in y 400..490
      vertical guide dashes   : w <= 22, h <= 60, centred in x 500..570
      frame line              : h <= 12, w >= 150
    Only OUTER contours (same winding as the largest) -- a letter's counter is never touched -- and only
    on letters/digits/@%#&【】, never on punctuation such as - — whose real ink looks exactly like this."""
    if g.numberOfContours <= 1:
        return []
    co, ends = g.coordinates, g.endPtsOfContours
    parts, s = [], 0
    for e in ends:
        pts = list(co[s:e + 1])
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        parts.append((s, e, area, (min(xs), max(xs), min(ys), max(ys))))
        s = e + 1
    outer_sign = 1 if max(parts, key=lambda p: abs(p[2]))[2] > 0 else -1
    gone = []
    for s, e, area, (x0, x1, y0, y1) in parts:
        w, h, xm, ym = x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2
        if area * outer_sign <= 0:
            continue
        if (h <= 22 and w <= 70 and 400 <= ym <= 490) or (w <= 22 and h <= 60 and 500 <= xm <= 570) \
                or (h <= 12 and w >= 150):
            gone.append((s, e))
    if not gone or len(gone) == len(parts):
        return []
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    nc, nf, ne = [], [], []
    for s, e, _, _ in parts:
        if (s, e) in gone:
            continue
        nc += list(co[s:e + 1])
        nf += list(g.flags[s:e + 1])
        ne.append(len(nc) - 1)
    g.coordinates, g.flags, g.endPtsOfContours, g.numberOfContours = GlyphCoordinates(nc), bytearray(nf), ne, len(ne)
    return gone


def strip_fused_lines(ch, px=500, thin=6, long=70):
    """Render ch from the latin font in build_font's cell->em mapping, erase pixels that belong to a horizontal
    run >= `long` px of ink whose vertical thickness is <= `thin` px (12 / 140 units at px=500: a printed rule,
    never a brush stroke of this hand -- its thinnest strokes measured ~30 units), re-trace. None if nothing to do."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_font as bf
    im = Image.new("L", (px, px), 0)
    ImageDraw.Draw(im).text((0, bf.ASCENT / bf.UPM * px), ch, font=ImageFont.truetype(a.latin, px), fill=255, anchor="ls")
    ink = np.asarray(im) > 127
    vt = np.zeros(ink.shape, int)                     # vertical run length through each ink pixel
    for x in range(px):
        col, y = ink[:, x], 0
        while y < px:
            if col[y]:
                y2 = y
                while y2 < px and col[y2]:
                    y2 += 1
                vt[y:y2, x] = y2 - y
                y = y2
            else:
                y += 1
    thinpx = ink & (vt <= thin)
    kill = np.zeros_like(ink)
    for y in range(px):
        row, x = thinpx[y], 0
        while x < px:
            if row[x]:
                x2 = x
                while x2 < px and row[x2]:
                    x2 += 1
                if x2 - x >= long:
                    kill[y, x:x2] = True
                x = x2
            else:
                x += 1
    if not kill.any():
        return None
    import cv2
    left = (ink & ~kill).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(left, 8)
    for i in range(1, n):   # line stubs the erase cut loose where the rule met a stroke (flat, wide, tiny)
        w, h = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        if h <= thin + 2 and w >= 3 * h:
            left[lab == i] = 0
            kill |= lab == i
    return bf.trace_to_glyph(left, False), int(kill.sum())


full, lat = TTFont(a.full), TTFont(a.latin)
fcmap, lcmap = full.getBestCmap(), lat.getBestCmap()
glyf, hmtx, lglyf = full["glyf"], full["hmtx"], lat["glyf"]
order = list(full.getGlyphOrder())
added, skipped, narrowed = [], [], 0

# Seat baseline punctuation. The L1 sheet never told writers WHERE in the cell to put . , ， 。 、
# so a participant wrote them in the centre (10-13) and they set as mid-dots ("3.14" read "3·14").
# Our instruction gap, not her error: move them here instead of asking for a rewrite.
#   . ,      -> bottom on her own Latin baseline (median yMin of non-descender letters + digits)
#   ， 。 、 -> bottom-left of the em, bottom on her own CJK baseline (median yMin of her CJK glyphs)
med = lambda v: sorted(v)[len(v) // 2]
lat_base = med([lglyf[lcmap[ord(c)]].yMin for c in "acemnorsuvwxzABCDEHKLMNRSTUVWXZ0123456789" if ord(c) in lcmap])
cjk_base = med([glyf[n].yMin for c, n in fcmap.items() if 0x4E00 <= c <= 0x9FFF and glyf[n].numberOfContours > 0])
SEAT = {} if a.keep_punct_position else {".": "lat", ",": "lat", "，": "cjk", "。": "cjk", "、": "cjk"}
print(f"baselines: latin {lat_base}, cjk {cjk_base}")


def keep_main(g):
    """A seated mark is one blob (plus its counter, e.g. 。): drop every contour not inside the largest one,
    otherwise scan residue widens the bbox and the mark is seated by the wrong box (林子策 ， 10-14)."""
    if g.numberOfContours <= 1:
        return 0
    co, ends, parts, s = g.coordinates, g.endPtsOfContours, [], 0
    for e in ends:
        xs, ys = [p[0] for p in co[s:e + 1]], [p[1] for p in co[s:e + 1]]
        parts.append((s, e, (min(xs), max(xs), min(ys), max(ys))))
        s = e + 1
    big = max(parts, key=lambda p: (p[2][1] - p[2][0]) * (p[2][3] - p[2][2]))[2]
    inside = lambda b: b[0] >= big[0] and b[1] <= big[1] and b[2] >= big[2] and b[3] <= big[3]
    keep = [p for p in parts if inside(p[2])]
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    nc, nf, ne = [], [], []
    for s, e, _ in keep:
        nc += list(co[s:e + 1]); nf += list(g.flags[s:e + 1]); ne.append(len(nc) - 1)
    dropped = len(parts) - len(keep)
    g.coordinates, g.flags, g.endPtsOfContours, g.numberOfContours = GlyphCoordinates(nc), bytearray(nf), ne, len(ne)
    return dropped


def seat(g, ch, how):
    k = keep_main(g)
    if k:
        print(f"seat-clean: {ch!r} dropped {k} stray contours")
    g.recalcBounds(lglyf)
    if how == "lat":
        dy = lat_base - g.yMin if ch == "." else lat_base + 40 - g.yMax   # comma hangs just below
        dx = 0
    else:   # full-width comma: its tail dips below the line (a tall comma seated by its foot floats mid-line)
        drop = int(0.35 * (g.yMax - g.yMin)) if ch == "，" else 0
        dy, dx = cjk_base - drop - g.yMin, 120 - g.xMin
    g.getCoordinates(lglyf)[0].translate((dx, dy))
    g.recalcBounds(lglyf)
    print(f"seated   : {ch!r} moved dx={dx} dy={dy}")


# template-core (10-14) does not ask for half-width ? ! ; : ( ) ' " -- in handwriting they are the
# same shapes as the full-width ones. Derive them: copy the full-width glyph, it gets narrowed below.
import copy  # noqa: E402
DERIVE = {"?": "？", "!": "！", ";": "；", ":": "：", "(": "（", ")": "）", "'": "’", '"': "”"}
derived = []
for half, fw in DERIVE.items():
    src = lcmap.get(ord(fw)) or fcmap.get(ord(fw))
    if ord(half) in lcmap or ord(half) in fcmap or not src:
        continue
    srcfont = lglyf if ord(fw) in lcmap else glyf
    nm = f"derived_{ord(half):04X}"
    lglyf.glyphs[nm] = copy.deepcopy(srcfont[src])
    lcmap[ord(half)] = nm
    derived.append(half)
guide_dropped, line_stripped = {}, {}
if derived:
    print(f"derived  : {''.join(derived)} from their full-width glyphs")

for cp, lname in sorted(lcmap.items()):
    if cp in fcmap:
        skipped.append(chr(cp))
        continue
    g = lglyf[lname]
    name = f"uni{cp:04X}"
    dropped = drop_border_specks(g)
    if dropped:
        print(f"border speck dropped: {chr(cp)!r} {dropped}")
    if a.strip_lines and chr(cp) in GUIDE_TARGETS:
        r = strip_fused_lines(chr(cp))
        if r and r[0] is not None:
            g = r[0]
            line_stripped[chr(cp)] = r[1]
    if chr(cp) in GUIDE_TARGETS:
        res = drop_guide_residue(g)
        if res:
            guide_dropped[chr(cp)] = len(res)
    if chr(cp) in SEAT:
        seat(g, chr(cp), SEAT[chr(cp)])
    assert name not in order, name
    if 0x21 <= cp <= 0x7E:
        g.recalcBounds(lglyf)
        dx = a.sb - g.xMin
        coords = g.getCoordinates(lglyf)[0]
        coords.translate((dx, 0))
        g.recalcBounds(lglyf)
        adv = (g.xMax - g.xMin) + 2 * a.sb
        narrowed += 1
    else:
        adv = lat["hmtx"][lname][0]
    glyf.glyphs[name] = g
    order.append(name)
    hmtx.metrics[name] = (adv, getattr(g, "xMin", 0))
    added.append(cp)

if 0x20 not in fcmap:
    glyf.glyphs["space"] = TTGlyphPen(None).glyph()
    order.append("space")
    hmtx.metrics["space"] = (a.space, 0)
    added.append(0x20)

full.setGlyphOrder(order)
glyf.glyphOrder = order
for t in full["cmap"].tables:
    if t.isUnicode():
        for cp in added:
            if t.format != 4 or cp <= 0xFFFF:
                t.cmap[cp] = "space" if cp == 0x20 else f"uni{cp:04X}"
full["maxp"].numGlyphs = len(order)
full["hhea"].numberOfHMetrics = len(order)
full.save(a.out)

# measured, not derived
chk = TTFont(a.out)
cm = chk.getBestCmap()
missing = [chr(c) for c in added if c not in cm]
assert not missing, missing
print(f"out      : {a.out}")
if a.strip_lines:
    print(f"fused lines stripped: {len(line_stripped)} glyphs (px erased) {line_stripped}")
print(f"guide residue dropped: {sum(guide_dropped.values())} contours in {len(guide_dropped)} glyphs {dict(guide_dropped)}")
print(f"glyphs   : {len(chk.getGlyphOrder())} (was {len(full.getGlyphOrder()) - len(added)} + {len(added)} added, measured {len(cm)} cmap entries)")
print(f"narrowed : {narrowed} ASCII glyphs, sb={a.sb}; space={a.space}")
print(f"skipped  : {len(skipped)} already in full font -> {''.join(skipped)}")
