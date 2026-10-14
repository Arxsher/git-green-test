"""Generate the screen images shown on the monitor and laptop in the 3D set.

Usage: python make_textures.py OUTDIR
Writes code_editor.png (ultrawide monitor) and chat.png (laptop).
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
random.seed(7)

# Syntax colours on a dark editor background.
BG = (24, 26, 38)
GUTTER = (32, 35, 50)
SYNTAX = [(199, 146, 234), (130, 170, 255), (195, 232, 141), (247, 140, 108), (137, 221, 255), (105, 112, 152)]


def code_column(d, x0, y0, width, lines, line_h):
    indent = 0
    for i in range(lines):
        y = y0 + i * line_h
        if random.random() < 0.12:
            continue  # blank line
        indent = max(0, min(4, indent + random.choice([-1, 0, 0, 0, 1])))
        x = x0 + indent * 28
        for _ in range(random.randint(1, 4)):
            w = random.randint(30, 140)
            if x + w > x0 + width:
                break
            d.rounded_rectangle([x, y + 6, x + w, y + line_h - 8], radius=5, fill=random.choice(SYNTAX))
            x += w + 14


def code_editor(path):
    W, H = 2400, 1000
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 46], fill=(18, 19, 28))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([20 + i * 30, 14, 38 + i * 30, 32], fill=c)
    d.rectangle([0, 46, 70, H], fill=GUTTER)
    # Two editor panes and a highlighted line, like a real IDE.
    d.rectangle([72, 46 + 31 * 12, 1180, 46 + 32 * 12 + 18], fill=(48, 52, 76))
    code_column(d, 100, 60, 1060, 30, 31)
    d.line([1200, 46, 1200, H], fill=(40, 43, 60), width=4)
    code_column(d, 1230, 60, 1130, 30, 31)
    img.save(path)


def chat(path):
    W, H = 1600, 1000
    img = Image.new("RGB", (W, H), (30, 30, 34))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 300, H], fill=(22, 22, 26))
    for i in range(9):
        d.rounded_rectangle([24, 90 + i * 70, 270, 130 + i * 70], radius=10, fill=(40, 40, 46))
    y = 80
    for i in range(6):
        if i % 2 == 0:  # user message, right aligned
            w = random.randint(380, 700)
            d.rounded_rectangle([1520 - w, y, 1520, y + 70], radius=18, fill=(58, 58, 66))
            y += 110
        else:  # assistant reply: lines of text with an orange marker
            d.ellipse([360, y + 4, 392, y + 36], fill=(217, 119, 87))
            for k in range(random.randint(2, 4)):
                w = random.randint(600, 1050)
                d.rounded_rectangle([420, y + k * 38, 420 + w, y + k * 38 + 18], radius=8, fill=(150, 150, 160))
            y += 190
    d.rounded_rectangle([380, H - 120, 1520, H - 50], radius=24, fill=(48, 48, 56), outline=(217, 119, 87), width=3)
    img.save(path)


code_editor(out / "code_editor.png")
chat(out / "chat.png")
print("ok")
