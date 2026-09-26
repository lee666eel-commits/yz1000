"""Synthesise a fake photographed sheet so the pipeline can be proven before
anyone hand-writes 100 characters into a possibly-broken slicer.

It draws the printed artefacts too -- grey cell rules and grey guide glyphs --
so thresholding is tested against the real nuisance signal, then adds rotation,
perspective, uneven lighting and noise. A few cells are left un-inked on
purpose to exercise blank detection.
"""

import argparse
import json
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PPM = 18.0          # render at higher res than the pipeline's canonical 12 px/mm
GUIDE_FONT = r"C:\Windows\Fonts\simkai.ttf"    # printed guide: 楷体
INK_FONT = r"C:\Windows\Fonts\msyh.ttc"        # stands in for handwriting


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sheet", default="S1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip", type=int, default=3,
                    help="leave this many cells un-inked, to test blank detection")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--ink-fill", type=int, default=25,
                    help="grey level of the fake ink (0=black). Real pen on "
                         "phone-photographed paper lands nearer 60-130.")
    ap.add_argument("--guide-tint", type=int, default=208,
                    help="grey the printed guide glyph comes out at; raise the "
                         "darkness (lower number) to simulate a heavy printer")
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    with open(args.manifest, encoding="utf-8") as f:
        man = json.load(f)
    sheet = next(s for s in man["sheets"] if s["id"] == args.sheet)

    W = int(man["page_mm"][0] * PPM)
    H = int(man["page_mm"][1] * PPM)
    img = Image.new("L", (W, H), 252)
    dr = ImageDraw.Draw(img)

    side = man["mark_side_mm"] * PPM
    for mx, my in man["marks_mm"]:
        x, y = mx * PPM, my * PPM
        dr.rectangle([x - side / 2, y - side / 2, x + side / 2, y + side / 2],
                     fill=20)

    cell_px = man["cell_mm"] * PPM
    guide = ImageFont.truetype(GUIDE_FONT, int(cell_px * 0.78))
    ink = ImageFont.truetype(INK_FONT, int(cell_px * 0.70))
    # v2 sheets print red rules and name the character in a gutter above the
    # cell instead of putting a traceable glyph inside it. Simulating that is
    # the only way to test whether either artefact leaks into the crops.
    red_sheet = man.get("grid_color") == "red"
    label = ImageFont.truetype(GUIDE_FONT, int(cell_px * 0.22))

    skipped = set(random.sample(range(len(sheet["cells"])), args.skip))
    for i, c in enumerate(sheet["cells"]):
        cx, cy, cw, ch = [v * PPM for v in c["cell_mm"]]
        if red_sheet:
            # greyscale value of #e23b32; deliberately DARKER than the v1 grey
            # rule, which is the whole point of the red-channel read
            dr.rectangle([cx, cy, cx + cw, cy + ch], outline=108, width=2)
            dr.line([cx, cy + ch / 2, cx + cw, cy + ch / 2], fill=170, width=1)
            dr.line([cx + cw / 2, cy, cx + cw / 2, cy + ch], fill=170, width=1)
            dr.text((cx + cw / 2, cy - cell_px * 0.12), c["char"], font=label,
                    fill=108, anchor="mm")
        else:
            dr.rectangle([cx, cy, cx + cw, cy + ch], outline=205, width=2)
            dr.text((cx + cw / 2, cy + ch / 2), c["char"], font=guide,
                    fill=args.guide_tint, anchor="mm")
        if i in skipped:
            continue
        # jitter position/size a little so the glyphs are not pixel-identical
        jx = random.uniform(-0.05, 0.05) * cw
        jy = random.uniform(-0.05, 0.05) * ch
        tile = Image.new("L", (int(cw), int(ch)), 255)
        ImageDraw.Draw(tile).text((cw / 2 + jx, ch / 2 + jy), c["char"],
                                  font=ink, fill=args.ink_fill, anchor="mm")
        tile = tile.rotate(random.uniform(-4, 4), resample=Image.BICUBIC,
                           fillcolor=255)
        a = np.array(img.crop((int(cx), int(cy), int(cx) + int(cw),
                               int(cy) + int(ch))))
        img.paste(Image.fromarray(np.minimum(a, np.array(tile))),
                  (int(cx), int(cy)))

    page = np.array(img)

    # --- camera-ish degradation ------------------------------------------
    ang = 2.3
    M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
    page = cv2.warpAffine(page, M, (W, H), borderValue=252)

    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = np.float32([[18, 26], [W - 34, 8], [W - 12, H - 30], [40, H - 10]])
    page = cv2.warpPerspective(page, cv2.getPerspectiveTransform(src, dst),
                               (W, H), borderValue=252)

    yy, xx = np.mgrid[0:H, 0:W]
    shade = 1.0 - 0.28 * ((xx / W) * 0.6 + (yy / H) * 0.4)
    page = np.clip(page.astype(np.float32) * shade + 18, 0, 255)
    page = np.clip(page + np.random.normal(0, 3.5, page.shape), 0, 255)
    page = cv2.GaussianBlur(page.astype(np.uint8), (3, 3), 0)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    cv2.imwrite(args.out, page)
    print(f"{args.out}  {W}x{H}")
    print(f"deliberately blank cells: "
          f"{sorted(sheet['cells'][i]['char'] for i in skipped)}")


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
