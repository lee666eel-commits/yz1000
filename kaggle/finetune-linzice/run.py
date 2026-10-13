# yzqj -- "how few characters does a NEW hand need?" (林子策, template-merged M1/M3/M9 = 40% done, 10-13).
# Start point = ckpt_ft (the 09-19 joint fine-tune on three earlier participants), i.e. the question answered is
# "a new participant joining the existing pipeline", not "from scratch". Nested train subsets N=50/100/212
# (train_order_linzice.txt prefix), same steps each, eval at 500 and 1000 steps on 40 held-out chars he
# wrote but the model never saw. N=0 row = ckpt_ft with his ref glyph and no training (control).
# Push: kaggle kernels push -p D:/handwriting-font/kaggle/finetune-linzice
import os, sys, glob, subprocess, functools, shutil, time

WORK = "/tmp/FontDiffuser"
OUT = "/kaggle/working/outputs"
STYLE = "LinZiCe"
TIERS = [50, 100, 212]
STEPS = int(os.environ.get("FT_STEPS", "1000"))
EVAL_AT = [500, 1000]
CELL = 96
Q, NL = chr(34), chr(10)


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


DS = CKPT_FT = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "heldout_linzice.txt" in files:
        DS = root
    if root.endswith("ckpt_ft") and "unet.pth" in files:
        CKPT_FT = root
assert DS, "yzqj-finetune-linzice not mounted"
assert CKPT_FT, "ckpt_ft not mounted (kernel_sources must list yzqj-fontdiffuser-finetune)"
print("DS =", DS, "| CKPT_FT =", CKPT_FT, flush=True)
os.makedirs(OUT, exist_ok=True)

import torch
assert torch.cuda.is_available(), "no CUDA"
print("torch", torch.__version__, "gpu", torch.cuda.get_device_name(0), flush=True)
if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown", "tensorboard"])
ckpt_pre = f"{WORK}/ckpt"
if not os.path.exists(f"{ckpt_pre}/unet.pth"):
    run(["gdown", "--folder", "https://drive.google.com/drive/folders/12hfuZ9MQvXqcteNuz7JQ2B_mUcTr-5jZ", "-O", ckpt_pre])

# --- same two train.py patches as kaggle/finetune/run.py
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

uname = lambda ch: f"U{ord(ch):04X}"
heldout = list(open(f"{DS}/heldout_linzice.txt", encoding="utf-8").read().strip())
order = list(open(f"{DS}/train_order_linzice.txt", encoding="utf-8").read().strip())
assert not set(heldout) & set(order)
assert TIERS[-1] <= len(order), (TIERS, len(order))

