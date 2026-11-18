# Dock outline and InfinityUpdater backdrop

The adaptive dock uses one Cairo contour for the sides and both lower corners.
The heavier upper highlight is clipped to the top edge. Custom border settings
and panel-mode edge selection continue to use the configured CSS borders.

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
The header and footer add a subtle black overlay in both color schemes.
With a ready backdrop, GTK window shadows, button ripple filters and the external
restart glow are disabled. Buttons keep their opaque rounded fill and an inset
keyboard focus outline; these controls must not paint rectangular shadow bounds
over the transparent window. The opaque fallback retains its existing styling.
Without the extension the app keeps its opaque fallback; disabling panel blur
also restores an opaque backdrop. Closing/minimizing the drawer, disabling the
extension, and rebuilding the panel release the extra effects and timers.

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
Confirm that header/footer shading is subtle and GTK labels/buttons stay sharp.
The GTK gate renders the window surface and every action button against the
bundled light/dark Orchis theme in normal, hover, pressed, keyboard-focus,
unfocused and disabled states. It checks that button corners and surrounding
pixels stay transparent while button fills remain opaque.
Check that a user-installed copy of an extension is not masking the RPM files.

Rebuild `infinity-updater` and `infinityos-shell-extensions` from the same commit
before publishing an image. Preserve the existing package build-revision markers.
