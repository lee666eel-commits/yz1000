"""Which characters of a text does a built font actually have?

    python tools\\coverage.py --font build\\LinHand.ttf --text D:\\...\\booklet.html

Answers the only question that matters before typesetting with a 1:1 traced
font: what falls back to a different typeface and gives the game away.
HTML input is stripped of tags, <script>/<style> bodies and entities first,
so the count reflects visible copy rather than markup.
"""
import argparse
import io
import re
import sys
from collections import Counter

from fontTools.ttLib import TTFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CJK = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")


def visible_text(raw, is_html):
    if not is_html:
        return raw
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"&[#\w]+;", " ", raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--text", required=True, nargs="+")
    ap.add_argument("--top", type=int, default=40,
                    help="how many missing characters to list, most frequent first")
    a = ap.parse_args()

    have = set(TTFont(a.font).getBestCmap())
    counts = Counter()
    for path in a.text:
        raw = io.open(path, encoding="utf-8", errors="replace").read()
        counts.update(c for c in visible_text(raw, path.lower().endswith(("html", "htm")))
                      if CJK.match(c))

    total = sum(counts.values())
    if not total:
        raise SystemExit("no CJK characters found in the input")
    missing = Counter({c: n for c, n in counts.items() if ord(c) not in have})
    covered = total - sum(missing.values())

    print(f"font    : {a.font}  ({len(have)} codepoints)")
    print(f"text    : {total} CJK chars, {len(counts)} distinct")
    print(f"covered : {covered}/{total} = {covered / total:.1%} of characters "
          f"({len(counts) - len(missing)}/{len(counts)} distinct)")
    print(f"missing : {len(missing)} distinct, {sum(missing.values())} occurrences")
    if missing:
        print("top missing (char x count):")
        print("  " + "  ".join(f"{c}x{n}" for c, n in missing.most_common(a.top)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
