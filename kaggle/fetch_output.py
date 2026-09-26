# Fetch a Kaggle kernel version's log + selected output files via the legacy API with the
# OAuth token from ~/.kaggle/credentials.json. The CLI's `kernels output` downloads everything
# and dies on Windows at the first CJK filename; this only pulls what matches --glob.
# usage: python fetch_output.py <owner/slug> <outdir> [--glob outputs/] [--log-only]
import fnmatch, json, os, sys
import requests

owner_slug, outdir = sys.argv[1], sys.argv[2]
prefix = sys.argv[sys.argv.index("--glob") + 1] if "--glob" in sys.argv else ""
log_only = "--log-only" in sys.argv
user, slug = owner_slug.split("/")
cred = json.load(open(os.path.expanduser("~/.kaggle/credentials.json")))
h = {"Authorization": "Bearer " + cred["access_token"]}
os.makedirs(outdir, exist_ok=True)

files, token, log = [], None, ""
while True:
    p = {"userName": user, "kernelSlug": slug}
    if token:
        p["pageToken"] = token
    r = requests.get("https://www.kaggle.com/api/v1/kernels/output", params=p, headers=h)
    r.raise_for_status()
    j = r.json()
    files += j.get("files", [])
    log = log or j.get("log", "")
    token = j.get("nextPageToken")
    if not j.get("hasNextPageToken") or not token:
        break

logtxt = log
try:
    L = json.loads(log)
    logtxt = "\n".join(str(x.get("data", "")) for x in L if isinstance(x, dict))
except Exception:
    pass
open(os.path.join(outdir, "kernel.log"), "w", encoding="utf-8").write(logtxt)
print("log chars", len(logtxt), "| files listed", len(files))

n = 0
if not log_only:
    for f in files:
        name = f.get("fileName", "")
        if prefix and not name.startswith(prefix):
            continue
        dst = os.path.join(outdir, name.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        rr = requests.get(f["url"], headers=h)
        rr.raise_for_status()
        open(dst, "wb").write(rr.content)
        n += 1
print("downloaded", n, "files to", outdir)
