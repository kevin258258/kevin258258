"""Render a continuously deforming ASCII stone with one persistent hole.

Requires Pillow and NumPy. Run:
    python assets/render_hollow_stone.py [--font /path/to/monospace.ttf]

The surface is a closed tube on a positive, star-shaped centerline. Each
azimuth has a simple closed cross-section, so morphing never cuts, joins,
or self-intersects the surface. All motion is periodic for a seamless loop.
"""

import argparse
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 900, 660
COLS, ROWS = 118, 60
FRAMES, DURATION = 180, 70
ROOT = Path(__file__).resolve().parent
THEMES = {
    "dark": ((13, 17, 23), (235, 239, 243)),
    "light": ((255, 255, 255), (27, 32, 39)),
}
U = np.linspace(0, math.tau, 480, endpoint=False)[:, None]
V = np.linspace(0, math.tau, 160, endpoint=False)[None, :]
RAMP = np.array(list(".,:;-=+*#%@"))
CELL_WIDTH, CELL_HEIGHT = 7, 10


def surface(phase):
    t = phase * math.tau
    square = (1 + math.cos(t)) / 2
    fluid = 1 - square
    power = 2 + 6 * square
    c, s = np.cos(U), np.sin(U)
    radius = 1.65 / (np.abs(c) ** power + np.abs(s) ** power) ** (1 / power)
    radius *= 1 + 0.16 * fluid * np.cos(3 * U - 2 * t)
    radius += 0.07 * fluid * np.sin(5 * U + t)
    center_z = 0.56 * fluid * np.sin(2 * U + t)
    center_z += 0.10 * math.sin(t) * np.cos(3 * U - t)
    twist = 1.10 * fluid * np.sin(3 * U - t) + 0.4 * math.sin(t)
    tube_power = 2 + 6 * square
    tube_radius = (np.abs(np.cos(V)) ** tube_power + np.abs(np.sin(V)) ** tube_power) ** (-1 / tube_power)
    a, b = tube_radius * np.cos(V), tube_radius * np.sin(V)
    width = 0.37 + 0.11 * fluid * np.cos(3 * U + t)
    thickness = 0.26 + 0.12 * fluid
    ripple = 1 + 0.055 * fluid * np.cos(8 * V + 3 * U)
    radial = (width * a * np.cos(twist) - thickness * b * np.sin(twist)) * ripple
    vertical = (width * a * np.sin(twist) + thickness * b * np.cos(twist)) * ripple
    points = np.stack([
        (radius + radial) * c,
        (radius + radial) * s,
        center_z + vertical,
    ], axis=-1)
    # Positive cylindrical radius and a simple tube section preserve the hole.
    assert np.min(radius + radial) > 0.65
    return points


