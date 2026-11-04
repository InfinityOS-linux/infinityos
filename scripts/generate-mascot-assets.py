#!/usr/bin/env python3
"""Render the boot animation and welcome icon from the mascot."""

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFilter, ImageOps


repo = Path(__file__).resolve().parents[1]
source = Image.open(repo / "assets/infinityos-mascot.png").convert("RGBA")
# Ignore very faint extraction noise when finding the mascot's bounds.
bounds = source.getchannel("A").point(lambda alpha: 255 if alpha > 32 else 0).getbbox()
if not bounds:
    raise RuntimeError("Mascot image has no visible pixels")
source = source.crop(bounds)


def centered_icon(size, inset):
    canvas = Image.new("RGBA", (size, size))
    mascot = ImageOps.contain(source, (size - 2 * inset, size - 2 * inset), Image.Resampling.LANCZOS)
    canvas.alpha_composite(mascot, ((size - mascot.width) // 2, (size - mascot.height) // 2))
    return canvas


webui_mascot = repo / "root/usr/share/cockpit/anaconda-webui/infinityos-installer-mascot.png"
welcome_icon = repo / "root/usr/share/icons/hicolor/256x256/apps/infinityos-welcome.png"
for destination in (webui_mascot, welcome_icon):
    centered_icon(256, round(256 * 0.07)).save(destination, optimize=True)

theme = repo / "root/usr/share/plymouth/themes/infinityos"
mascot = ImageOps.contain(source, (205, 175), Image.Resampling.LANCZOS)
frame_size = (280, 270)
shadow = Image.new("L", frame_size)
ImageDraw.Draw(shadow).ellipse((62, 210, 218, 224), fill=90)
shadow = shadow.filter(ImageFilter.GaussianBlur(9))

for frame in range(48):
    float_offset = round(2 * math.sin(2 * math.pi * frame / 48))
    position = ((frame_size[0] - mascot.width) // 2, 24 + float_offset)
    image = Image.new("RGBA", frame_size, (12, 8, 20, 0))
    image.putalpha(shadow)
    image.alpha_composite(mascot, position)
    image.save(theme / f"throbber-{frame + 1:04d}.png", optimize=True)

if (theme / "throbber-0001.png").read_bytes() == (theme / "throbber-0013.png").read_bytes():
    raise RuntimeError("The mascot frames do not animate")
