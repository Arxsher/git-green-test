"""Assemble an episode from rendered plates, the voice timeline and captions.

Usage: python compose.py TIMELINE.json PLATES_DIR FONT.ttf OUT.mp4 [--frames DIR]

For every frame: pick the camera of the current line, the pose plate that matches who is talking
(mouth from her loudness, bounce from Claude's), blinks on a random schedule, a slow push-in per shot,
and the current line as a caption. Then mix a quiet room tone under the voices and encode.
"""
import argparse
import json
import random
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("timeline")
ap.add_argument("plates")
ap.add_argument("font")
ap.add_argument("out")
ap.add_argument("--frames")
args = ap.parse_args()

W, H = 1080, 1920
CAM = {"CU": "CAM_CU", "OTS": "CAM_OTS", "WIDE": "CAM_WIDE"}
FOCUS = {"CAM_CU": (0.5, 0.45), "CAM_OTS": (0.5, 0.52), "CAM_WIDE": (0.5, 0.5)}  # push-in centre
PUSH = 0.035  # zoom gained over one shot

tl = json.loads(Path(args.timeline).read_text())
fps, N, lines = tl["fps"], tl["frames"], tl["lines"]
env = {k: np.array(v) for k, v in tl["envelope"].items()}
frames_dir = Path(args.frames or Path(args.out).with_suffix("")) / "frames"
frames_dir.mkdir(parents=True, exist_ok=True)
starts = [int(round(ln["start"] * fps)) for ln in lines]

speaking = {who: np.zeros(N, bool) for who in env}
for ln in lines:
    speaking[ln["who"]][int(ln["start"] * fps):int(ln["end"] * fps) + 1] = True


def blink_frames(seed):
    rng, out, t = random.Random(seed), set(), random.Random(seed).uniform(1.0, 2.0)
    while t < N / fps:
        f = int(t * fps)
        out.update(range(f, f + 4))
        t += rng.uniform(2.2, 4.8)
    return out


def held(targets, min_hold=2):
    """Smooth a per-frame state list so no state flickers for less than min_hold frames."""
    out, cur, hold = [], targets[0], 0
    for t in targets:
        if t != cur and hold >= min_hold:
            cur, hold = t, 0
        else:
            hold += 1
        out.append(cur)
    return out


def mouth_target(f):
    if not speaking["her"][f]:
        return "closed"
    e = env["her"][f]
    return "open" if e > 0.55 else "mid" if e > 0.2 else "closed"


def claude_target(f):
    if not speaking["claude"][f]:
        return "rest"
    e = env["claude"][f]
    return "up" if e > 0.5 else "rest" if e > 0.2 else "squash"


mouth = held([mouth_target(f) for f in range(N)])
bounce = held([claude_target(f) for f in range(N)])
her_blink, claude_blink = blink_frames(1), blink_frames(2)

plates = {}


def plate(name):
    if name not in plates:
        plates[name] = Image.open(Path(args.plates) / f"{name}.png").convert("RGB")
    return plates[name]


font = ImageFont.truetype(args.font, 50)


def wrap(text, max_w):
    words, rows, row = text.split(), [], ""
    for w in words:
        trial = f"{row} {w}".strip()
        if font.getlength(trial) <= max_w or not row:
            row = trial
        else:
            rows.append(row)
            row = w
    rows.append(row)
    return rows


def caption(img, text):
    rows = wrap(text, W * 0.74)
    lh = 64
    tw = max(font.getlength(r) for r in rows)
    bw, bh = tw + 52, lh * len(rows) + 30
    x0, y0 = (W - bw) / 2, H * 0.135
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=22, fill=(30, 30, 34, 185))
    for i, r in enumerate(rows):
        d.text(((W - font.getlength(r)) / 2, y0 + 15 + i * lh), r, font=font, fill=(255, 255, 255, 255))
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


for f in range(N):
    idx = max([i for i, s in enumerate(starts) if s <= f], default=0)
    seg_a = 0 if idx == 0 else starts[idx]
    seg_b = starts[idx + 1] if idx + 1 < len(starts) else N
    cam = CAM[lines[idx]["shot"]]
    m, b = mouth[f], bounce[f]
    if cam == "CAM_CU":
        name = f"CAM_CU__mouth-{m}_eyes-{'closed' if f in her_blink else 'open'}"
    elif cam == "CAM_OTS":
        name = f"CAM_OTS__claude-{b}_blink-{'yes' if f in claude_blink else 'no'}"
    else:
        name = f"CAM_WIDE__claude-{b if b in ('rest', 'up') else 'rest'}_mouth-{'closed' if m == 'closed' else 'open'}"
    src = plate(name)
    pw, ph = src.size
    z = 1 + PUSH * (f - seg_a) / max(1, seg_b - seg_a)
    cw, ch = pw / z, ph / z
    fx, fy = FOCUS[cam]
    cx = min(max(fx * pw, cw / 2), pw - cw / 2)
    cy = min(max(fy * ph, ch / 2), ph - ch / 2)
    frame = src.resize((W, H), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    if f >= starts[0]:
        frame = caption(frame, lines[idx]["text"])
    frame.save(frames_dir / f"{f:05d}.jpg", quality=94)
    if f % 150 == 0:
        print(f"frame {f}/{N}", flush=True)

# Sound: voices plus a very quiet brown-noise room tone.
voice, sr = sf.read(Path(args.timeline).parent / "voice_mix.wav")
rng = np.random.default_rng(0)
brown = np.cumsum(rng.standard_normal(len(voice)))
brown -= np.convolve(brown, np.ones(4001) / 4001, mode="same")  # remove drift
brown /= np.sqrt(np.mean(brown ** 2)) + 1e-9
room = brown * 10 ** (-46 / 20)
fade = np.minimum(1, np.minimum(np.arange(len(room)), np.arange(len(room))[::-1]) / (0.5 * sr))
mix = voice + room * fade
mix_path = frames_dir.parent / "mix.wav"
sf.write(mix_path, mix.astype(np.float32), sr)

subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames_dir / "%05d.jpg"),
    "-i", str(mix_path), "-af", "loudnorm=I=-14:TP=-1.5:LRA=7", "-ar", "48000",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out,
], check=True)
print("wrote", args.out)
