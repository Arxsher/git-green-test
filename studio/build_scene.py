"""Build the 3D set in Blender: her desk, the window and city on her right, her, and Claude.

Run headless:
  blender -b --python build_scene.py -- --tex TEXDIR --blend OUT.blend [--stills DIR] [--res 540] [--mood dusk]

Everything is low-poly and flat-shaded on purpose (the "toy diorama" look).
World axes: she sits at the origin facing +Y (toward the monitors); +X is her right, where the window is.
"""
import argparse
import math
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--tex", required=True)
ap.add_argument("--blend", required=True)
ap.add_argument("--stills")
ap.add_argument("--res", type=int, default=540, help="render width; height is 16:9 of it")
ap.add_argument("--mood", default="dusk", choices=["dusk", "night", "rain", "morning"])
ap.add_argument("--samples", type=int, default=24)
args = ap.parse_args(argv)

random.seed(3)

# ---------------------------------------------------------------- helpers


def lin(hexstr):
    """sRGB hex to linear RGB tuple."""
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


_mats = {}


def mat(name, color, rough=0.75, emit=None, emit_strength=0.0, metallic=0.0, alpha=1.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit), 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    _mats[name] = m
    return m


def image_mat(name, path, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Roughness"].default_value = 0.3
    return m


def link(ob, parent=None):
    bpy.context.scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def from_bm(name, bm, material, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    return link(ob, parent)


def box(name, size, loc, material, rot=(0, 0, 0), bevel=0.0, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=1, affect="EDGES")
    return from_bm(name, bm, material, loc, rot, parent)


def sphere(name, radius, loc, material, segs=12, rings=8, scale=(1, 1, 1), rot=(0, 0, 0), parent=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    return from_bm(name, bm, material, loc, rot, parent)


def ico(name, radius, loc, material, subdiv=1, scale=(1, 1, 1), rot=(0, 0, 0), parent=None):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    return from_bm(name, bm, material, loc, rot, parent)


def cyl(name, r1, r2, depth, loc, material, segs=10, rot=(0, 0, 0), parent=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    return from_bm(name, bm, material, loc, rot, parent)


def limb(name, p1, p2, radius, material, parent=None, segs=8):
    """A faceted capsule from p1 to p2 (sleeves, arms)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=6, radius=radius)
    bmesh.ops.scale(bm, vec=(1, 1, (d.length / 2 + radius) / radius), verts=bm.verts)
    rot = d.to_track_quat("Z", "Y").to_euler()
    return from_bm(name, bm, material, (p1 + p2) / 2, rot, parent)


def empty(name, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None)
    ob.location = loc
    return link(ob, parent)


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- reset scene

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

MOODS = {
    # sky top, sky horizon, window light colour/energy, key light energy, lit-window share, world strength
    "dusk": dict(top="#2B3A5E", hor="#B9A3B4", win="#8FA8F0", win_e=190, key_e=40, lit=0.35, world=0.25),
    "night": dict(top="#060A18", hor="#1C2445", win="#4F63A8", win_e=90, key_e=60, lit=0.55, world=0.15),
    "rain": dict(top="#4A5262", hor="#8D96A6", win="#A8B6CC", win_e=300, key_e=45, lit=0.2, world=0.4),
    "morning": dict(top="#7FA6D6", hor="#F2D9B8", win="#FFE6C4", win_e=520, key_e=30, lit=0.0, world=0.7),
}
M = MOODS[args.mood]

# ---------------------------------------------------------------- materials

skin = mat("skin", "#EBA382", 0.7)
hair = mat("hair", "#141116", 0.5)
hoodie = mat("hoodie", "#2E6145", 0.85)
hoodie_dark = mat("hoodie_dark", "#244E37", 0.85)
string_m = mat("drawstring", "#E9E4D6", 0.6)
black = mat("black", "#0C0C10", 0.35)
white = mat("eye_white", "#F6F3EE", 0.3)
gold = mat("gold", "#E2B54C", 0.25, metallic=1.0)
mouth_m = mat("mouth", "#5A2C2A", 0.6)
claude_m = mat("claude", "#E0662C", 0.5)
claude_dark = mat("claude_dark", "#B44A22", 0.6)
wood = mat("wood", "#7A4E33", 0.55)
wood_dark = mat("wood_dark", "#5A3A27", 0.6)
felt = mat("felt", "#2C2D31", 0.95)
plastic = mat("plastic", "#1D1E22", 0.45)
alu = mat("alu", "#9A9CA3", 0.35, metallic=0.6)
wall = mat("wall", "#A39A90", 0.9)
floor_m = mat("floor", "#8C6A4E", 0.6)
frame_m = mat("window_frame", "#3B3E45", 0.5)
mug_m = mat("mug", "#F1EEE8", 0.35)
coffee = mat("coffee", "#3B2416", 0.2)
pot = mat("pot", "#C9BBA6", 0.8)
leaf = mat("leaf", "#4E8A3F", 0.7)
leaf2 = mat("leaf2", "#6BA34F", 0.7)
chair_m = mat("chair", "#26272C", 0.7)
glow = mat("light_bar", "#FFFFFF", 0.5, emit="#FFD9A8", emit_strength=8.0)

screen_code = image_mat("screen_code", f"{args.tex}/code_editor.png", 1.6)
screen_chat = image_mat("screen_chat", f"{args.tex}/chat.png", 1.4)

# ---------------------------------------------------------------- room

box("floor", (6, 7, 0.05), (0, 0, -0.025), floor_m)
box("wall_back", (4, 0.1, 2.8), (-0.4, 1.15, 1.4), wall)  # behind the desk
box("wall_left", (0.1, 6, 2.8), (-1.6, -1.0, 1.4), wall)
box("wall_front", (4, 0.1, 2.8), (-0.4, -2.6, 1.4), wall)
box("ceiling", (4, 6, 0.05), (-0.4, -1.0, 2.8), wall)

# The window wall on her right: a big opening from y=-1.9 to y=1.0, z=0.35..2.5
WX = 1.1
box("wall_right_low", (0.12, 3.9, 0.35), (WX, -0.75, 0.175), wall)
box("wall_right_high", (0.12, 3.9, 0.3), (WX, -0.75, 2.65), wall)
box("wall_right_a", (0.12, 0.5, 2.8), (WX, 1.2, 1.4), wall)
box("wall_right_b", (0.12, 0.5, 2.8), (WX, -2.4, 1.4), wall)
for i, y in enumerate([-1.9, -0.95, 0.0, 0.95]):
    box(f"mullion_{i}", (0.08, 0.06, 2.15), (WX - 0.02, y, 1.42), frame_m)
box("transom", (0.08, 2.9, 0.06), (WX - 0.02, -0.45, 1.95), frame_m)
box("sill_in", (0.3, 2.95, 0.04), (WX - 0.15, -0.45, 0.37), frame_m)

# ---------------------------------------------------------------- desk (against the back wall, she faces it)

DESK_Z = 0.75
desk = box("desk_top", (1.9, 0.75, 0.04), (-0.15, 0.55, DESK_Z - 0.02), wood, bevel=0.008)
for x in (-1.05, 0.75):
    for y in (0.22, 0.88):
        box(f"desk_leg_{x}_{y}", (0.05, 0.05, DESK_Z - 0.04), (x, y, (DESK_Z - 0.04) / 2), wood_dark)
box("desk_mat", (1.0, 0.42, 0.006), (-0.05, 0.42, DESK_Z + 0.003), felt, bevel=0.003)

# Ultrawide monitor with a light bar on top
mon = empty("monitor", (-0.08, 0.86, DESK_Z))
box("mon_foot", (0.26, 0.18, 0.012), (0, 0, 0.006), alu, parent=mon)
box("mon_neck", (0.05, 0.03, 0.3), (0, 0.05, 0.15), alu, parent=mon)
box("mon_body", (0.98, 0.04, 0.4), (0, 0.0, 0.42), plastic, bevel=0.01, parent=mon)
box("mon_screen", (0.94, 0.006, 0.36), (0, -0.022, 0.42), screen_code, parent=mon)
box("mon_lightbar", (0.42, 0.05, 0.025), (0, -0.01, 0.64), glow, parent=mon)

# Laptop on a stand, on her left
lap = empty("laptop", (-0.78, 0.6, DESK_Z), )
lap.rotation_euler = (0, 0, math.radians(28))
box("lap_stand", (0.26, 0.22, 0.012), (0, 0, 0.12), alu, rot=(math.radians(-12), 0, 0), parent=lap)
box("lap_leg", (0.2, 0.02, 0.12), (0, 0.09, 0.06), alu, parent=lap)
box("lap_base", (0.32, 0.22, 0.012), (0, 0.0, 0.135), alu, rot=(math.radians(-12), 0, 0), parent=lap)
box("lap_lid", (0.32, 0.012, 0.21), (0, 0.13, 0.27), alu, rot=(math.radians(-8), 0, 0), parent=lap)
box("lap_screen", (0.3, 0.004, 0.19), (0, 0.122, 0.27), screen_chat, rot=(math.radians(-8), 0, 0), parent=lap)

# Keyboard, mouse, mug, phone, plants
kb = box("keyboard", (0.36, 0.12, 0.018), (-0.06, 0.34, DESK_Z + 0.012), plastic, bevel=0.004)
for r in range(4):
    box(f"keys_{r}", (0.33, 0.022, 0.006), (-0.06, 0.295 + r * 0.03, DESK_Z + 0.024), mat("keys", "#3A3C44", 0.5))
sphere("mouse", 0.035, (0.2, 0.34, DESK_Z + 0.012), plastic, segs=10, rings=6, scale=(0.75, 1.15, 0.45))
mug = empty("mug", (-0.36, 0.5, DESK_Z))
cyl("mug_body", 0.038, 0.038, 0.09, (0, 0, 0.045), mug_m, segs=12, parent=mug)
cyl("mug_coffee", 0.034, 0.034, 0.002, (0, 0, 0.082), coffee, segs=12, parent=mug)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=0.022, radius2=0.022, depth=0.008)
from_bm("mug_handle", bm, mug_m, (0.045, 0, 0.05), rot=(math.radians(90), 0, 0), parent=mug)
phone = empty("phone", (0.46, 0.7, DESK_Z))
box("phone_stand", (0.06, 0.06, 0.01), (0, 0, 0.005), alu, parent=phone)
box("phone_body", (0.07, 0.008, 0.14), (0, 0.01, 0.08), plastic, rot=(math.radians(-10), 0, 0), bevel=0.004, parent=phone)


def plant(name, loc, h=0.14):
    p = empty(name, loc)
    cyl(f"{name}_pot", 0.045, 0.035, 0.075, (0, 0, 0.0375), pot, segs=8, parent=p)
    for k in range(7):
        a = k / 7 * math.tau + random.uniform(-0.3, 0.3)
        tilt = random.uniform(0.35, 0.8)
        ico(f"{name}_leaf{k}", 0.03, (math.cos(a) * 0.035, math.sin(a) * 0.035, 0.09 + random.uniform(0, h * 0.4)),
            random.choice([leaf, leaf2]), subdiv=1, scale=(0.5, 0.5, 1.9),
            rot=(math.cos(a + 1.57) * tilt, math.sin(a + 1.57) * tilt, 0), parent=p)
    return p


plant("plant_a", (0.62, 0.78, DESK_Z))
plant("plant_b", (-0.52, 0.86, DESK_Z), h=0.18)

# Headphones hanging on the monitor's right edge
hp = empty("headphones", (0.36, 0.86, DESK_Z + 0.6))
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=False, segments=12, radius=0.07)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.02], context="VERTS")
me = bpy.data.meshes.new("hp_band")
bm.to_mesh(me)
bm.free()
band = bpy.data.objects.new("hp_band", me)
link(band, hp)
band.rotation_euler = (math.radians(90), 0, math.radians(90))
skin_mod = band.modifiers.new("thick", "SKIN")
for v in band.data.skin_vertices[0].data:
    v.radius = (0.008, 0.008)
band.data.materials.append(plastic)
for s in (-1, 1):
    sphere(f"hp_cup{s}", 0.035, (0, s * 0.065, -0.03), plastic, segs=10, rings=6, scale=(1, 0.55, 1.15), parent=hp)

# Microphone on a boom arm, left of the monitor
arm = empty("mic_arm", (-0.62, 0.95, DESK_Z))
box("mic_clamp", (0.05, 0.06, 0.06), (0, 0, 0.03), plastic, parent=arm)
cyl("mic_pole", 0.012, 0.012, 0.32, (0, 0, 0.22), plastic, segs=8, parent=arm)
cyl("mic_boom", 0.01, 0.01, 0.42, (0.07, -0.18, 0.43), plastic, segs=8, rot=(math.radians(65), 0, math.radians(-20)), parent=arm)
cyl("mic_head", 0.03, 0.03, 0.13, (0.15, -0.36, 0.5), mat("mic", "#2E3036", 0.4), segs=10, rot=(math.radians(90), 0, math.radians(-20)), parent=arm)

# Chair (behind her)
chair = empty("chair", (0.0, -0.12, 0))
box("chair_seat", (0.5, 0.48, 0.07), (0, 0, 0.47), chair_m, bevel=0.02, parent=chair)
box("chair_back", (0.44, 0.07, 0.34), (0, -0.25, 0.72), chair_m, rot=(math.radians(-8), 0, 0), bevel=0.02, parent=chair)
cyl("chair_post", 0.03, 0.03, 0.4, (0, 0, 0.23), alu, segs=8, parent=chair)

# Cozy corner behind her: bookshelf, floor lamp, poster, string lights
FW = -2.55  # front wall face
shelf = empty("bookshelf", (-0.75, FW + 0.17, 0))
book_cols = ["#C0533B", "#2F5D8C", "#E0B04A", "#4C7A55", "#8A5A9E", "#D9D2C5", "#3A3F4B"]
for lvl in range(4):
    box(f"shelf_board_{lvl}", (0.9, 0.3, 0.025), (0, 0, 0.35 + lvl * 0.4), wood_dark, parent=shelf)
    x = -0.4
    while x < 0.38:
        bw, bh = random.uniform(0.03, 0.06), random.uniform(0.2, 0.32)
        if random.random() < 0.12:
            x += 0.08
            continue
        box(f"book_{lvl}_{x:.2f}", (bw, 0.2, bh), (x + bw / 2, 0, 0.36 + lvl * 0.4 + bh / 2),
            mat(f"book_{random.randint(0, 6)}", random.choice(book_cols), 0.8), parent=shelf)
        x += bw + 0.004
for sx in (-0.46, 0.46):
    box(f"shelf_side_{sx}", (0.025, 0.3, 1.65), (sx, 0, 0.83), wood_dark, parent=shelf)
lamp = empty("floor_lamp", (-1.35, FW + 0.35, 0))
cyl("lamp_base", 0.12, 0.12, 0.03, (0, 0, 0.015), plastic, segs=10, parent=lamp)
cyl("lamp_pole", 0.012, 0.012, 1.5, (0, 0, 0.77), plastic, segs=6, parent=lamp)
cyl("lamp_shade", 0.16, 0.11, 0.24, (0, 0, 1.58), mat("shade", "#F3E3C8", 0.8, emit="#FFC98A", emit_strength=3.0), segs=10, parent=lamp)
ld = bpy.data.lights.new("lamp_light", "POINT")
ld.energy, ld.color, ld.shadow_soft_size = 60, lin("#FFB36B"), 0.15
lp = bpy.data.objects.new("lamp_light", ld)
lp.location = (0, 0, 1.55)
link(lp, lamp)
box("poster_frame", (0.5, 0.02, 0.68), (0.05, FW + 0.01, 1.55), plastic)
box("poster_art", (0.44, 0.022, 0.62), (0.05, FW + 0.012, 1.55), mat("poster", "#E7C9A0", 0.9, emit="#E7C9A0", emit_strength=0.15))
sphere("poster_sun", 0.09, (0.05, FW + 0.03, 1.62), mat("poster_sun", "#D9632E", 0.9), segs=10, rings=6, scale=(1, 0.1, 1))
box("poster_hill", (0.44, 0.03, 0.2), (0.05, FW + 0.035, 1.33), mat("poster_hill", "#4C7A55", 0.9))

bulb_m = mat("bulb", "#FFFFFF", 0.4, emit="#FFC780", emit_strength=25.0)


def string_lights(name, p1, p2, n, sag):
    p1, p2 = Vector(p1), Vector(p2)
    for k in range(n):
        t = k / (n - 1)
        p = p1.lerp(p2, t)
        p.z -= sag * 4 * t * (1 - t)
        sphere(f"{name}_{k}", 0.018, p, bulb_m, segs=6, rings=4)


string_lights("lights_desk", (-1.1, 1.08, 1.85), (0.95, 1.08, 1.85), 14, 0.2)
string_lights("lights_front", (-1.5, FW + 0.04, 2.2), (0.6, FW + 0.04, 2.2), 13, 0.25)

# ---------------------------------------------------------------- city outside the window (+X)

bm_b, bm_r, bm_w = bmesh.new(), bmesh.new(), bmesh.new()
facades = ["#D9CCB0", "#CDBD9C", "#E4D8C0", "#C9B79A", "#B9A68B", "#DCC6A0"]
fac_mats = [mat(f"facade_{i}", c, 0.9) for i, c in enumerate(facades)]
roof_m = mat("roof", "#A5492F", 0.8)
lit_m = mat("lit_window", "#FFFFFF", 0.5, emit="#FFC27A", emit_strength=6.0)
dark_win = mat("dark_window", "#2A3040", 0.3)
blds = []
for gx in range(16):
    for gy in range(-10, 11):
        x = 6.0 + gx * 3.6 + random.uniform(-0.7, 0.7)
        y = gy * 3.6 + random.uniform(-0.9, 0.9)
        if random.random() < 0.2:
            continue
        w, d, h = random.uniform(2.2, 3.2), random.uniform(2.2, 3.4), random.uniform(4.0, 11.0) + gx * 0.25
        blds.append((gx, x, y, w, d, h))
BASE = -10.0  # the street is ten metres below her floor
for i, (gx, x, y, w, d, h) in enumerate(blds):
    box(f"bld_{i}", (w, d, h), (x, y, BASE + h / 2), random.choice(fac_mats))
    rb = bmesh.new()
    bmesh.ops.create_cone(rb, cap_ends=True, segments=4, radius1=max(w, d) * 0.72, radius2=0.0, depth=1.3)
    from_bm(f"roof_{i}", rb, roof_m, (x, y, BASE + h + 0.65), rot=(0, 0, math.radians(45)))
    if gx > 9:
        continue  # far away: too small to need windows
    for fz in range(int((h - 1.0) // 1.3)):
        for fy in range(int(d // 0.9)):
            wy = y - d / 2 + 0.45 + fy * 0.9
            wz = BASE + 1.0 + fz * 1.3
            on = random.random() < M["lit"]
            box(f"win_{i}_{fz}_{fy}", (0.02, 0.38, 0.55), (x - w / 2 - 0.01, wy, wz), lit_m if on else dark_win)

# Two construction cranes
crane_m = mat("crane", "#E0A12E", 0.6)
for cx, cy, ch, ang in [(24, 8, 26, 20), (38, -16, 30, -35)]:
    c = empty(f"crane_{cx}", (cx, cy, -10))
    c.rotation_euler = (0, 0, math.radians(ang))
    box("mast", (0.5, 0.5, ch), (0, 0, ch / 2), crane_m, parent=c)
    box("jib", (0.35, 14, 0.4), (0, -4, ch), crane_m, parent=c)
    box("counter", (0.8, 2.5, 0.8), (0, 3.2, ch - 0.4), mat("crane_weight", "#5B5F66", 0.7), parent=c)
    sphere("crane_light", 0.25, (0, -11, ch + 0.3), mat("red_light", "#FF3B30", 0.5, emit="#FF3B30", emit_strength=20), parent=c)

# ---------------------------------------------------------------- her

HEAD = Vector((0.0, -0.02, 1.13))
her = empty("her", (0, 0, 0))
head = empty("her_head", HEAD, parent=her)
head.rotation_euler = (math.radians(4), 0, math.radians(-26))  # looking at Claude
R = 0.16
sphere("head", R, (0, 0, 0), skin, segs=14, rings=10, scale=(1.04, 1.0, 0.98), parent=head)

# Bob haircut with bangs: a slightly bigger sphere with the face cut out and trimmed at jaw length.
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=14, radius=R * 1.1)
kill = []
for f in bm.faces:
    c = f.calc_center_median()
    if c.z < (-0.15 if c.y < -0.04 else -0.13):
        kill.append(f)
    elif c.y > 0.03 and abs(c.x) < 0.118 and c.z < 0.05:
        kill.append(f)
bmesh.ops.delete(bm, geom=kill, context="FACES")
for v in bm.verts:  # flare the bob outwards a little at the bottom
    if v.co.z < 0:
        v.co.x *= 1.0 + (-v.co.z) * 0.6
        v.co.y *= 1.0 + (-v.co.z) * 0.3
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.012)
from_bm("hair", bm, hair, (0, -0.005, 0.01), parent=head)
# Bangs: a flat wedge across the forehead
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=R * 1.08)
kill = [f for f in bm.faces if not (f.calc_center_median().y > 0.05 and 0.035 < f.calc_center_median().z < 0.12)]
bmesh.ops.delete(bm, geom=kill, context="FACES")
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.015)
from_bm("bangs", bm, hair, (0, 0.006, 0.0), parent=head)
for k, bx in enumerate((-0.085, -0.045, 0.0, 0.045, 0.085)):  # pointed bang tips over the forehead
    by = math.sqrt(max((R * 1.1) ** 2 - bx * bx - 0.045 ** 2, 0)) + 0.004
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.026, radius2=0.0, depth=0.05 + 0.012 * (k % 2))
    from_bm(f"bang_tip_{k}", bm, hair, (bx, by, 0.035), rot=(math.radians(180), 0, math.radians(45)), parent=head)
for s_ in (-1, 1):  # side locks framing the face, down to the jaw
    limb(f"lock_{s_}", (s_ * 0.13, 0.085, 0.03), (s_ * 0.125, 0.09, -0.12), 0.03, hair, parent=head, segs=6)

# Face: dot eyes with highlights, small nose, rectangular mouth (animated by scale)
for s, name in ((-1, "L"), (1, "R")):
    ex, ez = s * 0.058, 0.0
    ey = math.sqrt(max(R * R - ex * ex - ez * ez, 0)) + 0.004
    eye = sphere(f"eye_{name}", 0.016, (ex, ey, ez), black, segs=10, rings=6, scale=(1, 0.5, 1.15), parent=head)
    sphere(f"eye_hl_{name}", 0.0045, (ex + 0.005, ey + 0.008, ez + 0.007), white, segs=6, rings=4, parent=head)
    # gold hoop earring
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, segments=10, radius=0.016)
    me = bpy.data.meshes.new(f"hoop_{name}")
    bm.to_mesh(me)
    bm.free()
    hoop = bpy.data.objects.new(f"hoop_{name}", me)
    link(hoop, head)
    hoop.location = (s * R * 1.0, 0.0, -0.075)
    hoop.rotation_euler = (0, math.radians(90), 0)
    sm = hoop.modifiers.new("thick", "SKIN")
    for v in hoop.data.skin_vertices[0].data:
        v.radius = (0.0025, 0.0025)
    hoop.data.materials.append(gold)
for s_ in (-1, 1):
    cx = s_ * 0.085
    cy = math.sqrt(max(R * R - cx * cx - 0.05 ** 2, 0)) + 0.001
    sphere(f"cheek_{s_}", 0.022, (cx, cy, -0.05), mat("cheek", "#F08A7A", 0.8), segs=8, rings=5, scale=(1.2, 0.35, 0.8), parent=head)
ny = math.sqrt(R * R - 0.025 ** 2) + 0.006
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=3, radius1=0.012, radius2=0.0, depth=0.018)
from_bm("nose", bm, mat("nose", "#DE8E6E", 0.7), (0, ny, -0.028), rot=(math.radians(-90), 0, 0), parent=head)
my = math.sqrt(R * R - 0.07 ** 2) + 0.003
mouth = box("mouth", (0.032, 0.008, 0.006), (0, my - 0.004, -0.072), mouth_m, rot=(math.radians(-25), 0, 0), parent=head)

# Body: an oversized hoodie, chunky and faceted
body = empty("her_body", (0, -0.03, 0), parent=her)
sphere("torso", 0.24, (0, 0, 0.8), hoodie, segs=10, rings=8, scale=(0.9, 0.72, 0.95), parent=body)
sphere("hood", 0.15, (0, -0.11, 0.98), hoodie_dark, segs=10, rings=6, scale=(1.2, 0.8, 0.55), parent=body)
cyl("neck", 0.055, 0.06, 0.08, (0, 0.0, 0.99), skin, segs=8, parent=body)
for s in (-1, 1):
    cyl(f"string_{s}", 0.005, 0.005, 0.15, (s * 0.04, 0.165, 0.87), string_m, segs=5, rot=(math.radians(-14), 0, 0), parent=body)
    shoulder, elbow, wrist = (s * 0.2, 0.0, 0.95), (s * 0.27, 0.13, 0.79), (s * 0.14, 0.33, 0.79)
    sphere(f"shoulder_{s}", 0.075, shoulder, hoodie, segs=8, rings=6, parent=body)
    limb(f"upper_arm_{s}", shoulder, elbow, 0.062, hoodie, parent=body)
    limb(f"forearm_{s}", elbow, wrist, 0.058, hoodie, parent=body)
    sphere(f"cuff_{s}", 0.05, wrist, hoodie_dark, segs=8, rings=6, scale=(1, 0.7, 1), parent=body)
    sphere(f"hand_{s}", 0.04, (s * 0.12, 0.375, 0.79), skin, segs=8, rings=6, scale=(1.1, 1.0, 0.7), parent=body)

# ---------------------------------------------------------------- Claude (on the desk, right of the keyboard)

CL = Vector((0.4, 0.4, DESK_Z))
claude = empty("claude", CL)
claude.rotation_euler = (0, 0, math.atan2(HEAD.x - CL.x, CL.y - HEAD.y))  # local -Y (its face) points at her
body_c = empty("claude_body", (0, 0, 0), parent=claude)  # animated: bounce + squash
ico("claude_blob", 0.08, (0, 0, 0.075), claude_m, subdiv=2, scale=(1.0, 0.95, 0.88), parent=body_c)
for s in (-1, 1):
    sphere(f"cl_eye_{s}", 0.023, (s * 0.032, -0.066, 0.088), white, segs=10, rings=6, scale=(1, 0.6, 1.1), parent=body_c)
    sphere(f"cl_pupil_{s}", 0.013, (s * 0.032, -0.08, 0.086), black, segs=8, rings=6, scale=(1, 0.6, 1.1), parent=body_c)
    sphere(f"cl_hl_{s}", 0.0042, (s * 0.032 + 0.005, -0.088, 0.093), white, segs=6, rings=4, parent=body_c)
    sphere(f"cl_foot_{s}", 0.019, (s * 0.036, -0.012, 0.009), claude_dark, segs=8, rings=5, scale=(1, 1.3, 0.6), parent=claude)

# ---------------------------------------------------------------- lights

world = bpy.data.worlds.new("world")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
bg = wn["Background"]
grad = wn.new("ShaderNodeTexGradient")
mapping = wn.new("ShaderNodeMapping")
texco = wn.new("ShaderNodeTexCoord")
ramp = wn.new("ShaderNodeValToRGB")
world.node_tree.links.new(texco.outputs["Generated"], mapping.inputs["Vector"])
mapping.inputs["Rotation"].default_value = (0, math.radians(-90), 0)  # gradient along Z
world.node_tree.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
world.node_tree.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position = 0.45
ramp.color_ramp.elements[0].color = (*lin(M["hor"]), 1)
ramp.color_ramp.elements[1].position = 0.75
ramp.color_ramp.elements[1].color = (*lin(M["top"]), 1)
world.node_tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = M["world"]


def area(name, loc, target, color, energy, size, shape="SQUARE", size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = lin(color)
    ld.shape = shape
    ld.size = size
    if size_y:
        ld.size_y = size_y
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    link(ob)
    look_at(ob, target)
    return ob


area("window_light", (WX + 0.4, -0.4, 1.5), (0, -0.1, 1.0), M["win"], M["win_e"], 2.6, "RECTANGLE", 2.0)
area("key_monitor", (-0.05, 0.75, 1.25), HEAD, "#FFD3A6", M["key_e"], 0.6)
area("rim_left", (-0.9, -0.7, 1.7), HEAD, "#FFB27A", 18, 0.4)
area("desk_fill", (0.2, 0.2, 1.6), (0.2, 0.4, DESK_Z), "#FFE2C4", 12, 0.8)

# ---------------------------------------------------------------- cameras


def camera(name, loc, target, lens, focus_obj, fstop, hide=()):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.focus_object = focus_obj
    cd.dof.aperture_fstop = fstop
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    ob["hide"] = ",".join(hide)  # objects (and their children) left out of this camera's renders
    link(ob)
    look_at(ob, target)
    return ob


focus_her = empty("focus_her", HEAD + Vector((0.06, 0.12, -0.02)))
focus_claude = empty("focus_claude", CL + Vector((0, -0.05, 0.07)))
camera("CAM_CU", (0.44, 0.74, 1.17), HEAD + Vector((0.02, 0, 0.03)), 62, focus_her, 1.6, hide=("phone", "headphones"))
camera("CAM_OTS", (0.33, -0.2, 1.05), CL + Vector((0, 0, 0.12)), 60, focus_claude, 1.6)
camera("CAM_WIDE", (-1.45, -0.5, 2.0), (0.25, 0.45, 0.85), 24, focus_her, 4.0)
camera("CAM_PORTRAIT", (0.0, 0.8, 1.15), HEAD, 50, focus_her, 4.0, hide=("monitor", "mic_arm"))


def set_camera(cam_name):
    """Make cam_name active and apply its hide list."""
    cam = bpy.data.objects[cam_name]
    hidden = set(filter(None, cam.get("hide", "").split(",")))
    for ob in bpy.data.objects:
        root = ob
        while root.parent:
            if root.name in hidden:
                break
            root = root.parent
        ob.hide_render = root.name in hidden
    scene.camera = cam


# ---------------------------------------------------------------- render settings

scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = args.samples
try:
    scene.eevee.use_raytracing = True
except AttributeError:
    pass
scene.render.resolution_x = args.res
scene.render.resolution_y = int(args.res * 16 / 9)
scene.render.fps = 30
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass
scene.render.image_settings.file_format = "PNG"

bpy.ops.wm.save_as_mainfile(filepath=args.blend)

if args.stills:
    for cam in ("CAM_CU", "CAM_OTS", "CAM_WIDE", "CAM_PORTRAIT"):
        set_camera(cam)
        scene.render.filepath = f"{args.stills}/{args.mood}_{cam}.png"
        bpy.ops.render.render(write_still=True)
        print("RENDERED", scene.render.filepath)
