"""Mixed CJK/Latin/digit proof: how each candidate looks next to system fallback glyphs.

Chars her font lacks are drawn with Microsoft YaHei (stand-in for what Word/Windows
substitutes). All runs share one baseline and one point size, like a real text line.
"""
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

B = "D:/handwriting-font/build/"
CANDS = [("原版 full.ttf", B + "0005MissHo-full.ttf"),
         ("放大 ×1.45", B + "0005MissHo-full-v2-k1.45.ttf"),
         ("放大 ×1.6", B + "0005MissHo-full-v2-k1.6.ttf")]
FALLBACK = "C:/Windows/Fonts/msyh.ttc"
TEXT = ["南华独中 2026 年 NHFS 校庆（第 90 届），欢迎光临！",
        "Email: nhfs@school.my，电话 05-6891234。"]
SIZE, PAD, LINE = 56, 30, 100


def draw_line(dr, x, y, text, her, cov, fb):
    for ch in text:
        f = her if ord(ch) in cov else fb
        dr.text((x, y), ch, font=f, fill=0, anchor="ls")
        x += f.getlength(ch)
    return x


def main():
    fb = ImageFont.truetype(FALLBACK, SIZE)
    lab = ImageFont.truetype(FALLBACK, 20)
    W, H = 1500, PAD + len(CANDS) * (40 + len(TEXT) * LINE + 20)
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    y = PAD
    for label, path in CANDS:
        dr.text((PAD, y), label, font=lab, fill=(180, 40, 40))
        y += 40
        her = ImageFont.truetype(path, SIZE)
        cov = set(TTFont(path).getBestCmap())
        for t in TEXT:
            y += LINE
            draw_line(dr, PAD, y - 25, t, her, cov, fb)
        y += 20
        dr.line([(0, y), (W, y)], fill=(210, 210, 210))
    img.save(B + "0005MissHo-mixed_proof.png")
    print("wrote", B + "0005MissHo-mixed_proof.png", img.size)


if __name__ == "__main__":
    main()
