# yzqj -- follow-up to linzice-minchars v1 (10-13): are the N=212 flaws caused by dirty training glyphs?
# 111 of the 212 train glyphs carry specks (grid-dash / frame residue: ink components < 8px at 96px).
# Two arms, both from ckpt_ft, 1000 steps, same hyper-params as v1:
#   clean101 = only the 101 speck-free glyphs  -> compare with v1 N=100 (same count, half dirty)
#   desp212  = all 212 glyphs, specks erased    -> compare with v1 N=212 (same chars, dirty)
# v1 rows are reused from the v1 kernel output; N=212 is ALSO regenerated from v1's ckpt_linzice to
# check that sampling is reproducible (if it is not, reused v1 rows are only roughly comparable).
# Push: kaggle kernels push -p D:/handwriting-font/kaggle/finetune-linzice-clean
import os, sys, glob, subprocess, functools, shutil, time

WORK = "/tmp/FontDiffuser"
OUT = "/kaggle/working/outputs"
STYLE = "LinZiCe"
STEPS = 1000
CELL = 96
Q, NL = chr(34), chr(10)


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


DS = CKPT_FT = CKPT_212 = V1 = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "heldout_linzice.txt" in files:
        DS = root
    if root.endswith("ckpt_ft") and "unet.pth" in files:
        CKPT_FT = root
    if root.endswith("ckpt_linzice") and "unet.pth" in files:
        CKPT_212 = root
    if root.endswith("n100_s1000") and files:
        V1 = os.path.dirname(root)
assert DS and CKPT_FT and CKPT_212 and V1, (DS, CKPT_FT, CKPT_212, V1)
print("DS", DS, "| ft", CKPT_FT, "| 212", CKPT_212, "| v1", V1, flush=True)
os.makedirs(OUT, exist_ok=True)

import torch
assert torch.cuda.is_available(), "no CUDA"
if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown", "tensorboard"])
os.makedirs(f"{WORK}/ckpt", exist_ok=True)   # sample.py arg defaults only; pretrained weights not needed

tp = f"{WORK}/train.py"
t = open(tp, encoding="utf-8").read()
if "INIT_CKPT_DIR" not in t:
    t = t.replace("import torch" + NL, "import torch" + NL + "import functools" + NL + "torch.load = functools.partial(torch.load, weights_only=False)" + NL, 1)
    anchor = "    model = FontDiffuserModel("
    assert anchor in t
    init_block = NL.join([
        "    if os.environ.get(@INIT_CKPT_DIR@):",
        "        _d = os.environ[@INIT_CKPT_DIR@]",
        "        unet.load_state_dict(torch.load(f@{_d}/unet.pth@))",
        "        style_encoder.load_state_dict(torch.load(f@{_d}/style_encoder.pth@))",
        "        content_encoder.load_state_dict(torch.load(f@{_d}/content_encoder.pth@))",
        "        print(@initialised from@, _d, flush=True)",
        ""]).replace("@", Q)
    t = t.replace(anchor, init_block + anchor, 1)
    open(tp, "w", encoding="utf-8").write(t)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

uname = lambda ch: f"U{ord(ch):04X}"
heldout = list(open(f"{DS}/heldout_linzice.txt", encoding="utf-8").read().strip())
order = list(open(f"{DS}/train_order_linzice.txt", encoding="utf-8").read().strip())
tgt = lambda ch: f"{DS}/data/train/TargetImage/{STYLE}/{STYLE}+{uname(ch)}.jpg"


def specks(ch):   # same definition as the local count (10-13): components < 8px after resize to 96
    a = (cv2.resize(cv2.imread(tgt(ch), 0), (96, 96)) < 128).astype(np.uint8)
    st = cv2.connectedComponentsWithStats(a)[2]
    return int((st[1:, 4] < 8).sum())


clean = [ch for ch in order if specks(ch) == 0]
print("clean", len(clean), "of", len(order), flush=True)
assert len(clean) == 101, len(clean)

# ref = 堂 as in v1 (it is in v1's N50 set); must stay the same so rows are comparable
REF_CH = "堂"
REF = tgt(REF_CH)


