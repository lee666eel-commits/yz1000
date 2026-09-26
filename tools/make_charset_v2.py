"""Build the v2 character set: the words the 讲座 actually needs, then filler.

Two changes he asked for:
  - drop the over-specific proper nouns (his own name, the school's name)
  - carry the organisers / sponsors, and the Arabic digits the first set lacked
    ("乐中学AI 2.0" cannot be typed without 0-9, A, I and an ASCII dot)

Everything in REQUIRED must fit; the rest of the 100 cells is high-frequency
filler so the font can still set ordinary sentences.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REQUIRED_STRINGS = [
    "乐中学AI2.0",              # 讲座名，含阿拉伯数字与拉丁字母
    "星洲日报",                  # 主办
    "万能", "万能企业", "万能爱心",
    "怡保双威医疗中心",
    "霹雳惠州会馆",
    "維綠穀",                    # 依他写的繁体字形，不改简繁
    "主办方", "协办方", "赞助商",
    "0123456789",
    "。，、？！：",
]

DROP = set("林策南华独")          # 林子策 / 南华独中 —— 过于专指
# 子 中 学 校 教 师 生 都是通用字，留着

FILLER = (
    "的一是了我不人在他有这个上们来到时大地为说国年着就那和要出也得里后自"
    "以会可下而过天去能对小多然于心么之都好看起发当没成只如事把还用样道想"
    "作种开总从无情己面最但现前些所同日手又行意动方期头经长回位分老因很"
    "给名法间知世什两次使身高已进话常活正感文字写体校教师生学"
)


def build(count=100):
    seen, out = set(), []
    for s in REQUIRED_STRINGS:
        for ch in s:
            if ch in seen or ch.isspace():
                continue
            seen.add(ch); out.append(ch)
    required = len(out)
    if required > count:
        raise SystemExit(f"必写字 {required} 个已超过 {count} 格")
    for ch in FILLER:
        if len(out) >= count:
            break
        if ch in seen or ch in DROP or ch.isspace():
            continue
        seen.add(ch); out.append(ch)
    return out, required


if __name__ == "__main__":
    chars, required = build(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
    # coverage is the point of the file, so assert it here rather than trust it
    have = set(chars)
    for s in REQUIRED_STRINGS:
        missing = [c for c in s if c not in have]
        assert not missing, f"{s} 缺字: {missing}"
    assert not (have & DROP), f"专指字没拿掉: {have & DROP}"
    open("template-v2-chars.txt", "w", encoding="utf-8").write("".join(chars))
    print(f"共 {len(chars)} 字，其中必写 {required}，填充 {len(chars) - required}")
    print("必写：", "".join(chars[:required]))
    print("填充：", "".join(chars[required:]))
