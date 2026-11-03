#!/usr/bin/env python3
"""Build a 15-second sample from the coded styles: 5 scenes, crossfaded, with a soft audio bed.

    python3 make_sample.py --out dopeak_15s.mp4

Frames are rendered by chrome-headless-shell in chunks of CHUNK frames (the DOM dump grows
~250 KB per 720x1280 frame, so one call per chunk keeps it safe), each scene is encoded,
then the scenes are chained with xfade and the audio bed is mixed in.
"""
import argparse
import base64
import importlib.util
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rs", os.path.join(HERE, "render_style.py"))
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)
SHARED = open(rs.shared_path(), encoding="utf-8").read()

CHUNK = 18
SCENES = [("B4", 3.4), ("C4", 3.4), ("D2", 3.4), ("G1", 3.4), ("E1", 3.4)]
FADE = 0.5


def style_code(sid):
    md = open(rs.style_path(sid), encoding="utf-8").read()
    m = re.search(r"```(?:js|javascript)\n(.*?)```", md, re.S)
    if not m:
        raise SystemExit(f"{sid} has no reference implementation")
    return m.group(1)


def render_frames(sid, seconds, w, h, fps, outdir):
    code = style_code(sid)
    total = int(round(seconds * fps))
    os.makedirs(outdir, exist_ok=True)
    made = 0
    with tempfile.TemporaryDirectory() as tmp:
        while made < total:
            n = min(CHUNK, total - made)
            t0 = 0.15 + made / fps
            html = rs.HTML.format(w=w, h=h, n=n, dur=seconds, sid=sid, shared=SHARED, style=code)
            # start the animation clock at t0 for this chunk
            html = html.replace("const t = 0.15 + (DUR-0.15) * (i/(N-1));",
                                f"const t = {t0} + i/{fps};")
            page = os.path.join(tmp, "p.html")
            open(page, "w", encoding="utf-8").write(html)
            r = subprocess.run([rs.CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                                "--virtual-time-budget=30000", "--dump-dom", "file://" + page],
                               capture_output=True, text=True, timeout=300)
            m = re.search(r'<div id="out">(.*?)</div>', r.stdout, re.S)
            if not m or not m.group(1):
                raise SystemExit(f"{sid}: chunk at frame {made} produced nothing")
            for url in m.group(1).split("|"):
                open(os.path.join(outdir, f"f{made:04d}.png"), "wb").write(
                    base64.b64decode(url.split(",", 1)[1]))
                made += 1
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dopeak_15s.mp4")
    ap.add_argument("--size", default="720x1280")
    ap.add_argument("--fps", type=int, default=24)
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    work = tempfile.mkdtemp(prefix="sample-")
    clips = []
    try:
        for sid, secs in SCENES:
            d = os.path.join(work, sid)
            n = render_frames(sid, secs, w, h, a.fps, d)
            clip = os.path.join(work, f"{sid}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                            "-i", os.path.join(d, "f%04d.png"), "-c:v", "libx264",
                            "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", clip],
                           check=True)
            clips.append(clip)
            print(f"  {sid}: {n} frames -> {os.path.getsize(clip)//1024} KB")

        # chain with crossfades
        ins, filt, last = [], [], "[0:v]"
        for i, c in enumerate(clips):
            ins += ["-i", c]
        off = 0.0
        for i in range(1, len(clips)):
            off += SCENES[i - 1][1] - FADE
            out = f"[v{i}]"
            filt.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE}:offset={off:.2f}{out}")
            last = out
        silent = os.path.join(work, "silent.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + ins +
                       ["-filter_complex", ";".join(filt), "-map", last,
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", silent], check=True)

        dur = sum(s for _, s in SCENES) - FADE * (len(SCENES) - 1)
        # soft ambient bed: three detuned sines, low-passed, slow tremolo, fades
        audio = (f"sine=frequency=110:duration={dur:.2f}[a1];"
                 f"sine=frequency=164.81:duration={dur:.2f}[a2];"
                 f"sine=frequency=220:duration={dur:.2f}[a3];"
                 f"[a1][a2][a3]amix=inputs=3:weights='1 0.5 0.3'[mix];"
                 f"[mix]lowpass=f=700,tremolo=f=0.25:d=0.35,"
                 f"afade=t=in:st=0:d=1.5,afade=t=out:st={dur-2:.2f}:d=2,"
                 f"volume=0.5[aout]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent,
                        "-filter_complex", audio, "-map", "0:v", "-map", "[aout]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        "-shortest", "-movflags", "+faststart", a.out], check=True)
        print(f"{a.out}: {dur:.1f}s, {w}x{h}, {os.path.getsize(a.out)/1024/1024:.1f} MB")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