def despeckle(src, dst):   # erase components < 8px-at-96 (= < 14px at 128) to white; strokes untouched
    g = cv2.imread(src, 0)
    a = (g < 128).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a)
    small = [i for i in range(1, n) if st[i, 4] < 14]
    g[np.isin(lab, small)] = 255
    cv2.imwrite(dst, cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
    return len(small)


arms = {}
for name, chars, desp in [("clean101", clean, False), ("desp212", order, True)]:
    root = f"/tmp/data_{name}"
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(f"{root}/train/TargetImage/{STYLE}")
    os.symlink(f"{DS}/data/train/ContentImage", f"{root}/train/ContentImage")
    erased = 0
    for ch in chars:
        dst = f"{root}/train/TargetImage/{STYLE}/{STYLE}+{uname(ch)}.jpg"
        if desp:
            erased += despeckle(tgt(ch), dst)
        else:
            os.symlink(tgt(ch), dst)
    print(name, len(chars), "glyphs, specks erased:", erased, flush=True)
    if desp:
        left = sum(1 for p in glob.glob(f"{root}/train/TargetImage/{STYLE}/*.jpg")
                   if (cv2.connectedComponentsWithStats((cv2.resize(cv2.imread(p, 0), (96, 96)) < 128).astype(np.uint8))[2][1:, 4] < 8).any())
        print(name, "glyphs still specky after erase (jpg/resize re-creates some):", left, flush=True)
    out = f"/tmp/ft_{name}"
    env = dict(os.environ, INIT_CKPT_DIR=CKPT_FT, PYTHONUNBUFFERED="1")
    t0 = time.time()
    run([sys.executable, "train.py", "--seed=123", f"--experience_name=ft_{name}",
         f"--data_root={root}", f"--output_dir={out}", "--report_to=tensorboard",
         "--resolution=96", "--style_image_size=96", "--content_image_size=96",
         "--content_encoder_downsample_size=3", "--channel_attn=True",
         "--content_start_channel=64", "--style_start_channel=64",
         "--train_batch_size=8", "--perceptual_coefficient=0.01", "--offset_coefficient=0.5",
         f"--max_train_steps={STEPS}", f"--ckpt_interval={STEPS}", "--gradient_accumulation_steps=1",
         "--log_interval=50", "--learning_rate=1e-5", "--lr_scheduler=constant",
         "--lr_warmup_steps=0", "--drop_prob=0.1", "--mixed_precision=no"], cwd=WORK, env=env)
    print(f"{name}: {(time.time() - t0) / 60:.1f} min", flush=True)
    arms[name] = f"{out}/global_step_{STEPS}"
    assert os.path.exists(f"{arms[name]}/unet.pth"), arms[name]

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)
import sample  # noqa: E402


def gen_row(ckpt_dir, tag):
    sys.argv = ["sample.py", f"--ckpt_dir={ckpt_dir}", "--device=cuda:0",
                "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
                "--guidance_scale=7.5", "--num_inference_steps=20", "--method=multistep"]
    a = sample.arg_parse()
    a.demo = False
    a.save_image = False
    a.save_image_dir = "/tmp/fd_cfg"
    a.character_input = False
    pipe = sample.load_fontdiffuer_pipeline(a)
    d = f"{OUT}/{tag}"
    os.makedirs(d, exist_ok=True)
    row = []
    for ch in heldout:
        a.style_image_path = REF
        a.content_image_path = f"{DS}/data/train/ContentImage/{uname(ch)}.jpg"
        img = sample.sampling(a, pipe)
        img = (img or Image.new("RGB", (CELL, CELL), "red")).convert("RGB").resize((CELL, CELL))
        img.save(f"{d}/{uname(ch)}.png")
        row.append(img)
    del pipe
    torch.cuda.empty_cache()
    print("row done:", tag, flush=True)
    return row


v1row = lambda tag: [Image.open(f"{V1}/{tag}/{uname(ch)}.png").convert("RGB") for ch in heldout]
re212 = gen_row(CKPT_212, "n212_s1000_regen")
diff = np.mean([np.abs(np.asarray(a, int) - np.asarray(b, int)).mean() for a, b in zip(re212, v1row("n212_s1000"))])
print(f"reproducibility: mean abs pixel diff regen vs v1 N=212 = {diff:.2f} (0 = identical)", flush=True)

rows = [("TRUTH (his)", [Image.open(tgt(ch)).convert("RGB").resize((CELL, CELL)) for ch in heldout]),
        ("v1 N=100 mixed", v1row("n100_s1000")),
        ("clean101", gen_row(arms["clean101"], "clean101_s1000")),
        ("v1 N=212 dirty", v1row("n212_s1000")),
        ("desp212", gen_row(arms["desp212"], "desp212_s1000"))]

LW = 120
sheet = Image.new("RGB", (LW + CELL * (len(heldout) + 1), CELL * len(rows)), "white")
dr = ImageDraw.Draw(sheet)
ref_im = Image.open(REF).convert("RGB").resize((CELL, CELL))
for i, (lab, row) in enumerate(rows):
    dr.text((6, CELL * i + 40), lab, fill="black")
    if i >= 1:
        sheet.paste(ref_im, (LW, CELL * i))
    for j, im in enumerate(row):
        sheet.paste(im, (LW + CELL * (j + 1), CELL * i))
    dr.line([(0, CELL * i), (sheet.width, CELL * i)], fill="red", width=1)
dr.line([(LW + CELL, 0), (LW + CELL, sheet.height)], fill="red", width=2)
sheet.save(f"{OUT}/sheet_clean_vs_dirty.png")
PER = 10
for k in range((len(heldout) + PER - 1) // PER):
    x0 = LW + CELL * (1 + PER * k)
    part = Image.new("RGB", (LW + CELL + CELL * PER, sheet.height), "white")
    part.paste(sheet.crop((0, 0, LW + CELL, sheet.height)), (0, 0))
    part.paste(sheet.crop((x0, 0, min(x0 + CELL * PER, sheet.width), sheet.height)), (LW + CELL, 0))
    part.save(f"{OUT}/sheet_part{k + 1}.png")
open(f"{OUT}/README.txt", "w", encoding="utf-8").write(
    "rows: " + " | ".join(l for l, _ in rows) + NL + f"regen-vs-v1 pixel diff: {diff:.2f}" + NL +
    "clean101 chars: " + "".join(clean) + NL)
print("done", flush=True)
