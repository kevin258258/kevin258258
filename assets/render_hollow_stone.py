"""Render the README's ASCII sculpture. Requires Pillow and NumPy.

Run: python assets/render_hollow_stone.py [--font /path/to/monospace.ttf]
The sculpture is ray traced as four stone beams, then drawn only as text.
"""

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 900, 660
COLS, ROWS = 85, 30
FRAMES, DURATION = 120, 80
ROOT = Path(__file__).resolve().parent
THEMES = {
    "dark": ((13, 17, 23), (222, 226, 230), (121, 131, 141)),
    "light": ((255, 255, 255), (35, 40, 45), (112, 120, 127)),
}


def sculpture(phase):
    yaw = phase * math.tau + 0.30
    tilt = 0.18 + 0.05 * math.sin(phase * math.tau)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cx, sx = math.cos(tilt), math.sin(tilt)
    rotation = np.array([
        [cy, sy * sx, sy * cx],
        [0, cx, -sx],
        [-sy, cy * sx, cy * cx],
    ])
    xx, yy = np.meshgrid(
        np.linspace(-3.45, 3.45, COLS),
        np.linspace(2.05, -2.05, ROWS),
    )
    yy -= 0.07 * math.sin(phase * math.tau)
    origin = np.stack([xx, yy, np.full_like(xx, 8)], axis=-1) @ rotation
    direction = np.array([0, 0, -1]) @ rotation
    # A real opening passes through the entire depth of the slab.
    boxes = [
        ((-1.38, -1.65, -0.28), (-0.80, 1.65, 0.28)),
        ((0.80, -1.65, -0.28), (1.38, 1.65, 0.28)),
        ((-0.80, 1.04, -0.28), (0.80, 1.65, 0.28)),
        ((-0.80, -1.65, -0.28), (0.80, -1.04, 0.28)),
    ]
    depth = np.full(xx.shape, np.inf)
    normals = np.zeros((*xx.shape, 3))
    for lower, upper in boxes:
        # Parallel rays are treated as lying inside/outside an infinite slab.
        a = np.empty_like(origin)
        b = np.empty_like(origin)
        for axis in range(3):
            if abs(direction[axis]) < 1e-10:
                inside = (origin[..., axis] >= lower[axis]) & (
                    origin[..., axis] <= upper[axis]
                )
                a[..., axis] = np.where(inside, -np.inf, np.inf)
                b[..., axis] = np.where(inside, np.inf, -np.inf)
            else:
                t1 = (lower[axis] - origin[..., axis]) / direction[axis]
                t2 = (upper[axis] - origin[..., axis]) / direction[axis]
                a[..., axis], b[..., axis] = np.minimum(t1, t2), np.maximum(t1, t2)
        near, far = a.max(axis=-1), b.min(axis=-1)
        hit = (near <= far) & (near > 0) & (near < depth)
        face = a.argmax(axis=-1)
        normal = np.zeros_like(normals)
        for axis in range(3):
            normal[..., axis] = np.where(
                face == axis, -np.sign(direction[axis]), 0
            )
        normals[hit] = (normal @ rotation.T)[hit]
        depth[hit] = near[hit]
    mask = np.isfinite(depth)
    light = np.array([-0.45, 0.65, 0.75])
    light /= np.linalg.norm(light)
    shade = 0.20 + 0.75 * np.clip(normals @ light, 0, 1)
    # Texture stays attached to the stone instead of flickering every frame.
    points = origin + np.where(mask, depth, 0)[..., None] * direction
    grain = np.sin(points[..., 0] * 17 + points[..., 1] * 23) * 0.055
    shade = np.clip(shade + grain, 0, 0.999)
    ramp = np.array(list(".:-=+*#%@"))
    chars = np.where(mask, ramp[(shade * len(ramp)).astype(int)], " ")
    # Sparse dust and registration marks give the sculpture a printed setting.
    for row, col, char in [(4, 12, "+"), (8, 71, "."), (22, 13, "."), (25, 72, "+")]:
        chars[row, col] = char
    return ["".join(row) for row in chars]


def render(lines, theme, font_path):
    background, foreground, muted = THEMES[theme]
    im = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(im)
    small = ImageFont.truetype(font_path, 12)
    title = ImageFont.truetype(font_path, 23)
    mono = ImageFont.truetype(font_path, 16)

    def label(x, y, text, font=small, fill=muted):
        draw.text((x, y), text, font=font, fill=fill)

    def right(y, text):
        label(WIDTH - 42 - draw.textlength(text, font=small), y, text)

    label(42, 24, "H / S")
    right(24, "KINETIC STUDY  /  001")
    label(42, 45, "-" * 113)
    label(42, 72, "H O L L O W   S T O N E", title, foreground)
    right(84, "[ SOLID / VOID ]")
    cell_width = draw.textlength("M", font=mono)
    start_x = (WIDTH - cell_width * COLS) / 2
    for row, line in enumerate(lines):
        label(start_x, 133 + row * 14, line, mono, foreground)
    label(42, 572, "THE SPACE INSIDE THE STONE.", fill=foreground)
    right(572, "ONE FORM. INFINITE RETURNS.")
    label(42, 601, "-" * 113)
    label(42, 626, "HOLLOW-STONE")
    right(626, "TENSORFIELDX.SPACE")
    return im


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default="/usr/share/fonts/noto/NotoSansMono-Regular.ttf")
    args = parser.parse_args()
    if not Path(args.font).is_file():
        parser.error("Choose an installed monospace TrueType font with --font.")
    text_frames = [sculpture(index / FRAMES) for index in range(FRAMES)]
    for theme in THEMES:
        background, foreground, muted = THEMES[theme]
        palette = Image.new("P", (1, 1))
        colors = []
        for index in range(256):
            t = index / 255
            colors.extend(round(a + (b - a) * t) for a, b in zip(background, foreground))
        palette.putpalette(colors)
        frames = [
            render(lines, theme, args.font).quantize(palette=palette, dither=Image.Dither.NONE)
            for lines in text_frames
        ]
        target = ROOT / f"hollow-stone-{theme}.gif"
        frames[0].save(
            target, save_all=True, append_images=frames[1:],
            duration=DURATION, loop=0, disposal=1, optimize=True,
        )
        print(f"{target.name}: {target.stat().st_size / 1024:.0f} KiB / {FRAMES * DURATION / 1000:.1f}s")


if __name__ == "__main__":
    main()
