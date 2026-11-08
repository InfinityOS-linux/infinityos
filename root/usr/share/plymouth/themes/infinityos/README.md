# Infinity OS Horizon

User-provided Horizon animation, supplied 2026-11-08 as
`infinityos-boot-horizon-frames.zip` (1280×720, 180 frames at 30 fps).
The same 480×270 RGBA frames serve Plymouth and the GTK Live welcome page.
Playback is 15 fps, once, holding frame 89. No video decoder is needed at boot.

Conversion from the supplied PNG sequence:

```sh
ffmpeg -framerate 30 -i input/frame-%03d.png -vf "$(cat horizon-filter.txt)" output/frame-%03d.png
```

Use separate input/output directories, then rename output frames 001–090 to
`horizon-0.png`–`horizon-89.png`. Alpha is the maximum RGB channel; RGB is unpremultiplied by that alpha.
This preserves the glow on black without dark fringes on light backgrounds.
The black background becomes transparent so
that the logo also blends with the welcome page. The theme itself stays black.
