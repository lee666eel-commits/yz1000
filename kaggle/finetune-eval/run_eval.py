# yzqj -- eval-only rerun of the 09-19 fine-tune (no retrain). The v1 sheet picked style refs
# by sorted-filename first/mid/last, which landed on punctuation (《 ；); only the 机 row was a
# fair test and pretrained had no fair counterpart. This mounts ckpt_ft/ from the finetune
# kernel's output and regenerates the 60 held-out MissHo chars with three REAL-character refs,
# for both pretrained and fine-tuned weights. Push: kaggle kernels push -p D:/handwriting-font/kaggle/finetune-eval
import os, sys, glob, subprocess, functools

WORK = "/tmp/FontDiffuser"
OUT = "/kaggle/working/outputs"
CELL = 96


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


DS = CKPT_FT = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "heldout_missho.txt" in files:
        DS = root
    if root.endswith("ckpt_ft") and "unet.pth" in files:
        CKPT_FT = root
assert DS, "yzqj-finetune-data not mounted"
assert CKPT_FT, "ckpt_ft not mounted (kernel_sources must list yzqj-fontdiffuser-finetune)"
print("DS =", DS, "| CKPT_FT =", CKPT_FT, flush=True)
os.makedirs(OUT, exist_ok=True)

import torch
assert torch.cuda.is_available(), "no CUDA"
if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown"])
ckpt = f"{WORK}/ckpt"
if not os.path.exists(f"{ckpt}/unet.pth"):
    run(["gdown", "--folder", "https://drive.google.com/drive/folders/12hfuZ9MQvXqcteNuz7JQ2B_mUcTr-5jZ", "-O", ckpt])

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)
import sample  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


heldout = list(open(f"{DS}/heldout_missho.txt", encoding="utf-8").read().strip())
uname = lambda ch: f"U{ord(ch):04X}"
cp = lambda p: int(os.path.basename(p).split("+")[1][1:5], 16)
# real CJK only -- punctuation refs were the v1 flaw
train_refs = [p for p in sorted(glob.glob(f"{DS}/data/train/TargetImage/MissHo/*.jpg")) if 0x4E00 <= cp(p) <= 0x9FFF]
refs = [train_refs[i] for i in (0, len(train_refs) // 2, len(train_refs) - 1)]
ref_chars = [chr(cp(r)) for r in refs]
print("held-out", len(heldout), "real-char refs", ref_chars, flush=True)


def load(ckpt_dir):
    sys.argv = ["sample.py", f"--ckpt_dir={ckpt_dir}", "--device=cuda:0",
                "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
                "--guidance_scale=7.5", "--num_inference_steps=20", "--method=multistep"]
    a = sample.arg_parse()
    a.demo = False
    a.save_image = False
    a.save_image_dir = "/tmp/fd_cfg"
    a.character_input = False
    return a, sample.load_fontdiffuer_pipeline(a)


def gen_row(a, pipe, ref, tag):
    row = []
    d = f"{OUT}/{tag}"
    os.makedirs(d, exist_ok=True)
    for ch in heldout:
        a.style_image_path = ref
        a.content_image_path = f"{DS}/data/train/ContentImage/{uname(ch)}.jpg"
        img = sample.sampling(a, pipe)
        img = (img or Image.new("RGB", (CELL, CELL), "red")).convert("RGB").resize((CELL, CELL))
        img.save(f"{d}/{uname(ch)}.png")
        row.append(img)
    print("row done:", tag, len(row), flush=True)
    return row


content_row = [Image.open(f"{DS}/data/train/ContentImage/{uname(ch)}.jpg").convert("RGB").resize((CELL, CELL)) for ch in heldout]
truth_row = [Image.open(f"{DS}/eval/MissHo/{uname(ch)}.jpg").convert("RGB").resize((CELL, CELL)) for ch in heldout]

a0, p0 = load(ckpt)
pre_rows = [gen_row(a0, p0, r, f"pretrained_ref{i}") for i, r in enumerate(refs)]
del p0
torch.cuda.empty_cache()
a1, p1 = load(CKPT_FT)
ft_rows = [gen_row(a1, p1, r, f"finetuned_ref{i}") for i, r in enumerate(refs)]

rows = [content_row, truth_row] + pre_rows + ft_rows
labels = [None, None] + [Image.open(r) for r in refs] * 2
w = CELL * (len(heldout) + 1)
sheet = Image.new("RGB", (w, CELL * len(rows)), "white")
for i, (lab, row) in enumerate(zip(labels, rows)):
    if lab is not None:
        sheet.paste(lab.convert("RGB").resize((CELL, CELL)), (0, CELL * i))
    for j, im in enumerate(row):
        sheet.paste(im, (CELL * (j + 1), CELL * i))
d = ImageDraw.Draw(sheet)
d.line([(CELL, 0), (CELL, sheet.height)], fill="red", width=2)
for i in range(1, len(rows)):
    d.line([(0, CELL * i), (w, CELL * i)], fill="red", width=1)
sheet.save(f"{OUT}/sheet_missho_heldout.png")
open(f"{OUT}/README.txt", "w", encoding="utf-8").write(
    "rows: 1 content(Noto) | 2 MissHo real (held-out) | 3-5 pretrained ref " + " ".join(ref_chars) +
    " | 6-8 fine-tuned (09-19 ckpt_ft, 3000 steps) same refs\nheld-out chars: " + "".join(heldout) + "\n")
print("done. sheet in", OUT, flush=True)
