# InfinityOS glove cursors

These two glove states use the artwork approved on 18 November 2026.
`grab.png` is the open hover hand; `grabbing.png` is the closed drag hand.
Both images use a common canvas and palm hotspot so the drag origin stays put.

The waiting cursor replaces the inherited beachball for both `wait` and
`progress` (including application startup, such as opening a folder). Only the
four fingers drum in sequence. The palm, thumb, cuff and hotspot stay fixed;
the lower hand pixels are identical in every frame. Fingers foreshorten toward
their fixed knuckles, including the fingertip curves, rather than sliding down
as a rigid shape. The motion matches the preview approved on 19 November 2026.
Tapping begins immediately, with 20 ms samples and an 800 ms loop. Each finger
bends for 80 ms, holds contact for 40 ms and returns over 140 ms. Taps start
120 ms apart and overlap naturally, followed by a short resting pause.
There is no initial idle delay, so short folder launches show finger motion. X11 and legacy toolkit aliases
resolve to the same native animation.

`waiting-hand.svg` is the neutral artwork reference. The fingertip control
points and animation timing live in `scripts/build-infinity-cursors`, which
renders 40 transparent frames per size. The packaged cursor needs no renderer,
timer extension or image-processing dependency at runtime. The existing shell
extensions RPM includes the entire theme, so normal updates install it too.

Run `python3 scripts/build-infinity-cursors` with ImageMagick installed to rebuild
the native cursor files. Each includes 16, 24, 32, 48, 64, 96 and 128 pixel sizes
and premultiplied ARGB pixels. Runtime use does not require ImageMagick.

The `InfinityOS-Modern-Ice` theme inherits Bibata Modern Ice for the remaining
pointer shapes. Existing custom cursor themes are preserved during migration.
