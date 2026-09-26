# Split a FontDiffuser eval sheet (96px cells, col 0 = ref glyph) into phone-readable parts.
# usage: python split_sheet.py <outputs_dir> <label1> <label2> ...   (one label per row, in order)
import os, sys
from PIL import Image, ImageDraw, ImageFont

CELL, LW, PER = 96, 110, 15
d, labels = sys.argv[1], sys.argv[2:]
sheet = Image.open(os.path.join(d, "sheet_missho_heldout.png"))
rows = sheet.height // CELL
assert len(labels) == rows, f"sheet has {rows} rows, got {len(labels)} labels"
cols = sheet.width // CELL - 1
try:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
except Exception:
    font = ImageFont.load_default()
for k in range((cols + PER - 1) // PER):
    x0 = CELL * (1 + PER * k)
    part = sheet.crop((x0, 0, min(x0 + CELL * PER, sheet.width), sheet.height))
    out = Image.new("RGB", (LW + part.width, part.height), "white")
    out.paste(part, (LW, 0))
    dr = ImageDraw.Draw(out)
    for i, l in enumerate(labels):
        dr.text((6, CELL * i + 38), l, fill="black", font=font)
        dr.line([(0, CELL * i), (out.width, CELL * i)], fill="red", width=1)
    dr.line([(LW, 0), (LW, out.height)], fill="red", width=2)
    p = os.path.join(d, f"sheet_part{k + 1}.png")
    out.save(p)
    print(p, out.size)
