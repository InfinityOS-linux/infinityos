#!/usr/bin/env python3
"""Render the boot animation, rEFInd icon and installer icon from one mascot."""

from pathlib import Path
import math

from PIL import Image, ImageFilter, ImageOps


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


installer_icons = repo / "root/usr/share/icons/hicolor"
for size in (32, 48, 64, 128, 256):
    destination = installer_icons / f"{size}x{size}/apps/infinity-installer.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    centered_icon(size, max(2, round(size * 0.07))).save(destination, optimize=True)

refind_icons = repo / "root/usr/share/infinityos/refind-theme/icons"
for name in ("os_infinityos.png", "os_infinityos_live.png"):
    centered_icon(128, 5).save(refind_icons / name, optimize=True)

theme = repo / "root/usr/share/plymouth/themes/infinityos"
mascot = ImageOps.contain(source, (205, 175), Image.Resampling.LANCZOS)
frame_size = (280, 210)
position = ((frame_size[0] - mascot.width) // 2, (frame_size[1] - mascot.height) // 2)
mask = Image.new("L", frame_size)
mask.paste(mascot.getchannel("A"), position)
halo = Image.blend(mask.filter(ImageFilter.GaussianBlur(17)),
                   mask.filter(ImageFilter.GaussianBlur(6)), 0.3)

for frame in range(48):
    pulse = (1 - math.cos(2 * math.pi * frame / 48)) / 2
    alpha = halo.point(lambda value: min(255, round(value * (0.45 + 0.35 * pulse))))
    image = Image.new("RGBA", frame_size, "#8457dc")
    image.putalpha(alpha)
    image.alpha_composite(mascot, position)
    image.save(theme / f"throbber-{frame + 1:04d}.png", optimize=True)

if (theme / "throbber-0001.png").read_bytes() == (theme / "throbber-0025.png").read_bytes():
    raise RuntimeError("The mascot glow frames do not animate")
