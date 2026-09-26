"""Uniformly enlarge every glyph so her writing fills a normal share of the em box.

Why: build_font.py maps the whole 17.8mm grid cell onto the em (so per-character
size variance survives -- that is the handwriting feel), but she wrote at ~50% of
the cell, so her hanzi ink is 499/1000 em against ~897 for Noto SC. Next to any
Latin/digit fallback her Chinese looks tiny (his 2026-09-23 test: 落差太大).
One factor for all glyphs, x and y together, about her median ink centre, which is
then moved to the em centre -- variance and proportions are untouched.
Also widens OS/2 winAscent/winDescent to the real extents: Windows GDI clips any
outline that pokes beyond them.
"""
import argparse
import os

import numpy as np
from fontTools.ttLib import TTFont

UPM, EM_CX, EM_CY = 1000, 500.0, 380.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--k", type=float, required=True)
    ap.add_argument("--family", required=True)
    a = ap.parse_args()
    assert not os.path.exists(a.out) or os.environ.get("ALLOW_OVERWRITE"), a.out + " exists"

    f = TTFont(a.src)
    glyf, cmap = f["glyf"], f.getBestCmap()
    han = [cmap[c] for c in cmap if 0x4E00 <= c <= 0x9FFF]
    cx = float(np.median([(glyf[n].xMax + glyf[n].xMin) / 2 for n in han]))
    cy = float(np.median([(glyf[n].yMax + glyf[n].yMin) / 2 for n in han]))
    h0 = float(np.median([glyf[n].yMax - glyf[n].yMin for n in han]))

    for name in f.getGlyphOrder():
        g = glyf[name]
        if not g.numberOfContours:
            continue
        c = g.coordinates
        for i in range(len(c)):
            x, y = c[i]
            c[i] = (int(round(EM_CX + (x - cx) * a.k)), int(round(EM_CY + (y - cy) * a.k)))
        g.recalcBounds(glyf)

    ymax = max(glyf[n].yMax for n in f.getGlyphOrder() if glyf[n].numberOfContours)
    ymin = min(glyf[n].yMin for n in f.getGlyphOrder() if glyf[n].numberOfContours)
    os2 = f["OS/2"]
    os2.usWinAscent, os2.usWinDescent = max(os2.usWinAscent, ymax), max(os2.usWinDescent, -ymin)
    f["head"].yMax, f["head"].yMin = ymax, ymin
    n = f["name"]
    for nid, val in ((1, a.family), (4, a.family + " Regular"), (6, a.family.replace(" ", "") + "-Regular")):
        n.setName(val, nid, 3, 1, 0x409)
        n.setName(val, nid, 1, 0, 0)
    f.save(a.out)

    rb = TTFont(a.out)
    rg, rc = rb["glyf"], rb.getBestCmap()
    rh = [rg[rc[c]].yMax - rg[rc[c]].yMin for c in rc if 0x4E00 <= c <= 0x9FFF]
    print("k=%.2f centre (%.0f,%.0f)->(500,380) | hanzi ink height median %.0f -> %.0f (read back) | glyphs %d"
          % (a.k, cx, cy, h0, np.median(rh), len(rc)))
    print("winAscent %d winDescent %d | wrote %s" % (rb["OS/2"].usWinAscent, rb["OS/2"].usWinDescent, a.out))


if __name__ == "__main__":
    main()
