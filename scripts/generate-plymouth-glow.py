#!/usr/bin/env python3
"""Regenerate Plymouth frames. Requires Pillow and rsvg-convert on the build host."""

from io import BytesIO
from pathlib import Path
import math
import subprocess

from PIL import Image, ImageFilter


theme = Path(__file__).resolve().parents[1] / "root/usr/share/plymouth/themes/infinityos"
rendered = subprocess.run(
    ["rsvg-convert", "-w", "512", "-h", "512", str(theme / "symbol.svg")],
    check=True,
    capture_output=True,
).stdout
source = Image.open(BytesIO(rendered)).convert("RGBA")
symbol = source.crop(source.getbbox())
symbol = symbol.resize((115, round(symbol.height * 115 / symbol.width)), Image.Resampling.LANCZOS)
size = (220, 140)
x = (size[0] - symbol.width) // 2
y = (size[1] - symbol.height) // 2
mask = Image.new("L", size)
mask.paste(symbol.getchannel("A"), (x, y))
wide = mask.filter(ImageFilter.GaussianBlur(15))
tight = mask.filter(ImageFilter.GaussianBlur(5.5))
halo = Image.blend(wide, tight, 0.27)

for frame in range(48):
    pulse = (1 - math.cos(2 * math.pi * frame / 48)) / 2
    opacity = 0.26 + 0.20 * pulse
    alpha = halo.point(lambda value: min(255, round(value * 2.0 * opacity)))
    image = Image.new("RGBA", size, "#645394")
    image.putalpha(alpha)
    image.alpha_composite(symbol, (x, y))
    image.save(theme / f"throbber-{frame + 1:04d}.png", optimize=True)

if (theme / "throbber-0001.png").read_bytes() == (theme / "throbber-0025.png").read_bytes():
    raise RuntimeError("The glow frames do not animate")
