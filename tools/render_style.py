#!/usr/bin/env python3
"""Render one of the 341 code-animation styles to an MP4, headless, no browser lib.

    python3 render_style.py A1 --out preview_a1.mp4 --frames 24 --size 360x640

How it works: the style file ships a JS function S.<ID>(ctx, w, h, t, state) plus a shared
utils file. This builds a single HTML page that calls it for every frame at load time
(state carried across calls, exactly as the animation is meant to be driven), embeds each
frame as a PNG data URL, then we pull them out of `chrome-headless-shell --dump-dom` and
encode with ffmpeg. No playwright, no node, no display.
"""
import argparse
import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

def _first(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def style_path(sid):
    return _first([os.path.join(d, sid + ".md") for d in (
        os.path.join(HERE, "styles"), os.path.join(HERE, "prompts"),
        os.path.join(HERE, "..", "styles"), os.path.join(HERE, "..", "prompts"))])


def shared_path():
    import glob
    direct = _first([os.path.join(d, "_shared.js") for d in (
        os.path.join(HERE, "styles"), os.path.join(HERE, "..", "styles"))])
    if direct:
        return direct
    hits = sorted(glob.glob(os.path.join(HERE, "*_shared*")) +
                  glob.glob(os.path.join(HERE, "..", "*_shared*")))
    return hits[0] if hits else None

def find_chrome():
    """CHROME_BIN, then a PATH lookup, then the usual playwright/chromium locations."""
    import glob
    env = os.environ.get("CHROME_BIN")
    if env:
        return env
    for name in ("chrome-headless-shell", "chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    patterns = [
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"),
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        "/usr/bin/chromium*",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    raise SystemExit("no Chromium found — set CHROME_BIN=/path/to/chrome-headless-shell")


CHROME = find_chrome()

HTML = """<!doctype html><meta charset="utf-8">
<style>html,body{{margin:0;background:#000}}canvas{{display:block}}</style>
<canvas id="c" width="{w}" height="{h}"></canvas>
<script>{shared}</script>
<script>var SERIF = '"Noto Serif SC", "Songti SC", Georgia, serif'; var S = window.S || {{}};</script>
<script>{style}</script>
<script>
const W={w}, H={h}, N={n}, DUR={dur};
const c=document.getElementById('c').getContext('2d');
const st={{}}; const out=[];
for (let i=0;i<N;i++) {{
  const t = 0.15 + (DUR-0.15) * (i/(N-1));
  try {{ S['{sid}'](c, W, H, t, st); }} catch (e) {{ document.title='ERR '+e; break; }}
  out.push(document.getElementById('c').toDataURL('image/png'));
}}
const d=document.createElement('div'); d.id='out';
d.textContent=out.join('|'); document.body.appendChild(d);
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("style")
    ap.add_argument("--out", default=None)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--size", default="360x640")
    ap.add_argument("--duration", type=float, default=3.0)
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    sid = a.style.upper()
    sp = style_path(sid)
    if not sp:
        sys.exit(f"no such style: {sid}")
    md = open(sp, encoding="utf-8").read()
    code = re.search(r"```(?:js|javascript)\n(.*?)```", md, re.S)
    if not code:
        sys.exit(f"{sid} ships a prompt but no reference implementation")
    sh = shared_path()
    if not sh:
        sys.exit("shared canvas utils not found (styles/_shared.js)")
    shared = open(sh, encoding="utf-8").read()
    html = HTML.format(w=w, h=h, n=a.frames, dur=a.duration, sid=sid,
                       shared=shared, style=code.group(1))
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "page.html")
        open(page, "w", encoding="utf-8").write(html)
        r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                            "--virtual-time-budget=30000",
                            "--dump-dom", "file://" + page],
                           capture_output=True, text=True, timeout=180)
        dom = r.stdout
        err = re.search(r"<title>(ERR .*?)</title>", dom)
        if err:
            sys.exit(err.group(1))
        m = re.search(r'<div id="out">(.*?)</div>', dom, re.S)
        if not m:
            sys.exit("no frames in DOM (chrome printed nothing)")
        frames = m.group(1).split("|")
        out = a.out or f"preview_{sid.lower()}.mp4"
        fdir = os.path.join(tmp, "f")
        os.makedirs(fdir)
        for i, url in enumerate(frames):
            data = base64.b64decode(url.split(",", 1)[1])
            open(os.path.join(fdir, f"f{i:04d}.png"), "wb").write(data)
        fps = max(1, round(len(frames) / a.duration))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                        "-i", os.path.join(fdir, "f%04d.png"), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
        print(f"{out}: {len(frames)} frames, {w}x{h}, {fps} fps, "
              f"{os.path.getsize(out)/1024:.0f} KB")


if __name__ == "__main__":
    main()