# ref = the N50 glyph with median ink coverage, shared by every generated row (a real character, not punctuation)
from PIL import Image, ImageDraw  # noqa: E402
import numpy as np  # noqa: E402
tgt = lambda ch: f"{DS}/data/train/TargetImage/{STYLE}/{STYLE}+{uname(ch)}.jpg"
ink = sorted(order[:TIERS[0]], key=lambda ch: (np.asarray(Image.open(tgt(ch)).convert("L")) < 128).mean())
REF_CH = ink[len(ink) // 2]
REF = tgt(REF_CH)
print("ref char", uname(REF_CH), flush=True)

# --- train each tier from ckpt_ft
ckpts = {}
for n in TIERS:
    root = f"/tmp/data_n{n}"
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(f"{root}/train/TargetImage/{STYLE}")
    os.symlink(f"{DS}/data/train/ContentImage", f"{root}/train/ContentImage")
    for ch in order[:n]:
        os.symlink(tgt(ch), f"{root}/train/TargetImage/{STYLE}/{STYLE}+{uname(ch)}.jpg")
    out = f"/tmp/ft_n{n}"
    env = dict(os.environ, INIT_CKPT_DIR=CKPT_FT, PYTHONUNBUFFERED="1")
    t0 = time.time()
    run([sys.executable, "train.py", "--seed=123", f"--experience_name=ft_n{n}",
         f"--data_root={root}", f"--output_dir={out}", "--report_to=tensorboard",
         "--resolution=96", "--style_image_size=96", "--content_image_size=96",
         "--content_encoder_downsample_size=3", "--channel_attn=True",
         "--content_start_channel=64", "--style_start_channel=64",
         "--train_batch_size=8", "--perceptual_coefficient=0.01", "--offset_coefficient=0.5",
         f"--max_train_steps={STEPS}", f"--ckpt_interval={EVAL_AT[0]}", "--gradient_accumulation_steps=1",
         "--log_interval=50", "--learning_rate=1e-5", "--lr_scheduler=constant",
         "--lr_warmup_steps=0", "--drop_prob=0.1", "--mixed_precision=no"], cwd=WORK, env=env)
    print(f"N={n}: {(time.time() - t0) / 60:.1f} min for {STEPS} steps (~{STEPS * 8 / n:.0f} epochs)", flush=True)
    for s in EVAL_AT:
        d = f"{out}/global_step_{s}"
        assert os.path.exists(f"{d}/unet.pth"), d
        ckpts[(n, s)] = d
    if os.path.exists(f"{out}/fontdiffuser_training.log"):
        shutil.copy(f"{out}/fontdiffuser_training.log", f"{OUT}/train_log_n{n}.log")

# keep the largest tier's final weights: if he likes it, that is what a 2610-char generation would use
keep = "/kaggle/working/ckpt_linzice"
os.makedirs(keep, exist_ok=True)
for f in ["unet.pth", "style_encoder.pth", "content_encoder.pth"]:
    shutil.copy(f"{ckpts[(TIERS[-1], EVAL_AT[-1])]}/{f}", f"{keep}/{f}")

# --- eval
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)
import sample  # noqa: E402


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


def gen_row(ckpt_dir, tag):
    a, pipe = load(ckpt_dir)
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
    print("row done:", tag, len(row), flush=True)
    return row


rows = [("content", [Image.open(f"{DS}/data/train/ContentImage/{uname(ch)}.jpg").convert("RGB").resize((CELL, CELL)) for ch in heldout]),
        ("TRUTH (his)", [Image.open(tgt(ch)).convert("RGB").resize((CELL, CELL)) for ch in heldout]),
        ("pretrained", gen_row(ckpt_pre, "pretrained")),
        ("N=0 ckpt_ft", gen_row(CKPT_FT, "n0_ckpt_ft"))]
for n in TIERS:
    for s in EVAL_AT:
        rows.append((f"N={n} @{s}", gen_row(ckpts[(n, s)], f"n{n}_s{s}")))

LW = 120
sheet = Image.new("RGB", (LW + CELL * (len(heldout) + 1), CELL * len(rows)), "white")
dr = ImageDraw.Draw(sheet)
ref_im = Image.open(REF).convert("RGB").resize((CELL, CELL))
for i, (lab, row) in enumerate(rows):
    dr.text((6, CELL * i + 40), lab, fill="black")
    if i >= 2:
        sheet.paste(ref_im, (LW, CELL * i))
    for j, im in enumerate(row):
        sheet.paste(im, (LW + CELL * (j + 1), CELL * i))
    dr.line([(0, CELL * i), (sheet.width, CELL * i)], fill="red", width=1)
dr.line([(LW + CELL, 0), (LW + CELL, sheet.height)], fill="red", width=2)
sheet.save(f"{OUT}/sheet_linzice_heldout.png")
PER = 10
for k in range((len(heldout) + PER - 1) // PER):
    x0 = LW + CELL * (1 + PER * k)
    part = Image.new("RGB", (LW + CELL + CELL * PER, sheet.height), "white")
    part.paste(sheet.crop((0, 0, LW + CELL, sheet.height)), (0, 0))
    part.paste(sheet.crop((x0, 0, min(x0 + CELL * PER, sheet.width), sheet.height)), (LW + CELL, 0))
    part.save(f"{OUT}/sheet_part{k + 1}.png")
open(f"{OUT}/README.txt", "w", encoding="utf-8").write(
    "rows: " + " | ".join(l for l, _ in rows) + NL + "ref (col 1): " + REF_CH + NL +
    "held-out chars: " + "".join(heldout) + NL + "train order (N=prefix): " + "".join(order) + NL)
print("done. sheets in", OUT, flush=True)
