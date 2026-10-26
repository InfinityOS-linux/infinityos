# DING profiling and targeted optimization (2026-10-26)

## Tested build and ownership

The ARM live VM reports Infinity OS 44 (Fedora 44 base), GNOME Shell 50.6,
GJS 1.88.1, GTK 4.22.5, libadwaita 1.9.4, and DING 99. DING is GPL-3.0-only
(`COPYING` and SPDX headers). The maintained source is
`root/usr/share/gnome-shell/extensions/ding@rastersoft.com/`. On an installed
system, the `infinityos-shell-extensions` RPM owns
`/usr/share/gnome-shell/extensions/ding@rastersoft.com/`; the tested VM had
`infinityos-shell-extensions-1.0.0-10000116.fc44.noarch`. Its schema is compiled
by the RPM post-transaction script. No Fedora-owned file was edited for this
work. GNOME Shell 50 compatibility is declared in `metadata.json` and the RPM
requires `gnome-shell >= 50, < 51`.

The Shell-side `extension.js` tracks monitor geometry and launches a separate
GJS/libadwaita desktop process. `app/ding.js` initializes it. `desktopManager.js`
monitors and enumerates Desktop, builds the file list, and places icons through
`desktopGrid.js` and `fileItem.js`. `desktopMenu.js`, `fileItemMenu.js`, and the
drag/clipboard modules provide the context menus and file operations.
`thumbnails.js` uses GnomeDesktop's thumbnail factory or its helper process.
Settings live in the DING GSettings schema. Integration uses Gio/GVfs metadata,
GNOME Shell's Meta/St APIs, Nautilus file operations and preview D-Bus APIs,
File Roller, and optional Switcheroo Control. The earlier Infinity OS menu
animation and dismissal changes from `e9d0d2f` remain in this version.

## Measurement method

The previous source at `e9d0d2f` and the candidate source were each copied to
`~/.local/share/gnome-shell/extensions/ding@rastersoft.com` in the same ARM VM.
The system RPM directory was untouched. A VM snapshot named
`Before DING profiling 2026-10-26` and a copy at
`~/ding-before-optimization` provide rollback. Temporary VM-only log markers
recorded the end of `_drawDesktop()`, file construction, grid placement, and
main-loop timer gaps; these markers are absent from the shipped code.

The same workload restarted the extension three times, sampled five seconds
of idle CPU, moved 100 then 500 text files onto Desktop, and refreshed one
file three times. Files were removed after the draw and a settling interval.
CPU time and RSS came from `/proc` for the separate DING `gjs` process; GNOME
Shell and graphics memory are excluded. These are single VM workload runs,
not hardware-independent performance guarantees.

| Observation | Before | After (200-file async batches) |
| --- | ---: | ---: |
| Startup to completed first draw, 3 runs | 264, 279, 283 ms | 183, 321, 479 ms |
| Idle DING CPU over 5 s / RSS | 0.8% / 218 MiB | 0.6% / 219 MiB |
| 100 files: last move to completed draw | 193 ms | 226 ms |
| 500 files: last move to completed draw | 277 ms | 289 ms |
| 500 files: DING CPU time / RSS | 150 ms / 240 MiB | 140 ms / 240 MiB |
| Single-file refresh, 3 runs | 5.5, 4.6, 5.7 ms | 6.5, 13.0, 6.6 ms |
| Longest contiguous file-construction batch at 500 files | 54 ms | 18 ms |
| Grid placement at 500 files | 73 ms | 79 ms |
| Main-loop gap caused by final 500-file draw | 132 ms | 80 ms |

The workload's absolute maximum timer gap after the change was 134 ms, but
the log places that gap **before** file construction; VM scheduling also causes
long unrelated gaps. The 80 ms gap follows the completed draw. The optimization
therefore reduces the DING work that blocks interaction, while total draw
latency is slightly longer. Startup, idle CPU, and RSS show no reliable gain.
GTK icon creation and grid placement remain the dominant work after batching.

## Confirmed defects and implementation

The old `_doReadAsync()` synchronously built every file item in one GTK callback.
It also swallowed an enumeration error and returned `null`, making
`_updateDesktop()` retry every 100 ms indefinitely. Denying Desktop read
permission in the VM reproduced repeated `Permission denied` attempts. The
new reader handles a small first batch immediately, yields via GIO's async
enumerator for larger directories, closes the enumerator, and destroys
partially created items on cancellation/error. Persistent errors now reach the
existing caller's log handler and stop that update. A new file event after
permissions were restored redrew the desktop and the extension stayed active.

The thumbnail queue could discard a destroyed or missing file without settling
its Promise. Failed-thumbnail and helper-error paths had the same issue. The
queue now settles those cases with `null`, handles backend failures, and starts
failed-thumbnail fallback only once if a timeout races with cancellation. A
late callback also cannot remove the next thumbnail's timer.
`tests/ding-thumbnails.gjs` reproduced the stuck Promise on the previous code
and passes six cases on the new code in the Fedora 44 VM.
`tests/ding-refresh.gjs` reproduced the stale busy flag after a failed read
on the previous code and verifies a subsequent update on the new code.

Rewriting the extension in Rust/C would still need GNOME Shell's GJS APIs and
GTK icon placement on the UI thread. It would add a native ABI or IPC layer
without addressing the measured grid cost. GIO batching is the smallest
change that reduces the confirmed main-loop stall while preserving menus,
settings, keyboard access, icon metadata, and GNOME 50 integration.

## Run and recovery

The updated source is included in the next `infinityos-shell-extensions` RPM
when the main-branch RPM publishing workflow completes. An installed system
loads it after the RPM update and a GNOME Shell session restart. The test VM
runs a user extension copy at
`~/.local/share/gnome-shell/extensions/ding@rastersoft.com`; verify it with
`gnome-extensions info ding@rastersoft.com` and run the focused test with
`gjs -m tests/ding-thumbnails.gjs /path/to/ding/app/thumbnails.js` and
`gjs -m tests/ding-refresh.gjs /path/to/ding/app/desktopManager.js`.

To restore the VM's previous test copy quickly, copy
`~/ding-before-optimization/app/desktopManager.js` and `thumbnails.js` back
into the user extension and run `gnome-extensions disable ding@rastersoft.com`
followed by `gnome-extensions enable ding@rastersoft.com`. To return to the
RPM-owned version, remove the user extension copy and log out/in; GNOME Shell
selects the system path at the next login. The VM snapshot restores the whole
pre-test environment.

The VM checks covered ARM and GNOME 50.6. They did not measure x86_64,
multi-monitor placement, very large icon counts beyond 500, or graphical menu
input through Parallels, whose guest input integration was unavailable. The
existing menu behavior and GTK accessibility interfaces were left intact.
