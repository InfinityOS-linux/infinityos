#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
sandbox=$(mktemp -d)
cleanup() {
    if mountpoint -q "$sandbox/run/doc"; then umount -l "$sandbox/run/doc" 2>/dev/null || true; fi
    # D-Bus activated services can finish writing after the bus exits.
    # Retry briefly instead of letting this teardown race fail a passing test.
    for attempt in $(seq 1 10); do
        if rm -rf "$sandbox" 2>/dev/null; then return 0; fi
        sleep 0.5
    done
    rm -rf "$sandbox"
}
trap cleanup EXIT
export XDG_DATA_HOME="$sandbox/data" XDG_CONFIG_HOME="$sandbox/config" XDG_CACHE_HOME="$sandbox/cache"
export XDG_DATA_DIRS="$sandbox/system:/usr/local/share:/usr/share"
export XCURSOR_PATH="$sandbox/system/icons:/usr/share/icons"
export SMOKE_EXTENSIONS="$sandbox/system/gnome-shell/extensions"
export XDG_RUNTIME_DIR="$sandbox/run" LIBGL_ALWAYS_SOFTWARE=1
mkdir -p "$SMOKE_EXTENSIONS" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
mkdir -p "$sandbox/system/icons"
cp -a "$repo/root/usr/share/icons/InfinityOS-Modern-Ice" "$sandbox/system/icons/"
# Force the GNOME 51 provider: this disposable copy cannot fall back to our
# legacy wait bitmap. Source tests separately load every Xcursor size/frame.
rm "$sandbox/system/icons/InfinityOS-Modern-Ice/cursors/wait"
chmod 700 "$XDG_RUNTIME_DIR"
for uuid in globalmenu@ShiroOSL.github.io media-controller@naimur raccoonlauncher@shimafallah.github.io dash2dock-animated@infinityos.org wack-shell@rinzler69-wastaken.github.com; do
    cp -a "$repo/root/usr/share/gnome-shell/extensions/$uuid" "$SMOKE_EXTENSIONS/"
done
for package in infinity-terminal infinity-updater; do
    cp -a "$repo/packages/$package/root/usr/share/gnome-shell/extensions/." "$SMOKE_EXTENSIONS/"
done
cp "$SMOKE_EXTENSIONS/infinity-updater@infinityos.org/panel-backdrop.js" "$SMOKE_EXTENSIONS/ghostty@infinityos.org/"
cp -a "$repo/vendor/gnome-shell/fedora-45/usr/share/gnome-shell/extensions/blur-my-shell@aunetx" "$SMOKE_EXTENSIONS/"
cp -a "$repo/tests/shell-smoke" "$SMOKE_EXTENSIONS/infinity-smoke@test"
for schemas in "$SMOKE_EXTENSIONS"/*/schemas; do glib-compile-schemas --strict "$schemas"; done
export SMOKE_LOG="$sandbox/shell.log"
# The persistent terminal binary is not installed in this disposable Shell.
# Keep its desktop ID while using an available inert executable for AppInfo.
mkdir -p "$sandbox/system/applications"
sed 's|^Exec=.*|Exec=/usr/bin/true|' \
    "$repo/packages/infinity-terminal/root/usr/share/applications/com.infinityos.GhosTTY.desktop" \
    > "$sandbox/system/applications/com.infinityos.GhosTTY.desktop"
export INFINITY_SMOKE_TERMINAL_DESKTOP="$sandbox/system/applications/com.infinityos.GhosTTY.desktop"
export INFINITY_SMOKE_UPDATER="$repo/packages/infinity-updater/root/usr/share/infinityos/updater/updater.py"
export INFINITY_SMOKE_APP_BACKDROP="$repo/packages/infinity-updater/root/usr/share/infinityos/panel_backdrop.py"
export INFINITY_SMOKE_BACKDROP_REPORT="$sandbox/updater-backdrop.json"
export INFINITY_SMOKE_CURSOR_REPORT="$sandbox/cursor-client.json"
export INFINITY_SMOKE_GTK_THEME="$repo/root/usr/share/themes/Orchis-Purple-Dark-Compact/gtk-4.0/gtk.css"
dbus-run-session -- bash -euo pipefail -c '
    dconf load / < "$INFINITY_SMOKE_BLUR_DEFAULTS"
    # Test vendored code, never replace it with extensions.gnome.org downloads.
    gsettings set org.gnome.shell allow-extension-installation false
    gsettings set org.gnome.shell disable-user-extensions false
    gsettings set org.gnome.desktop.interface cursor-theme InfinityOS-Modern-Ice
    gsettings set org.gnome.desktop.interface cursor-size 32
    gsettings set org.gnome.shell enabled-extensions "[\"infinity-smoke@test\"]"
    gnome-shell --headless --virtual-monitor 1280x800 >"$SMOKE_LOG" 2>&1 &
    shell_pid=$!
    trap '\''kill "$shell_pid" 2>/dev/null || true; wait "$shell_pid" 2>/dev/null || true'\'' EXIT
    for attempt in $(seq 1 150); do
        if grep -q INFINITY_SMOKE_PASS "$SMOKE_LOG"; then
            if grep -q "JS ERROR" "$SMOKE_LOG"; then cat "$SMOKE_LOG"; exit 1; fi
            for mode in DARK LIGHT; do
                log="$XDG_RUNTIME_DIR/ding-$mode.log"
                WAYLAND_DISPLAY=wayland-0 GDK_BACKEND=wayland WAYLAND_DEBUG=client gjs -m "$INFINITY_DING_TEST" "$INFINITY_DING_CSS" "$mode" 2>"$log" || { tail -80 "$log"; exit 1; }
                if ! grep -Eq "set_blur_region\(wl_region[#@]" "$log"; then
                    grep -E "background_effect|xdg_popup|Gjs-" "$log" | tail -60 || true
                    echo "Desktop menu did not request compositor blur in $mode mode"; exit 1
                fi
            done
            exit 0
        fi
        if grep -q INFINITY_SMOKE_FAIL "$SMOKE_LOG" || ! kill -0 "$shell_pid" 2>/dev/null; then cat "$SMOKE_LOG"; exit 1; fi
        sleep 1
    done
    cat "$SMOKE_LOG"; exit 1
'
cat "$SMOKE_LOG"
