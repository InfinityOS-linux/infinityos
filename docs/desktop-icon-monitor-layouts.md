# Desktop icon positions with multiple monitors

InfinityOS vendors Desktop Icons NG (DING). Previously, each file had one
`metadata::nautilus-icon-position` containing global desktop coordinates.
DING already relocated off-screen icons onto available grids without replacing
that position during a normal monitor change. However, moving or arranging an
icon while undocked replaced the only saved position. There was no independent
position history for the docked and undocked configurations.

DING now also writes `metadata::infinityos-monitor-positions`, a bounded JSON
map of the last 16 logical desktop configurations for each icon. The existing
GVfs metadata backend persists both attributes. It also retains the legacy
position for interoperability and initial migration. Desktop files are not edited.

Configuration keys contain the sorted monitor rectangles and scale factors.
Monitor enumeration, primary-monitor selection, and panel/dock margins are not
part of the key. Negative origins, resolution, layout and scale changes are.
These are spatial configurations, not hardware serial numbers: replacing a
monitor with one having the same logical geometry reuses the spatial layout.

For a known configuration, its saved coordinates take precedence. In a new
configuration, normal DING placement brings off-screen icons onto available
grids, then saves the actual placed positions for that configuration. Moving an
icon changes only the active configuration. Re-enumeration and a fresh DING
process read the profiles from metadata. Redraws and temporary grid reflow do
not replace known preferred positions; explicit moves update the active profile.
Automatic arrangement and stacking continue to follow their existing settings.
Restoration requires sufficient free icon cells on the connected monitors.

Existing coordinates seed the initial configuration when it is first displayed.
Positions that had already been overwritten before this change cannot be
reconstructed. Invalid profile metadata falls back to normal legacy placement.
Incoming drag/drop file operations clear old profiles alongside the legacy
coordinates, so a newly dropped file follows its requested destination.

## Validation

`node --test tests/ding-monitor-layouts.test.mjs` exercises the real manager,
file-coordinate setters and grid placement with GTK/GIO boundaries replaced
by test doubles. It covers undocking, edits while undocked, reconnecting after
reloading persisted metadata, negative monitor origins, changed scale, reordered
monitor enumeration, unchanged redraws, corrupt metadata, bounded history,
vertical fallback distance, occupied-cell fallback, temporary grid reflow and
changing only the primary monitor.

The Fedora GTK CI job also runs `tests/ding-monitor-layouts.gjs` in a private
D-Bus session. It imports the real FileItem module in GJS, writes through Gio
to GVfs metadata, reloads the positions for docked and undocked layouts, and
checks that desktop file contents remain unchanged.

Hardware acceptance sequence after updating and logging in again:

1. With laptop and external monitor active, place different icons on each.
2. Unplug the external monitor. Check that all icons fit on the laptop.
3. Move an icon on the laptop, then log out and back in while undocked.
4. Reconnect the monitor in the original geometry. Check the original positions.
5. Unplug it again. Check that the edited laptop-only layout returns.
6. Repeat with the external monitor to the left or above the laptop, mixed
   scaling, and a change of primary monitor. Newly created files should target
   the selected primary screen; existing icons should retain their layout.

For a regular desktop file, inspect the persisted coordinates with:

```sh
gio info -a 'metadata::nautilus-icon-position,metadata::infinityos-monitor-positions' /path/to/Desktop/file
journalctl --user -b --no-pager | rg 'DING|desktop coordinates|desktop index'
```

Failed GVfs writes are reported through the existing DING coordinate-error log.
