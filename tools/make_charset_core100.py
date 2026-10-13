# Pick the ~100 characters a new participant writes first (10-14 decision: >100 real glyphs makes the
# fine-tuned hand more uniform, 50-100 already carries the 笔性; 1000-char sheets scare people off).
# Goal: the 100 that teach the model the most about the 3500 通用规范一级 chars it must then generate.
#   feature = (top-level structure slot, component) e.g. ('⿰0','亻'), plus every deeper component
#   weight  = how many of the 3500 targets contain that feature  -> greedy max-coverage pick
#   pool    = chars from the school-corpus merged sheet (common, natural to write) + 永 (永字八法, forced)
# Prints coverage vs a random 100 from the same pool, so the claim "this pick is better" is measured.
# needs cjkvi-ids ids.txt (https://github.com/cjkvi/cjkvi-ids), path as argv[1].
import json, random, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = "D:/handwriting-font"
IDC = set("⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻")

ids = {}
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith("#"):
        continue
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3:
        ids[p[1]] = re.sub(r"\[[^\]]*\]", "", p[2])


def parse(s, i=0):
    """IDS string -> (idc, [children]) tree; leaf = char."""
    c = s[i]
    if c in IDC:
        n = 3 if c in "⿲⿳" else 2
        kids, j = [], i + 1
        for _ in range(n):
            k, j = parse(s, j)
            kids.append(k)
        return (c, kids), j
    return c, i + 1


def comps(ch, depth=0):
    d = ids.get(ch, ch)
    if d == ch or depth > 6:
        return {ch}
    try:
        tree, _ = parse(d)
    except IndexError:
        return {ch}
    out = set()

    def walk(t):
        if isinstance(t, tuple):
            for k in t[1]:
                walk(k)
        else:
            out.add(t)
            out.update(comps(t, depth + 1) if t != ch else set())
    walk(tree)
    return out


def feats(ch):
    d = ids.get(ch, ch)
    f = {("deep", c) for c in comps(ch)}
    try:
        tree, _ = parse(d) if d != ch else (ch, 0)
    except IndexError:
        tree = ch
    if isinstance(tree, tuple):
        f.add(("shape", tree[0]))
        for k, kid in enumerate(tree[1]):
            leaf = kid if not isinstance(kid, tuple) else d   # nested slot: key on the slot's own IDS
            f.add((f"{tree[0]}{k}", leaf if isinstance(leaf, str) and len(leaf) == 1 else str(kid)))
    else:
        f.add(("shape", "独体"))
    return f


universe = [c for c in open(f"{ROOT}/chars-3500-level1.txt", encoding="utf-8").read() if not c.isspace()]
F = {c: feats(c) for c in universe}
weight = {}
for fs in F.values():
    for x in fs:
        weight[x] = weight.get(x, 0) + 1

man = json.load(open(f"{ROOT}/template-merged/manifest.json", encoding="utf-8"))
pool = [c["char"] for s in man["sheets"] for c in s["cells"] if 0x4E00 <= ord(c["char"]) <= 0x9FFF and c["char"] in F]
pool = list(dict.fromkeys(["永"] + pool))


def coverage(chosen):
    cov = set().union(*(F[c] for c in chosen))
    w = sum(weight[x] for x in cov) / sum(weight.values())
    # a target char is "fully seen" if every top-level slot component was written somewhere
    full = sum(all(x in cov for x in F[c] if x[0] != "deep") for c in universe)
    return w, full


def greedy(n):
    chosen, cov = ["永"], set(F["永"])
    while len(chosen) < n:
        best = max((c for c in pool if c not in chosen), key=lambda c: (sum(weight[x] for x in F[c] - cov), -pool.index(c)))
        chosen.append(best)
        cov |= F[best]
    return chosen


N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
pick = greedy(N)
w, full = coverage(pick)
rnd = [coverage(random.Random(s).sample(pool, N)) for s in range(20)]
print(f"pool {len(pool)} | picked {len(pick)}")
print(f"greedy : weighted feature coverage {w:.3f} | 3500 targets with every slot-component seen: {full}")
print(f"random : weighted {sum(r[0] for r in rnd) / 20:.3f} | slot-complete {sum(r[1] for r in rnd) / 20:.0f}  (mean of 20 draws)")
shapes = {}
for c in pick:
    s = next((x[1] for x in F[c] if x[0] == "shape"), "?")
    shapes[s] = shapes.get(s, 0) + 1
print("structures:", shapes)
open(f"{ROOT}/chars-core100.txt", "w", encoding="utf-8").write("".join(pick) + "\n")
print("".join(pick))
