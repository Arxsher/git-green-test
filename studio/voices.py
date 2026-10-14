"""Voice every line of an episode and lay out the timeline.

Usage: python voices.py EPISODE.json OUTDIR
Writes OUTDIR/lines/NN.wav, OUTDIR/voice_mix.wav and OUTDIR/timeline.json, which holds each line's
start/end and a per-frame loudness envelope (0..1) for each speaker, used to drive mouths and bounces.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SR = 24000
FPS = 30
LEAD_IN = 0.3       # silence before the first line
GAP = 0.35          # normal pause between lines
BEAT_GAP = 0.8      # pause before a line that starts with "..."
TAIL = 1.6          # hold after the last line

ep = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
(out / "lines").mkdir(parents=True, exist_ok=True)

pipes = {}


def speak(who, text):
    v = ep["voices"][who]
    if v["lang"] not in pipes:
        pipes[v["lang"]] = KPipeline(lang_code=v["lang"])
    spoken = re.sub(r"^\.\.\.\s*", "", text).replace("—", ",")
    chunks = [a.numpy() if hasattr(a, "numpy") else np.asarray(a) for _, _, a in pipes[v["lang"]](spoken, voice=v["voice"], speed=v["speed"])]
    audio = np.concatenate(chunks).astype(np.float32)
    # trim leading/trailing near-silence so the timing is tight
    loud = np.where(np.abs(audio) > 0.01)[0]
    if len(loud):
        audio = audio[max(loud[0] - 600, 0):min(loud[-1] + 2400, len(audio))]
    return audio


t = LEAD_IN
lines, clips = [], []
for i, ln in enumerate(ep["lines"]):
    audio = speak(ln["who"], ln["text"])
    if i > 0:
        t += BEAT_GAP if ln["text"].startswith("...") else GAP
    dur = len(audio) / SR
    sf.write(out / "lines" / f"{i:02d}.wav", audio, SR)
    lines.append({**ln, "start": round(t, 3), "end": round(t + dur, 3)})
    clips.append((t, audio))
    t += dur
total = t + TAIL

mix = np.zeros(int(total * SR) + SR, np.float32)
tracks = {w: np.zeros_like(mix) for w in ep["voices"]}
for (start, audio), ln in zip(clips, lines):
    a = int(start * SR)
    mix[a:a + len(audio)] += audio
    tracks[ln["who"]][a:a + len(audio)] += audio
sf.write(out / "voice_mix.wav", mix, SR)

# Per-frame loudness for each speaker, normalised so a typical loud syllable is ~1.
nframes = int(total * FPS)
env = {}
hop = SR // FPS
for who, tr in tracks.items():
    rms = np.array([np.sqrt(np.mean(tr[f * hop:(f + 1) * hop] ** 2)) for f in range(nframes)])
    ref = np.percentile(rms[rms > 1e-4], 90) if np.any(rms > 1e-4) else 1.0
    env[who] = np.clip(rms / ref, 0, 1).round(3).tolist()

(out / "timeline.json").write_text(json.dumps({"fps": FPS, "duration": round(total, 3), "frames": nframes,
                                                "lines": lines, "envelope": env}, indent=1))
print(f"{len(lines)} lines, {total:.1f} s")
for ln in lines:
    print(f"  {ln['start']:5.2f}-{ln['end']:5.2f} {ln['who']:6} {ln['shot']:4} {ln['text']}")
