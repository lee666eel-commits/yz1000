# yzqj -- build the Kaggle dataset for the 林子策 "minimum characters" fine-tune test.
# Source: build/linzice-40pct/debug cell crops (template-merged M1/M3/M9, CamScanner scan, red-grid whitened,
# 境 blacked out by him -> blank). TargetImage recipe matches finetune-data (debug crop -> LANCZOS 128px RGB jpg,
# measured 10-13 on another participant's 机/三/龙: mean abs diff 0.11-0.20 vs 0.35+ for other filters).
# Cells with a printed frame line surviving at the edge are dropped so the held-out truth row is clean.
import glob, os, random, shutil, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = "D:/handwriting-font"
SRC = f"{ROOT}/build/linzice-40pct/debug"
OLD = f"{ROOT}/kaggle/finetune-data/data/train/ContentImage"
OUT = f"{ROOT}/kaggle/finetune-linzice-data"
STYLE = "LinZiCe"

crops = {int(p[-8:-4], 16): p for p in glob.glob(f"{SRC}/M*_r*_*.png")}
cjk = sorted(c for c in crops if 0x4E00 <= c <= 0x9FFF)


def edge_line(p):
    a = np.asarray(Image.open(p).convert("L")) < 128
    n = a.shape[0]
    b = int(n * 0.07)
    return max(a[:b].sum(1).max(), a[-b:].sum(1).max(), a[:, :b].sum(0).max(), a[:, -b:].sum(0).max()) > 0.45 * n


dirty = [c for c in cjk if edge_line(crops[c])]
clean = [c for c in cjk if c not in dirty]
rng = random.Random(20261013)
rng.shuffle(clean)
heldout, train = clean[:40], clean[40:]          # train order = nesting order: N50 = train[:50], N100 = train[:100]

for d in ("data/train/ContentImage", f"data/train/TargetImage/{STYLE}"):
    shutil.rmtree(f"{OUT}/{d}", ignore_errors=True)
    os.makedirs(f"{OUT}/{d}")
for c in heldout + train:
    u = f"U{c:04X}"
    shutil.copy(f"{OLD}/{u}.jpg", f"{OUT}/data/train/ContentImage/{u}.jpg")   # all 263 present in the 908 set
    Image.open(crops[c]).convert("L").resize((128, 128), Image.LANCZOS).convert("RGB").save(
        f"{OUT}/data/train/TargetImage/{STYLE}/{STYLE}+{u}.jpg", quality=95)
open(f"{OUT}/heldout_linzice.txt", "w", encoding="utf-8").write("".join(map(chr, heldout)))
open(f"{OUT}/train_order_linzice.txt", "w", encoding="utf-8").write("".join(map(chr, train)))
print("cjk", len(cjk), "| dropped edge-line", len(dirty), "".join(map(chr, dirty)))
print("heldout", len(heldout), "".join(map(chr, heldout)))
print("train pool", len(train), "| N50 =", "".join(map(chr, train[:50])))
n_t = len(glob.glob(f"{OUT}/data/train/TargetImage/{STYLE}/*.jpg"))
n_c = len(glob.glob(f"{OUT}/data/train/ContentImage/*.jpg"))
assert n_t == n_c == len(heldout) + len(train), (n_t, n_c)
print("written (measured):", n_t, "target /", n_c, "content")