def sculpture(phase):
    t = phase * math.tau
    points = surface(phase)
    tangent_u = np.roll(points, -1, axis=0) - np.roll(points, 1, axis=0)
    tangent_v = np.roll(points, -1, axis=1) - np.roll(points, 1, axis=1)
    normals = np.cross(tangent_u, tangent_v)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    yaw, pitch, roll = 0.20 + 0.46 * math.sin(t), 0.38 + 0.20 * math.cos(t), 0.23 * math.sin(t)
    cy, sy, cx, sx, cr, sr = (
        math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch),
        math.cos(roll), math.sin(roll),
    )
    rotation = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rotation = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ rotation
    rotation = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]]) @ rotation
    world = points @ rotation.T
    normals = normals @ rotation.T
    # Orthographic projection keeps the opening legible during the entire loop.
    col = np.rint((world[..., 0] / 7.40 + 0.5) * (COLS - 1)).astype(int)
    row = np.rint((0.5 - world[..., 1] / 5.60) * (ROWS - 1)).astype(int)
    assert col.min() > 0 and col.max() < COLS - 1
    assert row.min() > 0 and row.max() < ROWS - 1
    flat_cell = (row * COLS + col).ravel()
    # Sort by cell, then depth; the last surface sample wins the z-buffer.
    order = np.lexsort((world[..., 2].ravel(), flat_cell))
    sorted_cells = flat_cell[order]
    last = np.r_[sorted_cells[1:] != sorted_cells[:-1], True]
    visible = order[last]
    cells = flat_cell[visible]
    normal = normals.reshape(-1, 3)[visible]
    light = np.array([-0.45, 0.60, 0.80])
    light /= np.linalg.norm(light)
    diffuse = np.clip(normal @ light, 0, 1)
    rim = (1 - np.abs(normal[:, 2])) ** 2
    reflected = 2 * (normal @ light)[:, None] * normal - light
    specular = np.clip(reflected[:, 2], 0, 1) ** 14
    # Engraved material lines follow the moving surface, with polished highlights.
    engraving = (0.5 + 0.5 * np.cos(22 * U + 4 * np.sin(3 * V))) ** 10
    engraving = np.broadcast_to(engraving, points.shape[:2]).ravel()[visible]
    shade = np.clip(0.12 + 0.60 * diffuse + 0.19 * rim + 0.38 * specular - 0.13 * engraving, 0, 0.999)
    chars = np.full(ROWS * COLS, " ", dtype="<U1")
    chars[cells] = RAMP[(shade * len(RAMP)).astype(int)]
    return ["".join(row) for row in chars.reshape(ROWS, COLS)]


@lru_cache(maxsize=2)
def glyph_tiles(font):
    atlas = np.zeros((128, CELL_HEIGHT, CELL_WIDTH), dtype=np.uint8)
    for char in " " + "".join(RAMP):
        tile = Image.new("L", (CELL_WIDTH, CELL_HEIGHT))
        ImageDraw.Draw(tile).text((0, -3), char, font=font, fill=255)
        atlas[ord(char)] = np.asarray(tile)
    return atlas


def palette_for(theme):
    background, foreground = THEMES[theme]
    return [
        round(a + (b - a) * index / 255)
        for index in range(256)
        for a, b in zip(background, foreground)
    ]


def raster(lines, font):
    codes = np.frombuffer("".join(lines).encode("ascii"), dtype=np.uint8).reshape(ROWS, COLS)
    pixels = glyph_tiles(font)[codes].transpose(0, 2, 1, 3)
    pixels = pixels.reshape(ROWS * CELL_HEIGHT, COLS * CELL_WIDTH)
    canvas = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    x = (WIDTH - pixels.shape[1]) // 2
    y = (HEIGHT - pixels.shape[0]) // 2
    canvas[y:y + pixels.shape[0], x:x + pixels.shape[1]] = pixels
    return Image.fromarray(canvas).convert("P")


def render(lines, theme, font):
    image = raster(lines, font)
    image.putpalette(palette_for(theme))
    return image.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default="/usr/share/fonts/noto/NotoSansMono-Regular.ttf")
    args = parser.parse_args()
    if not Path(args.font).is_file():
        parser.error("Choose an installed monospace TrueType font with --font.")
    font = ImageFont.truetype(args.font, 11)
    text_frames = []
    for index in range(FRAMES):
        text_frames.append(sculpture(index / FRAMES))
        if index % 45 == 0:
            print(f"Geometry: {index}/{FRAMES}", flush=True)
    raster_frames = [raster(lines, font) for lines in text_frames]
    for theme in THEMES:
        frames = [frame.copy() for frame in raster_frames]
        for frame in frames:
            frame.putpalette(palette_for(theme))
        target = ROOT / f"hollow-stone-{theme}.gif"
        frames[0].save(
            target, save_all=True, append_images=frames[1:],
            duration=DURATION, loop=0, disposal=1, optimize=True,
        )
        print(f"{target.name}: {target.stat().st_size / 1024:.0f} KiB / {FRAMES * DURATION / 1000:.1f}s", flush=True)


if __name__ == "__main__":
    main()
