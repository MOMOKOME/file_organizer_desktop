"""Build icons/app.ico from the design source icons/file_organizer_icon_source.png.

Developer-only tool; not part of the application or the PyInstaller bundle.

    python -m pip install -r requirements-icon.txt
    python icons/build_icon.py

Technical processing only - the artwork itself is not redrawn or recoloured:
1. The off-white background and drop shadow around the rounded tile are made
   transparent. The background region is found by flood-filling the light
   pixels connected to the image border, so the tile keeps its exact outline.
2. The tile is centred on a square transparent canvas with a small margin.
3. Each icon size is resampled from the full-resolution image (Lanczos, with
   alpha handled premultiplied by Pillow) and written into one .ico file.
"""
from collections import deque
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "file_organizer_icon_source.png"
TARGET = HERE / "app.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]
# Pixels with an RGB sum below this belong to the tile (its navy edge included);
# lighter pixels connected to the border are background or shadow.
TILE_THRESHOLD = 3 * 128
TILE_SHARE = 0.94  # the tile spans 94% of the icon's width/height


def transparent_background(image):
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    outside = bytearray(width * height)
    queue = deque()
    for x in range(width):
        queue.extend(((x, 0), (x, height - 1)))
    for y in range(height):
        queue.extend(((0, y), (width - 1, y)))
    while queue:
        x, y = queue.popleft()
        index = y * width + x
        if outside[index] or sum(pixels[x, y]) < TILE_THRESHOLD:
            continue
        outside[index] = 1
        if x > 0: queue.append((x - 1, y))
        if x < width - 1: queue.append((x + 1, y))
        if y > 0: queue.append((x, y - 1))
        if y < height - 1: queue.append((x, y + 1))
    alpha = Image.frombytes("L", (width, height), bytes(0 if v else 255 for v in outside))
    result = rgb.convert("RGBA")
    result.putalpha(alpha)
    return result


def square_canvas(image):
    tile = image.crop(image.getchannel("A").getbbox())
    side = round(max(tile.size) / TILE_SHARE)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(tile, ((side - tile.width) // 2, (side - tile.height) // 2))
    return canvas


def main():
    master = square_canvas(transparent_background(Image.open(SOURCE)))
    frames = [master.resize((size, size), Image.Resampling.LANCZOS) for size in SIZES]
    frames[-1].save(TARGET, format="ICO", sizes=[(s, s) for s in SIZES],
                    append_images=frames[:-1])
    print(f"{TARGET.name}: {', '.join(f'{s}x{s}' for s in SIZES)} from {SOURCE.name} {Image.open(SOURCE).size}")


if __name__ == "__main__":
    main()
