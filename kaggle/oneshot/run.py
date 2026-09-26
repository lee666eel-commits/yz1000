# 遗字千金 -- FontDiffuser one-shot calibration run (Kaggle GPU, script kernel)
#
# Pushed with `kaggle kernels push -p D:\handwriting-font\kaggle\oneshot`, results pulled
# with `kaggle kernels output lucaslimzzce/yzqj-fontdiffuser-oneshot -p <dir>`.
# Same acceptance rule as the 09-03 SDT test: a glyph must be BOTH recognisable AND look
# like the writer's hand. This run only measures how much better FontDiffuser's pretrained
# base is than SDT; it does not answer "can we approach the participant's hand" -- that
# needs a per-participant fine-tune on their ~900 real glyphs.
import os, sys, glob, subprocess, functools

WORK = "/tmp/FontDiffuser"   # keep clone+ckpt out of /kaggle/working so the version output is results only

# dataset mount path is not guaranteed to equal the slug (v1 died on a hard-coded path): locate it
STYLE_ROOT = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "test_chars.txt" in files:
        STYLE_ROOT = root
        break
print("/kaggle/input tree:", [(r, d, f[:5]) for r, d, f in os.walk("/kaggle/input")][:20], flush=True)
assert STYLE_ROOT, "fontdiffuser-package dataset not mounted (no test_chars.txt under /kaggle/input)"
print("STYLE_ROOT =", STYLE_ROOT, flush=True)
OUT = "/kaggle/working/outputs"
CELL = 96


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


import torch
assert torch.cuda.is_available(), "no CUDA: enable_gpu must be true in kernel-metadata.json"
print("torch", torch.__version__, "gpu", torch.cuda.get_device_name(0), flush=True)

if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
# ponytail: requirements.txt pins transformers==4.33.1 -> tokenizers source build -> fails on
# Kaggle's python (that is exactly where the 09-08 run died). sample.py's import chain never
# touches transformers or gradio, so install only what it does import.
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown"])

ckpt = f"{WORK}/ckpt"
if not os.path.exists(f"{ckpt}/unet.pth"):
    run(["gdown", "--folder", "https://drive.google.com/drive/folders/12hfuZ9MQvXqcteNuz7JQ2B_mUcTr-5jZ", "-O", ckpt])
print("ckpt files:", os.listdir(ckpt), flush=True)

# content font: repo ships no ttf/ (README points at a BaiduYun link). Neutral print face so the
# structure input carries no second handwriting style.
ttf = f"{WORK}/ttf/NotoSansSC.ttf"
os.makedirs(f"{WORK}/ttf", exist_ok=True)
if not os.path.exists(ttf):
    run(["curl", "-sL", "-o", ttf, "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf"])

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)  # author ckpt, torch>=2.6 default flipped
import sample  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

sys.argv = ["sample.py", f"--ckpt_dir={ckpt}", "--character_input", "--device=cuda:0",
            f"--ttf_path={ttf}", "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
            "--guidance_scale=7.5", "--num_inference_steps=20", "--method=multistep"]
args = sample.arg_parse()
args.demo = False         # demo=True is the gradio branch (expects PIL images passed in); file paths need False
args.save_image = False   # we save ourselves; sampling() still dumps a yaml per call into save_image_dir
args.save_image_dir = "/tmp/fd_cfg"
pipe = sample.load_fontdiffuer_pipeline(args)

chars = list(open(f"{STYLE_ROOT}/test_chars.txt", encoding="utf-8").read().strip())
print("test chars:", len(chars), "".join(chars), flush=True)

font = sample.load_ttf(ttf)
content_row = [sample.ttf2im(font, ch).resize((CELL, CELL)) for ch in chars]


def gen(ch, ref):
    args.style_image_path = ref
    args.content_character = ch
    img = sample.sampling(args, pipe)
    if img is None:
        img = Image.new("RGB", (CELL, CELL), "red")
    return img.convert("RGB").resize((CELL, CELL))


def save_sheet(path, rows, labels):
    # rows: list of PIL lists (equal length); labels: list of PIL (one per row) pasted in column 0
    w = CELL * (len(rows[0]) + 1)
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
    sheet.save(path)
    print("sheet saved:", path, sheet.size, flush=True)


summary = []
os.makedirs(OUT, exist_ok=True)

# A. control: a PRINTED glyph as the style reference. If the 24 chars still come out in the same
#    running-hand look as v3, the style encoder is near-inert; if they turn print-like, it works
#    but has low resolution between handwriting samples.
ctrl_ref = f"{WORK}/data_examples/sampling/example_style.jpg"
ctrl_row = [gen(ch, ctrl_ref) for ch in chars]
os.makedirs(f"{OUT}/control", exist_ok=True)
for ch, im in zip(chars, ctrl_row):
    im.save(f"{OUT}/control/{ch}.png")
save_sheet(f"{OUT}/sheet_control_printed_style.png", [content_row, ctrl_row],
           [None, Image.open(ctrl_ref)])
summary.append(f"control\t{len(ctrl_row)}")

# B. ground truth: generate the chars the writer actually wrote (the reference crops ARE the real
#    handwriting), conditioning on a different reference char of the same writer, then put
#    content / generated / real side by side. This is the only sheet that can answer "does it look
#    like the person's hand".
for sd in ["style-linhand", "style-liujiarui"]:
    refs = sorted(glob.glob(f"{STYLE_ROOT}/{sd}/*.png"))
    if not refs:
        continue
    tags = [os.path.splitext(os.path.basename(r))[0].split("_", 1)[1] for r in refs]
    out_dir = f"{OUT}/groundtruth/{sd}"
    os.makedirs(out_dir, exist_ok=True)
    c_row, g_row, t_row = [], [], []
    for k, (ref, ch) in enumerate(zip(refs, tags)):
        other = refs[(k + 1) % len(refs)]          # style ref = a different real glyph, never itself
        c_row.append(sample.ttf2im(font, ch).resize((CELL, CELL)))
        g = gen(ch, other)
        g.save(f"{out_dir}/{ch}.png")
        g_row.append(g)
        t_row.append(Image.open(ref).convert("RGB").resize((CELL, CELL)))
    save_sheet(f"{OUT}/sheet_groundtruth_{sd}.png", [c_row, g_row, t_row], [None, None, None])
    print(f"groundtruth {sd}: {len(g_row)} chars {''.join(tags)}", flush=True)
    summary.append(f"groundtruth/{sd}\t{len(g_row)}")

open(f"{OUT}/summary.tsv", "w").write("\n".join(summary) + "\n")
n = len(glob.glob(f"{OUT}/**/*.png", recursive=True))
print("done. png files:", n, flush=True)
