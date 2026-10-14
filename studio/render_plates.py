"""Render every pose "plate" the compositor needs, for one lighting mood.

Run headless on a scene saved by build_scene.py:
  blender -b SCENE.blend --python render_plates.py -- OUTDIR [--width 1152] [--samples 16] [--only CAM_CU]

Limited animation: only mouths, blinks and Claude's bounce change between frames, so each camera is
rendered once per pose combination and compose.py picks the right plate for every video frame.
Plates are rendered slightly larger than 1080x1920 so the compositor can push in without upscaling.
"""
import argparse
import itertools
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--width", type=int, default=1152)
ap.add_argument("--samples", type=int, default=16)
ap.add_argument("--only")
args = ap.parse_args(argv)

sc = bpy.context.scene
O = bpy.data.objects
sc.render.resolution_x = args.width
sc.render.resolution_y = int(args.width * 16 / 9)
sc.eevee.taa_render_samples = args.samples
sc.eevee.use_raytracing = True

MOUTH = {"closed": (1.0, 1.0), "mid": (0.95, 2.3), "open": (0.8, 3.8)}  # (x, z) scale of the mouth box
CLAUDE = {  # (lift in metres, x/y scale, z scale)
    "rest": (0.0, 1.0, 1.0),
    "up": (0.014, 0.97, 1.05),
    "squash": (0.0, 1.06, 0.9),
    "hop": (0.028, 0.95, 1.09),
}


def set_mouth(state):
    sx, sz = MOUTH[state]
    O["mouth"].scale = (sx, 1, sz)


def set_eyes(closed):
    for n in ("L", "R"):
        O[f"eye_{n}"].scale = (1, 1, 0.14 if closed else 1)
        O[f"eye_hl_{n}"].hide_render = closed


def set_claude(state, blink=False):
    lift, sxy, sz = CLAUDE[state]
    O["claude_body"].location = (0, 0, lift)
    O["claude_body"].scale = (sxy, sxy, sz)
    for s in ("-1", "1"):  # eye shapes are baked into the meshes; object scale 1 = open
        O["cl_eye_" + s].scale = (1, 1, 0.12 if blink else 1)
        O["cl_pupil_" + s].scale = (1.7, 1, 0.14) if blink else (1, 1, 1)
        O["cl_hl_" + s].hide_render = blink


def set_camera(name):
    cam = O[name]
    hidden = set(filter(None, cam.get("hide", "").split(",")))
    for ob in O:
        root = ob
        while root.parent and root.name not in hidden:
            root = root.parent
        ob.hide_render = root.name in hidden
    sc.camera = cam


def reset():
    set_mouth("closed")
    set_eyes(False)
    set_claude("rest")


jobs = []
for m, e in itertools.product(MOUTH, ("open", "closed")):
    jobs.append(("CAM_CU", f"mouth-{m}_eyes-{e}", lambda m=m, e=e: (set_mouth(m), set_eyes(e == "closed"))))
for c, b in itertools.product(CLAUDE, ("no", "yes")):
    jobs.append(("CAM_OTS", f"claude-{c}_blink-{b}", lambda c=c, b=b: set_claude(c, b == "yes")))
for c, m in itertools.product(("rest", "up", "hop"), ("closed", "open")):
    jobs.append(("CAM_WIDE", f"claude-{c}_mouth-{m}", lambda c=c, m=m: (set_claude(c), set_mouth(m))))

for cam, state, apply in jobs:
    if args.only and cam != args.only:
        continue
    set_camera(cam)  # also resets hide_render, so pose changes come after it
    reset()
    apply()
    sc.render.filepath = f"{args.out}/{cam}__{state}.png"
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"PLATE {cam}__{state} {time.time() - t:.0f}s", flush=True)
