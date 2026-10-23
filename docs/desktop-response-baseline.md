# Desktop response baseline

Measured on 2026-10-20 in the freshly installed ARM VM described in
`installation-smoke-test.md`. The source image was revision `3a68997`; the
Terminal extension fix was copied into the VM for its separate interaction
check. These numbers are observations of this VM, not performance promises for
other hardware.

## Session startup

After graphical login, run as the desktop user:

```sh
systemd-analyze --user critical-chain default.target
systemd-analyze --user blame
```

`default.target` became active at **94 ms**. GNOME Shell took **585 ms**,
GPaste **1.228 s**, and InfinityUpdater **2.683 s**. Those services were not in
the displayed critical chain for `default.target`; their `blame` durations
must not be added to get a desktop-ready time. On an earlier installed ARM VM,
the same commands showed 84 ms for `default.target`, 512 ms for GNOME Shell,
1.608 s for GPaste, and 2.333 s for InfinityUpdater.

## Interaction checks

From a shell for the logged-in user, time the launch request with:

```sh
time env XDG_RUNTIME_DIR=/run/user/$(id -u) \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus \
  WAYLAND_DISPLAY=wayland-0 gtk-launch org.infinityos.Setup
```

The earlier application ID returned after **0.08 s** on the fresh VM (about
**0.095 s** on the earlier VM). The command above uses the current InfinitySetup
ID and has not been timed. The figures measure only the launch request; the
application window was subsequently confirmed on screen, without measuring
the time to first paint.

The dock was present and the Terminal icon was visible after login. The
Terminal launch interaction was verified separately, as recorded in the
installation smoke test. A dock click latency was not measured.

For the desktop context menu, press `Super+D` to show the desktop, `Esc` and
`Tab` to focus its icon layer, then `Shift+F10`. Capture the screen until the
menu appears. In three automated Parallels console runs,
the menu was detected in the first or second screenshot after **0.546 s**,
**0.763 s**, and **0.819 s**. Those are upper bounds for console key delivery,
screen capture and menu painting together; they are not isolated GNOME menu
latencies. The menu was visibly populated.

No reproducible delay in these checks established a code optimization. A
future performance change should first measure input-to-paint latency for the
dock and InfinitySetup directly, then compare it with this session baseline.
