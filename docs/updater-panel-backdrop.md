# Dock outline and InfinityUpdater backdrop

The adaptive dock uses one Cairo contour for the sides and both lower corners.
The heavier upper highlight is clipped to the top edge. Custom border settings
and panel-mode edge selection continue to use the configured CSS borders.

The adaptive Dash2Dock Animated pill uses the same BMS panel backdrop factory as
InfinityUpdater. It follows the panel's live sigma/brightness or static preset,
with a separate rounded effect for the dock. Its Cairo surface paints the panel
background and visible WACK tint layers in the same order and with the same
effective alpha as the updater, before painting the existing outline. The dock's
old independent light blur and neutral CSS tint no longer determine its adaptive
appearance. Wallpaper sampling still follows each surface's own screen position.

BMS watches the dock's mode, radius and panel pipeline and rebuilds its matching
backdrop after settings or provider changes. Static backgrounds retain their
wallpaper coordinates and rounded clip. If no matching backdrop is ready, the
dock remains transparent with its rounded outline in both themes. Tint polling is bounded and
only repaints mapped docks when the tint changes; destroy removes its timer.
The dock retains BMS's normal Clutter repaint handling instead of requesting the
GTK drawer's complete-frame repaint mode for the lifetime of the desktop.
Custom-background and panel-mode docks retain their existing styling.
The animation and dock-transparency passes keep a valid panel-matched blur group visible. They no
longer unconditionally hides BMS backgrounds or replaces BMS geometry updates
with a no-op. Destroyed, fallback and legacy rectangular groups stay hidden;
the user's unblur-in-overview and transparent-overview preferences remain respected.

InfinityUpdater's Shell extension puts a separate backdrop below the GTK window
surface and clips it to the window frame, excluding the shadow. Blur My Shell's
panel controller creates the backdrop from the same static preset or live
sigma/brightness settings as the top panel. Each surface owns its effects and
follows its monitor's wallpaper coordinates. Panel tint layers are applied in
paint order; the window contents retain full opacity and sharp text.

The GTK content area is transparent only after the Shell has created a working
backdrop. The extension exports a `Ready` property on
`org.gnome.Shell`, path `/org/infinityos/UpdaterBackdrop`, interface
`org.infinityos.UpdaterBackdrop`. GTK loads it asynchronously and follows property
changes and Shell owner loss. A delayed setup or a failed first attempt can recover
while the window stays open, without a blocking extension-state RPC.
The header stays transparent and uses the same backdrop as the content area.
The footer adds a subtle black overlay in both color schemes.
The drawer opens with one cubic ease-out slide directly to its resting position,
without overshoot or an elastic return; reduced motion disables the slide.
With a ready backdrop, GTK window shadows, button ripple filters and the external
restart glow are disabled. Buttons keep their opaque rounded fill and a rounded
keyboard focus border; these controls must not paint rectangular shadow bounds
over the transparent window. The opaque fallback retains its existing styling.
Without the extension the app keeps its opaque fallback; disabling panel blur
also restores an opaque backdrop. Closing/minimizing the drawer, disabling the
extension, and rebuilding the panel release the extra effects and timers.

Live matching backdrops request unclipped compositor redraws only for their
lifetime. Native background blur cannot reliably sample pixels outside a GTK
hover damage rectangle under clipped redraws; CSS-only checks cannot detect this
feedback. The existing BMS artifact preference remains in force after the last
drawer backdrop is destroyed. Static wallpaper blur does not request full frames.

The top bar suppresses the power-profile glyph and connected Ethernet glyph.
Wi-Fi keeps its native signal icon, including when Ethernet is also active.
Without either active link, the primary network glyph shows disconnected.
VPN status and Quick Settings controls are preserved.

## Validation

Run the dock-border, dock-outline, updater-indicator, updater-panel-backdrop,
and panel-matching-backdrop Node tests and the updater backdrop Python tests.
Run the Fedora GTK gate and GNOME 51 native Shell smoke test before release.
The native test paints the dock contour and opens the production updater window
and stylesheet over the real native blur produced by the panel factory. It checks
that GTK is opaque before blur is ready, transparent after setup, and switches back
and recovers when the blur is disabled, detached and reattached. Only package IO
is stubbed in this client.

After updating the extension RPMs, sign out and back in on Wayland. Check the
lower dock arcs at 100%, fractional and 200% scale, then open/close the drawer,
switch themes and monitors, and change the panel's static/dynamic blur settings.
Confirm that the header matches the content backdrop, the footer shading is
subtle, and GTK labels/buttons stay sharp. Opening must slow to a stop without
overshoot, including after quickly reversing a closing drawer.
The GTK gate renders the window surface and every action button against the
bundled light/dark Orchis theme in normal, hover, pressed, keyboard-focus,
unfocused and disabled states. It checks that button corners and surrounding
pixels stay transparent while button fills remain opaque.
Check that a user-installed copy of an extension is not masking the RPM files.

Rebuild `infinity-updater` and `infinityos-shell-extensions` from the same commit
before publishing an image. Preserve the existing package build-revision markers.

The updater's normal check action uses `view-refresh-symbolic`, with a localized
tooltip and accessible name. The restart action retains its text label.

The dock parent is not redirected into its own offscreen framebuffer: a dynamic
BACKGROUND blur needs the stage behind it, while a transparent parent framebuffer
contains no wallpaper to sample. Individual icon renderers retain their offscreen
surfaces. The native smoke test samples a black/white edge through the GPU blur,
then restores parent redirection as a negative control and checks that the edge
becomes sharp again. A mapped actor and attached effect alone are insufficient.

The dock's BMS discovery proxy is mapped and bound to the dock's size, and points
at the actual visible pill. Native blur follows pill allocation changes and sits
below the tint and icons. Default dock brightness is 0.9, with the blur corner
radius taken from the dock itself. The native Shell smoke test verifies discovery,
GPU-effect creation, geometry, resizing and hiding.

RPM candidates explicitly skipped by DNF's dependency solver are grouped under
"Waiting for compatibility". This is a read-only resolve with the installer's
no-best policy, not a download or a staged transaction. The grouping matches
name, architecture and version, is recalculated on each check, and does not use
package-name heuristics. If the solver fails, candidates stay visible with a
check warning. Missing solver bindings on older installations also retain the
normal candidates until the new RPM dependency is installed.

Held candidates do not count toward the available-update pill or panel badge,
and cannot enable an install action by themselves. Downloaded offline versions
remain in the restart-required flow. The Fedora gate builds a disposable local
RPM repository to verify a dependency hold and its automatic release, while
checking that the installed RPM database remains unchanged.

User tray spacing is based on centered content groups, including GPaste's nested
status box, rather than equal outer cells alone. Native icon and group alignment
is restored when an app is pinned back to the panel or the tray is disabled.
Indicators that hide themselves do not leave a reserved empty tray cell.
