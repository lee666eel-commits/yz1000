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


# --- variance probe: is 冠/余 a sampling wobble or a model ceiling?
probe_chars = list("冠余互脑")   # 2 his deductions + 2 controls that came out clean
seeds = [1, 2, 3, 4, 5]
steps_list = [20, 50]
uname = lambda ch: f"U{ord(ch):04X}"
cp = lambda p: int(os.path.basename(p).split("+")[1][1:5], 16)
train_refs = [p for p in sorted(glob.glob(f"{DS}/data/train/TargetImage/MissHo/*.jpg")) if 0x4E00 <= cp(p) <= 0x9FFF]
ref = train_refs[len(train_refs) // 2]   # 机, same as v2 row 7
print("ref", chr(cp(ref)), flush=True)

def load(ckpt_dir, steps):
    sys.argv = ["sample.py", f"--ckpt_dir={ckpt_dir}", "--device=cuda:0",
                "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
                "--guidance_scale=7.5", f"--num_inference_steps={steps}", "--method=multistep"]
    a = sample.arg_parse()
    a.demo = False; a.save_image = False; a.save_image_dir = "/tmp/fd_cfg"; a.character_input = False
    assert hasattr(a, "seed"), "sample.py has no --seed; probe is meaningless"
    return a, sample.load_fontdiffuer_pipeline(a)

a, pipe = load(CKPT_FT, 20)
rows = []   # (label_img, [imgs])
truth = [Image.open(f"{DS}/eval/MissHo/{uname(c)}.jpg").convert("RGB").resize((CELL, CELL)) for c in probe_chars]
rows.append((None, truth))
for steps in steps_list:
    a.num_inference_steps = steps
    for seed in seeds:
        a.seed = seed
        imgs = []
        for c in probe_chars:
            a.style_image_path = ref
            a.content_image_path = f"{DS}/data/train/ContentImage/{uname(c)}.jpg"
            img = sample.sampling(a, pipe)
            img = (img or Image.new("RGB", (CELL, CELL), "red")).convert("RGB").resize((CELL, CELL))
            d = f"{OUT}/steps{steps}_seed{seed}"; os.makedirs(d, exist_ok=True); img.save(f"{d}/{uname(c)}.png")
            imgs.append(img)
        rows.append((f"s{steps} #{seed}", imgs))
        print("row done", steps, seed, flush=True)

LW = 70
sheet = Image.new("RGB", (LW + CELL * len(probe_chars), CELL * len(rows)), "white")
dr = ImageDraw.Draw(sheet)
for i, (lab, imgs) in enumerate(rows):
    dr.text((4, CELL * i + 40), lab or "real", fill="black")
    for j, im in enumerate(imgs):
        sheet.paste(im, (LW + CELL * j, CELL * i))
    dr.line([(0, CELL * i), (sheet.width, CELL * i)], fill="red", width=1)
sheet.save(f"{OUT}/probe_sheet.png")
open(f"{OUT}/README.txt", "w", encoding="utf-8").write("variance probe: chars " + "".join(probe_chars) + " | row0 real | then steps20 seeds1-5, steps50 seeds1-5 | ref 机 | ft ckpt\n")
print("done", flush=True)
