# InfinityOS glove cursors

These two glove states use the artwork approved on 18 November 2026.
`grab.png` is the open hover hand; `grabbing.png` is the closed drag hand.
Both images use a common canvas and palm hotspot so the drag origin stays put.

Run `python3 scripts/build-infinity-cursors` with ImageMagick installed to rebuild
the native cursor files. Each includes 16, 24, 32, 48, 64, 96 and 128 pixel sizes
and premultiplied ARGB pixels. Runtime use does not require ImageMagick.

The `InfinityOS-Modern-Ice` theme inherits Bibata Modern Ice for the remaining
pointer shapes. Existing custom cursor themes are preserved during migration.
