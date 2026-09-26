"""Chars his real corpus uses that GB2312 level-1 misses entirely — mostly
proper nouns (place/school names, traditional variants). Small list, high
personal relevance, worth a dedicated add-on sheet on top of the national floor.
"""
import io
import json
import re
from collections import Counter

CJK = re.compile(r"[\u4e00-\u9fff]")


def gb2312_level1():
    chars = set()
    for hi in range(0xB0, 0xD8):
        for lo in range(0xA1, 0xFF):
            try:
                ch = bytes([hi, lo]).decode("gb2312")
            except UnicodeDecodeError:
                continue
            if len(ch) == 1 and "\u4e00" <= ch <= "\u9fff":
                chars.add(ch)
    return chars


posts = json.load(io.open("C:/dev/nanhwafs-site/data/posts.json", encoding="utf-8"))
items = posts if isinstance(posts, list) else posts.get("posts", posts.get("items", []))
counts = Counter()
for p in items:
    text = ""
    if isinstance(p, dict):
        for k in ("content", "text", "body", "message"):
            if k in p and isinstance(p[k], str):
                text += p[k]
    elif isinstance(p, str):
        text = p
    counts.update(c for c in text if CJK.match(c))

gb1 = gb2312_level1()
already = set(io.open("D:/handwriting-font/template-v2-chars.txt", encoding="utf-8").read()) \
    | set(io.open("D:/handwriting-font/chars-ext900.txt", encoding="utf-8").read())
import sys
sys.path.insert(0, "D:/handwriting-font/tools")
import make_template as mt
already |= set(mt.PILOT_CHARS[:100])

addon = [c for c, n in counts.most_common() if c not in gb1 and c not in already]
io.open("D:/handwriting-font/chars-addon-outside-gb1.txt", "w", encoding="utf-8").write("".join(addon))
print(f"addon chars: {len(addon)}", file=sys.stderr if False else sys.stdout)
