# Terminal handle cursors and opening motion

The handle uses the approved open glove on hover and the closed glove while
pressed/dragged. A temporary transparent cursor surface retains that shape over
native Wayland windows. Release, Escape, extension teardown and session changes
remove the surface and restore the open hover cursor.

The InfinityOS Modern Ice cursor theme overrides `grab`, `grabbing`, `wait` and
the busy aliases, and inherits the remaining shapes from Bibata Modern Ice. Both glove states use the
same palm hotspot and include 16 through 128 pixel variants. The theme sync
helper migrates the previous default once; custom cursor themes are preserved.

The waiting glove uses the finger-drumming motion approved on 19 November 2026:
four overlapping taps across 40 frames and an 800 ms loop. The fingers shorten
toward fixed knuckles; the palm, thumb, cuff and hotspot remain still. Wait and
progress use the same native animation at all packaged cursor sizes.

Manual handle pulls request a non-bouncing reveal. This request survives a cold
launch and the first-frame delay, including releasing before the terminal is
ready. Clicking the handle and the normal Super+T toggle reset the request to
the default bouncing reveal. Reduced motion still disables the animation.

Run the pull-handle, first-frame and gesture Node tests, cursor file/native
loader tests, cursor migration test, and the GNOME 51 native smoke test. Check
that cursor size and hotspot remain stable across monitors and that no cursor
surface survives release, cancellation or extension disable.
