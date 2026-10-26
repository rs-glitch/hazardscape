"""Headless runtime check: serve web/, load views in Chrome with software WebGL, fail on console errors.

Usage: python selftest.py [view ...]   (views: state, or a fire id such as dixie). Screenshots go to data/selftest/.
"""
import functools
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading

from common import ROOT, WEB

CHROME = os.environ.get("CHROME") or next(
    (p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and os.path.exists(p)), "chrome")
OUT = ROOT / "data" / "selftest"
OUT.mkdir(parents=True, exist_ok=True)


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    h.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def check(port, view, size="1400,900"):
    url = f"http://127.0.0.1:{port}/index.html" + ("" if view == "state" else f"#{view}")
    w, h = map(int, size.split(","))
    if w < 520:   # headless Chrome will not make a window narrower than ~500 px: test phone width in an iframe
        (WEB / "_phone.html").write_text(f'<body style="margin:0;background:#000"><iframe src="{url}" '
                                         f'style="width:{w}px;height:{h}px;border:0"></iframe>', encoding="utf-8")
        url, size = f"http://127.0.0.1:{port}/_phone.html", f"520,{h}"
    shot = OUT / f"{view}_{size.replace(',', 'x')}.png"
    cmd = [CHROME, "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
           "--enable-logging=stderr", "--v=0", f"--window-size={size}", "--virtual-time-budget=25000",
           f"--user-data-dir={OUT / 'profile'}", f"--screenshot={shot}", url]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    console = [l for l in p.stderr.splitlines() if "CONSOLE" in l or "Uncaught" in l]
    errors = [l for l in console if re.search(r"error|uncaught|failed|NaN", l, re.I)]
    return shot, console, errors


if __name__ == "__main__":
    views = sys.argv[1:] or ["state", "dixie"]
    srv = serve()
    bad = 0
    for v in views:
        for size in ("1400,900", "400,860"):
            shot, console, errors = check(srv.server_port, v, size)
            print(f"{v} @ {size}: {'FAIL' if errors else 'ok'}  -> {shot.name}")
            for l in errors[:8]:
                print("   ", l[-240:])
            bad += bool(errors)
    srv.shutdown()
    (WEB / "_phone.html").unlink(missing_ok=True)
    sys.exit(1 if bad else 0)
