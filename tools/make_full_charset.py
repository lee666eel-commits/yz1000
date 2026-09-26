"""Build the character list for a full printable "every-character-real" font.

Two inputs, no guessing:
1. GB2312 level-1 table (3755 chars) — mechanically derived from the GB2312
   encoding range (area 16-55), not typed from memory. This is the closest
   thing to a hallucination-proof "national standard common-char list"; the
   newer 通用规范汉字表一级(3500字) is close but not identical and its exact
   member list was NOT typed from memory here on purpose — cross-check
   against the official 教育部语言文字应用研究所 table before using that
   exact name in any customer-facing claim.
2. His own corpus (nanhwafs-site posts.json) for frequency ranking, so the
   writing order matches what he/the school actually use most, same method
   as the 09-03 900-char extension.

Output: remaining chars (not yet in any already-written set), ranked by
corpus frequency first, then by GB2312 pinyin order for chars the corpus
never used (guarantees the national-standard floor is still fully covered).
"""
import io
import json
import re
from collections import Counter


def gb2312_level1():
    """3755 hanzi, area 16-55, GB2312 high byte 0xB0-0xD7."""
    chars = []
    for hi in range(0xB0, 0xD8):
        for lo in range(0xA1, 0xFF):
            try:
                b = bytes([hi, lo])
                ch = b.decode("gb2312")
            except UnicodeDecodeError:
                continue
            if len(ch) == 1 and "\u4e00" <= ch <= "\u9fff":
                chars.append(ch)
    return chars


def already_written():
    import sys
    sys.path.insert(0, "D:/handwriting-font/tools")
    import make_template as mt
    v1 = set(mt.PILOT_CHARS[:100])  # --count 100 default, what LinHand.ttf actually has
    v2 = set(io.open("D:/handwriting-font/template-v2-chars.txt", encoding="utf-8").read())
    ext900 = set(io.open("D:/handwriting-font/chars-ext900.txt", encoding="utf-8").read())
    return v1 | v2 | ext900, v1, v2, ext900


CJK = re.compile(r"[\u4e00-\u9fff]")


def corpus_freq(path):
    posts = json.load(io.open(path, encoding="utf-8"))
    counts = Counter()
    items = posts if isinstance(posts, list) else posts.get("posts", posts.get("items", []))
    for p in items:
        text = ""
        if isinstance(p, dict):
            for k in ("content", "text", "body", "message"):
                if k in p and isinstance(p[k], str):
                    text += p[k]
        elif isinstance(p, str):
            text = p
        counts.update(c for c in text if CJK.match(c))
    return counts


def main():
    gb1 = gb2312_level1()
    written, v1, v2, ext900 = already_written()
    freq = corpus_freq("C:/dev/nanhwafs-site/data/posts.json")

    remaining = [c for c in gb1 if c not in written]
    remaining_sorted = sorted(remaining, key=lambda c: (-freq.get(c, 0), gb1.index(c)))

    out_all = "D:/handwriting-font/chars-full-gb1-remaining.txt"
    with io.open(out_all, "w", encoding="utf-8") as f:
        f.write("".join(remaining_sorted))

    # tiers matching the existing 900-char sheet cadence (108/sheet, 9 sheets ~ done)
    for tier_n in (900, 1800, 2700):
        tier = remaining_sorted[:tier_n]
        path = f"D:/handwriting-font/chars-full-tier{tier_n}.txt"
        with io.open(path, "w", encoding="utf-8") as f:
            f.write("".join(tier))
        print(f"{path}: {len(tier)} chars")

    covered_by_corpus = sum(freq.values())
    corpus_distinct = len(freq)
    already_in_corpus = sum(n for c, n in freq.items() if c in written)
    print(f"\nGB2312 level-1: {len(gb1)} chars")
    print(f"already written (v1∪v2∪ext900, dedup): {len(written)} chars "
          f"(v1={len(v1)} v2={len(v2)} ext900={len(ext900)})")
    print(f"remaining to cover GB2312 level-1 floor: {len(remaining)} chars")
    print(f"corpus: {corpus_distinct} distinct chars, {covered_by_corpus} occurrences")
    if covered_by_corpus:
        print(f"corpus coverage by already-written set: "
              f"{already_in_corpus / covered_by_corpus:.1%}")
    out_of_gb1 = [c for c in freq if c not in gb1]
    if out_of_gb1:
        oob_occ = sum(freq[c] for c in out_of_gb1)
        print(f"corpus chars outside GB2312 level-1: {len(out_of_gb1)} distinct, "
              f"{oob_occ} occurrences ({oob_occ / covered_by_corpus:.2%}) — "
              f"these need a manual add-on list, not covered by the national floor")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
