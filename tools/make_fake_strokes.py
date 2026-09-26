"""Synthesise a stroke capture so the stroke->ttf path can be proven without a
tablet in hand.

Uses only characters made of straight strokes, so the expected result is
unambiguous: their polylines can be written out exactly, and the proof render
either shows 一二三十口日田士 correctly or it does not. Random scribbles would
exercise the same code while telling you nothing about the output.

    python make_fake_strokes.py --out test\\fake_strokes.json
"""

import argparse
import json
import os
import random

BOX = 1000.0
BASE_W = 45.0     # keep in step with make_spen_page.py --base-width


def seg(x0, y0, x1, y1, n=9, jitter=3.0):
    """One straight stroke, sampled, with a pressure ramp: a real stroke lands
    heavy and lifts light, and that ramp is what the width modulation reads."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = x0 + (x1 - x0) * t + random.uniform(-jitter, jitter)
        y = y0 + (y1 - y0) * t + random.uniform(-jitter, jitter)
        p = 0.78 - 0.33 * t
        pts.append([round(x, 1), round(y, 1), round(p, 2)])
    return pts


def h(y, x0, x1):
    return seg(x0, y, x1, y)


def v(x, y0, y1):
    return seg(x, y0, x, y1)


def hook(x0, y0, x1, y1):
    """横折: one stroke that turns a corner."""
    return seg(x0, y0, x1, y0) + seg(x1, y0, x1, y1)[1:]


BOX_3 = [v(280, 240, 760), hook(280, 240, 720, 760), h(760, 280, 720)]

GLYPHS = {
    "一": [h(500, 180, 820)],
    "二": [h(360, 220, 780), h(660, 180, 820)],
    "三": [h(300, 230, 770), h(500, 260, 740), h(700, 180, 820)],
    "十": [h(500, 170, 830), v(500, 170, 830)],
    "口": BOX_3,
    "日": BOX_3 + [h(500, 280, 720)],
    "田": BOX_3 + [v(500, 240, 760), h(500, 280, 720)],
    # bar lengths deliberately far apart: at 64px a modest difference reads as
    # 工 and the check stops discriminating
    "士": [h(280, 380, 620), v(500, 280, 700), h(720, 170, 830)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--pen", action="store_true", default=True)
    args = ap.parse_args()
    random.seed(args.seed)

    glyphs = {}
    for ch, strokes in GLYPHS.items():
        glyphs[str(ord(ch))] = {"char": ch, "pen": args.pen,
                                "strokes": strokes}

    data = {"version": 1, "set_id": "faketest", "box": BOX,
            "base_width": BASE_W, "created": "synthetic", "glyphs": glyphs}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    n = sum(len(g["strokes"]) for g in glyphs.values())
    print(f"{args.out}")
    print(f"glyphs={len(glyphs)} ({''.join(GLYPHS)})  strokes={n}")


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
