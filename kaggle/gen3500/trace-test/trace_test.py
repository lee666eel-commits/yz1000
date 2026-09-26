# One-glyph experiment: can 96px FontDiffuser output be vectorised through the SAME potrace path
# build_font.py uses for 600dpi scans? Variants: raw 96 / 2x / 4x bicubic+gaussian+threshold.
import os, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, "D:/handwriting-font/tools")
import build_font as bf

G = "D:/handwriting-font/kaggle/gen3500/results-v1/outputs/glyphs"
REAL_TTF = "D:/handwriting-font/build/0005MissHo.ttf"
CHARS = "一微羹"
VARIANTS = [("raw96", 1, 0), ("x2", 2, 0.8), ("x4", 4, 1.6)]   # (name, scale, gaussian sigma px)
U = lambda c: f"U{ord(c):04X}"

def bitmap(ch, scale, sigma):
    g = np.asarray(Image.open(f"{G}/{U(ch)}.png").convert("L"))
    if scale > 1:
        g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        g = cv2.GaussianBlur(g, (0, 0), sigma)
    return (g < 128).astype(np.uint8)

glyphs, names = {}, {}
for ch in CHARS:
    for name, scale, sigma in VARIANTS:
        bmp = bitmap(ch, scale, sigma)
        gl = bf.trace_to_glyph(bmp, reverse=False)
        assert gl is not None, (ch, name)
        gname = f"{U(ch)}_{name}"
        glyphs[gname] = gl
        names[(ch, name)] = gname
        print(ch, name, "bitmap", bmp.shape, "ink px", int(bmp.sum()), "contours", len(gl.endPtsOfContours), "points", len(gl.coordinates))

# build a throwaway TTF: map each variant to a private-use codepoint so PIL can render it
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
fb = FontBuilder(bf.UPM, isTTF=True)
order = [".notdef"] + list(glyphs)
fb.setupGlyphOrder(order)
cmap = {}
for i, gname in enumerate(glyphs):
    cmap[0xE000 + i] = gname
fb.setupCharacterMap(cmap)
fb.setupGlyf({".notdef": TTGlyphPen(None).glyph(), **glyphs})
fb.setupHorizontalMetrics({n: (bf.UPM, 0) for n in order})
fb.setupHorizontalHeader(ascent=bf.ASCENT, descent=bf.ASCENT - bf.UPM)
fb.setupNameTable({"familyName": "tracetest", "styleName": "Regular"})
fb.setupOS2(); fb.setupPost()
fb.save("tracetest.ttf")

# proof: rows = chars; cols = source bitmap | raw96 | x2 | x4 | real MissHo 机 (scan-traced reference)
S = 200; pad = 20
cols = 1 + len(VARIANTS) + 1
img = Image.new("L", (pad + cols * (S + pad), pad + len(CHARS) * (S + pad) + 30), 255)
dr = ImageDraw.Draw(img)
ft = ImageFont.truetype("tracetest.ttf", S)
fr = ImageFont.truetype(REAL_TTF, S)
lab = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
for j, t in enumerate(["生成96px位图"] + [v[0] for v in VARIANTS] + ["真迹扫描描边(机)"]):
    dr.text((pad + j * (S + pad), 4), t, font=lab, fill=0)
for i, ch in enumerate(CHARS):
    y = 30 + pad + i * (S + pad)
    src = Image.open(f"{G}/{U(ch)}.png").convert("L").resize((S, S), Image.NEAREST)
    img.paste(src, (pad, y))
    for j, (name, _, _) in enumerate(VARIANTS):
        cp = 0xE000 + list(glyphs).index(names[(ch, name)])
        dr.text((pad + (j + 1) * (S + pad), y), chr(cp), font=ft, fill=0)
    dr.text((pad + (len(VARIANTS) + 1) * (S + pad), y), "机", font=fr, fill=0)
img.save("trace_test_proof.png")
print("proof", img.size)
