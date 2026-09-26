"""Serve the capture page on the LAN and accept the finished strokes back.

Without this you have to move writer.html onto the tablet and the .json back off
it by hand, which is the step most likely to stall the whole thing. With it: open
the printed URL on the tablet, write, tap 交出, and the file lands in strokes\\.

    python spen_serve.py
    python spen_serve.py --port 8000 --dir D:\\handwriting-font

Trusted LAN only -- it binds to every interface and writes files that anyone on
the network could POST. Ctrl-C when you are done writing; do not leave it up.
"""

import argparse
import os
import re
import socket
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

MAX_BYTES = 8 * 1024 * 1024
SAFE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def make_handler(root, save_dir):
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=root, **kw)

        def do_POST(self):
            if self.path.split("?")[0] != "/save":
                self.send_error(404)
                return
            try:
                n = int(self.headers.get("Content-Length", 0))
            except ValueError:
                n = 0
            if not 0 < n <= MAX_BYTES:
                self.reply(413, f"body must be 1..{MAX_BYTES} bytes, got {n}")
                return

            name = "strokes.json"
            if "?" in self.path:
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query).get("name", [""])[0]
                if q:
                    if not SAFE.match(q) or not q.endswith(".json"):
                        self.reply(400, "bad name")
                        return
                    name = q

            body = self.rfile.read(n)
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, name)

            # never silently overwrite earlier work
            if os.path.exists(path):
                i = 2
                stem = name[:-5]
                while os.path.exists(os.path.join(save_dir, f"{stem}-{i}.json")):
                    i += 1
                path = os.path.join(save_dir, f"{stem}-{i}.json")

            with open(path, "wb") as f:
                f.write(body)
            print(f"  saved {path}  ({n} bytes)")
            self.reply(200, os.path.basename(path))

        def reply(self, code, text):
            b = text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass
    return H


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=here, help="directory to serve")
    ap.add_argument("--save-dir", default=os.path.join(here, "strokes"))
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    page = os.path.join(args.dir, "spen", "writer.html")
    if not os.path.exists(page):
        sys.exit(f"missing {page}\nGenerate it first:\n"
                 f"  python tools\\make_spen_page.py --out "
                 f"{os.path.join(args.dir, 'spen')} "
                 f"--manifest {os.path.join(args.dir, 'template', 'manifest.json')}")

    srv = ThreadingHTTPServer(("0.0.0.0", args.port),
                              make_handler(args.dir, args.save_dir))
    print(f"serving  {args.dir}")
    print(f"saving   {args.save_dir}")
    print(f"\n  On the tablet, same WiFi, open:\n")
    print(f"      http://{lan_ip()}:{args.port}/spen/writer.html\n")
    print("Tap 交出 when done; the file appears above. Ctrl-C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
