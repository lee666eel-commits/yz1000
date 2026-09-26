"""Trace the per-character ink masks pulled out of donor.pdf into a standalone
donor .ttf, reusing build_font.py's proven tracer/assembler instead of
reinventing bitmap-to-glyph conversion.

Usage: python tools/build_donor_font.py --raw-dir build/donor-CYBBCJT/raw \
    --out build/donor-CYBBCJT/DonorCYBBCJT.ttf --family "Donor CYBBCJT"
"""
import argparse
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from build_font import trace_to_glyph, build_ttf, render_proof  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--family", default="Donor")
    ap.add_argument("--style", default="Regular")
    ap.add_argument("--ink-thresh", type=int, default=127)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.raw_dir, "uni*.png")))
    glyphs, blank, failed = {}, [], []

    for fp in files:
        base = os.path.splitext(os.path.basename(fp))[0]
        cp = int(base[3:], 16)
        img = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
        if img is None:
            failed.append((base, "unreadable"))
            continue
        bmp = (img >= args.ink_thresh).astype(np.uint8)  # white ink -> 1
        if bmp.sum() == 0:
            blank.append(base)
            continue
        g = trace_to_glyph(bmp, reverse=False)
        if g is None:
            failed.append((base, "no contour"))
            continue
        glyphs[f"uni{cp:04X}"] = g

    print(f"input files: {len(files)}  traced: {len(glyphs)}  "
          f"blank: {len(blank)}  failed: {len(failed)}")
    if failed:
        print("failed sample:", failed[:10])

    build_ttf(glyphs, args.family, args.style, args.out)
    png = os.path.splitext(args.out)[0] + "_proof.png"
    chars = [chr(int(n[3:], 16)) for n in sorted(glyphs)]
    lines, dropped = render_proof(args.out, chars, png)
    print(f"ttf: {args.out}")
    print(f"proof: {png}  lines: {len(lines)}  dropped: {dropped}")


if __name__ == "__main__":
    main()
