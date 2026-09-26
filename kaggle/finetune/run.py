# yzqj -- FontDiffuser per-participant fine-tune (Kaggle GPU, script kernel)
# Train: 3 hands (0005MissHo / 0010Phoon / LiuJiaRui, 908 real glyphs each, MissHo minus 60
# held-out chars) starting from the pretrained weights. Eval: the 60 MissHo chars the model
# never saw, side by side with her real glyphs -- the only sheet that can answer "does it
# look like her hand". Push: kaggle kernels push -p D:/handwriting-font/kaggle/finetune
import os, sys, glob, subprocess, functools, shutil, time

WORK = "/tmp/FontDiffuser"
OUT = "/kaggle/working/outputs"
FT = "/tmp/ft"                      # training output; only the final ckpt is copied to /kaggle/working
STEPS = int(os.environ.get("FT_STEPS", "3000"))
BATCH = 8
LR = "1e-5"
CELL = 96
Q = chr(34)
NL = chr(10)


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


DS = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "heldout_missho.txt" in files:
        DS = root
        break
assert DS, "yzqj-finetune-data not mounted"
print("DS =", DS, flush=True)
os.makedirs(OUT, exist_ok=True)

import torch
assert torch.cuda.is_available(), "no CUDA"
print("torch", torch.__version__, "gpu", torch.cuda.get_device_name(0), flush=True)

if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown", "tensorboard"])
ckpt = f"{WORK}/ckpt"
if not os.path.exists(f"{ckpt}/unet.pth"):
    run(["gdown", "--folder", "https://drive.google.com/drive/folders/12hfuZ9MQvXqcteNuz7JQ2B_mUcTr-5jZ", "-O", ckpt])

# --- patch train.py: (a) torch>=2.6 weights_only default, (b) phase-1 init from a ckpt dir
tp = f"{WORK}/train.py"
t = open(tp, encoding="utf-8").read()
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

# --- train
env = dict(os.environ, INIT_CKPT_DIR=ckpt, PYTHONUNBUFFERED="1")
t0 = time.time()
run([sys.executable, "train.py", "--seed=123", "--experience_name=ft_yzqj",
     f"--data_root={DS}/data", f"--output_dir={FT}", "--report_to=tensorboard",
     "--resolution=96", "--style_image_size=96", "--content_image_size=96",
     "--content_encoder_downsample_size=3", "--channel_attn=True",
     "--content_start_channel=64", "--style_start_channel=64",
     f"--train_batch_size={BATCH}", "--perceptual_coefficient=0.01", "--offset_coefficient=0.5",
     f"--max_train_steps={STEPS}", "--ckpt_interval=1000", "--gradient_accumulation_steps=1",
     "--log_interval=50", f"--learning_rate={LR}", "--lr_scheduler=constant",
     "--lr_warmup_steps=0", "--drop_prob=0.1", "--mixed_precision=no"], cwd=WORK, env=env)
print(f"training wall time: {(time.time() - t0) / 60:.1f} min for {STEPS} steps", flush=True)

steps_dirs = sorted(glob.glob(f"{FT}/global_step_*"), key=lambda p: int(p.rsplit("_", 1)[1]))
assert steps_dirs, "no checkpoint written"
final = steps_dirs[-1]
ckpt_out = "/kaggle/working/ckpt_ft"
os.makedirs(ckpt_out, exist_ok=True)
for n in ["unet.pth", "style_encoder.pth", "content_encoder.pth"]:
    shutil.copy(f"{final}/{n}", f"{ckpt_out}/{n}")
if os.path.exists(f"{FT}/fontdiffuser_training.log"):
    shutil.copy(f"{FT}/fontdiffuser_training.log", f"{OUT}/fontdiffuser_training.log")
print("final ckpt:", final, "->", ckpt_out, flush=True)

# --- eval on held-out MissHo chars
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)
import sample  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

heldout = list(open(f"{DS}/heldout_missho.txt", encoding="utf-8").read().strip())
uname = lambda ch: f"U{ord(ch):04X}"
train_refs = sorted(glob.glob(f"{DS}/data/train/TargetImage/MissHo/*.jpg"))
refs = [train_refs[i] for i in (0, len(train_refs) // 2, len(train_refs) - 1)]
print("held-out", len(heldout), "refs", [os.path.basename(r) for r in refs], flush=True)


def load(ckpt_dir):
    sys.argv = ["sample.py", f"--ckpt_dir={ckpt_dir}", "--device=cuda:0",
                "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
                "--guidance_scale=7.5", "--num_inference_steps=20", "--method=multistep"]
    a = sample.arg_parse()
    a.demo = False
    a.save_image = False
    a.save_image_dir = "/tmp/fd_cfg"
    a.character_input = False           # content comes from the dataset ContentImage jpg
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
pre_row = gen_row(a0, p0, refs[0], "pretrained_ref0")
del p0
torch.cuda.empty_cache()
a1, p1 = load(ckpt_out)
ft_rows = [gen_row(a1, p1, r, f"finetuned_ref{i}") for i, r in enumerate(refs)]

rows = [content_row, truth_row, pre_row] + ft_rows
labels = [None, None, Image.open(refs[0]), Image.open(refs[0]), Image.open(refs[1]), Image.open(refs[2])]
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
half = CELL * 31
sheet.crop((0, 0, half, sheet.height)).save(f"{OUT}/sheet_missho_heldout_a.png")
right = Image.new("RGB", (half, sheet.height), "white")
right.paste(sheet.crop((0, 0, CELL, sheet.height)), (0, 0))
right.paste(sheet.crop((half, 0, w, sheet.height)), (CELL, 0))
right.save(f"{OUT}/sheet_missho_heldout_b.png")
open(f"{OUT}/README.txt", "w", encoding="utf-8").write(
    "rows: 1 content(Noto) | 2 MissHo real (held-out, never trained) | 3 pretrained one-shot ref0 | "
    "4-6 fine-tuned with ref0/ref1/ref2" + NL + "held-out chars: " + "".join(heldout) + NL)
print("done. sheets in", OUT, flush=True)
