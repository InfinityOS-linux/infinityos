# InfinityTerminal pull handle

The GNOME panel has a shallow symmetrical 180 × 18 logical-pixel handle below
its clock, centered on the primary monitor rather than a transient clock allocation. Its two cubic curves use mirrored control points and match the panel
background. It does not reserve additional desktop work area.

Click or press Enter/Space to toggle InfinityTerminal. Hold the primary mouse
button and pull down to reveal it, then release to settle open. A pull shorter
than 60 pixels closes again; Escape restores the previous open/closed state.
The existing Super+T shortcut, touchpad gestures and lower-edge resize remain.
When a window reaches the primary panel or the terminal is open, the handle
animates to half size. Fullscreen also selects the compact size, with a
hamburger beside the clock when the panel is visible. GNOME retains
its existing fullscreen panel visibility behavior; the extension does not force
the panel over fullscreen applications. Overview and lock screen hide both.

## Validation

Run the pull-handle, edge-resize, first-frame, gestures, resize and window-lifecycle
Node tests. Before release, run GNOME 51 shell smoke tests and visually check:

- Centering at 100% and 200% scale, including a secondary monitor.
- Click, slow drag, rapid drag/release, Escape, and cold terminal launch.
- Fullscreen enter/exit, overview, lock/unlock and extension disable during drag.
- Existing keyboard toggle, hardware strip, lower-edge resize and focus handling.

Package installation includes the entire extension directory, including
pull-handle.js. Rebuild infinity-terminal from the source commit before producing
an ISO; the package build-revision marker remains required.

The handle reconnects when Blur My Shell initializes late or replaces its panel
background. Its blur contour repaints throughout the compact-size animation.
The native Shell smoke test exercises the BMS panel sizing and GPU clip path.
After installing updated GNOME extensions on Wayland, log out and back in so
the session loads the new JavaScript for both the panel and terminal together.

The handle remains usable while compact. Its panel outline remains visible.
Light and dark styles follow the system preference and panel theme. The hamburger
is raised three logical pixels inside the unchanged curve. The adaptive dock
gets a matching top hairline; custom dock borders keep their chosen colors.

Window movement, resizing, minimization and workspace changes update the compact
state. Reduced motion switches size without animation. Dock overlap detection
also runs in live sessions, while retaining pointer access and installer rules.

