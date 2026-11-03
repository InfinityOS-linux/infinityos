# Infinity system application icons

The InfinitySetup, Infinity Config, InfinityUpdater, InfinityTerminal and Live
Installer artwork shares a sculpted violet and lavender style with white symbols.
The user approved the concept family on 2026-11-03. Original artwork was generated
using OpenAI ImageGen and is shipped as PNG with alpha transparency.

Application icons are installed under hicolor/512x512/apps, preserving their
existing desktop-file icon names and application IDs. InfinitySetup also keeps
its private catalog image. The Live Installer uses its existing 256x256 PNG path.
The update indicator keeps its monochrome symbolic icon for panel readability.

System desktop entries use the absolute path of their packaged 512px artwork.
This keeps the approved artwork independent of icon-theme lookup preferences
and third-party theme overrides. The animated dock clears its visual icon clones
after a debounced TextureCache invalidation; it does not recreate the dash or
restart its services during RPM transactions.
