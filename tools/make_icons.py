"""Draws the SalonSlotly app icons (a calendar with time slots). Run once: python tools\\make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw

BRAND = "#1d4ed8"
LIGHT = "#bfdbfe"
SLOT = "#dbeafe"
OUT = Path(__file__).resolve().parent.parent / "static" / "icons"


def make_icon(size):
    big = size * 4          # draw large, then shrink, for smooth edges
    k = big / 512
    img = Image.new("RGB", (big, big), BRAND)
    d = ImageDraw.Draw(img)

    def box(x0, y0, x1, y1):
        return (x0 * k, y0 * k, x1 * k, y1 * k)

    # white calendar card, kept inside the centre so round icon masks don't cut it
    d.rounded_rectangle(box(116, 128, 396, 384), radius=32 * k, fill="white")
    # header bar with square bottom corners
    d.rounded_rectangle(box(116, 128, 396, 200), radius=32 * k, fill=LIGHT)
    d.rectangle(box(116, 168, 396, 200), fill=LIGHT)

    # 3 x 2 grid of time slots, one highlighted as "booked"
    for row in range(2):
        for col in range(3):
            x = 144 + col * 80
            y = 236 + row * 64
            colour = BRAND if (row, col) == (0, 1) else SLOT
            d.rounded_rectangle(box(x, y, x + 64, y + 48), radius=10 * k, fill=colour)

    return img.resize((size, size), Image.Resampling.LANCZOS)


OUT.mkdir(parents=True, exist_ok=True)
for name, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
    make_icon(size).save(OUT / name)
    print("created", OUT / name)