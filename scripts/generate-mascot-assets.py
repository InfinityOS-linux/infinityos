#!/usr/bin/env python3
"""Render the installer mascot asset."""

from pathlib import Path

from PIL import Image, ImageOps


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
centered_icon(256, round(256 * 0.07)).save(webui_mascot, optimize=True)
