"""Build the charset for the 英文字母/阿拉伯数字/标点 add-on sheet.

None of the existing tier files (donor-target-charset.txt, chars-full-tier*,
chars-ext900.txt, chars-addon-outside-gb1.txt, template-v2-chars.txt) contain
a single ASCII letter, digit, or punctuation mark -- verified by grep, not
assumed. Those code points in the shipped font are all filler-font glyphs,
never his hand, which is the "违和感" in the 2026-09-25 proof render. Same
fix as every other gap in this project: donor writes it, the pipeline traces
it. No AI substitute for this category exists yet.

Three categories, matching the letter sent to 何小姐:
  - 26 English letters (both cases -- a font needs both, "26个字母" in the
    letter is the everyday count, not a claim that lowercase is skipped)
  - 0-9 Arabic digits
  - punctuation: half-width ASCII (for English/code mixed into Chinese text)
    + full-width Chinese (for ordinary prose) -- both are distinct glyphs a
    font must carry separately.
"""
import sys

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT_ASCII = ".,!?:;'\"()-/@%"
PUNCT_FULLWIDTH = "。，、；：？！“”‘’（）《》—…"

REQUIRED_STRINGS = [UPPER, LOWER, DIGITS, PUNCT_ASCII, PUNCT_FULLWIDTH]


def build():
    seen, out = set(), []
    for s in REQUIRED_STRINGS:
        for ch in s:
            if ch in seen:
                continue
            seen.add(ch)
            out.append(ch)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    chars = build()
    have = set(chars)
    for s in REQUIRED_STRINGS:
        missing = [c for c in s if c not in have]
        assert not missing, f"缺字: {missing}"
    open("chars-latin-punct.txt", "w", encoding="utf-8").write("".join(chars))
    print(f"共 {len(chars)} 格：大写{len(UPPER)} 小写{len(LOWER)} "
          f"数字{len(DIGITS)} 半形标点{len(PUNCT_ASCII)} 全形标点{len(PUNCT_FULLWIDTH)}")
