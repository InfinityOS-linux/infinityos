#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
sandbox=$(mktemp -d)
cleanup() {
    if mountpoint -q "$sandbox/run/doc"; then umount -l "$sandbox/run/doc" 2>/dev/null || true; fi
    rm -rf "$sandbox"
}
trap cleanup EXIT
export XDG_DATA_HOME="$sandbox/data" XDG_CONFIG_HOME="$sandbox/config" XDG_CACHE_HOME="$sandbox/cache"
export XDG_RUNTIME_DIR="$sandbox/run" LIBGL_ALWAYS_SOFTWARE=1
mkdir -p "$XDG_DATA_HOME/gnome-shell/extensions" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
for uuid in nowplay@LalaloyXyz raccoonlauncher@shimafallah.github.io dash2dock-animated@infinityos.org; do
    cp -a "$repo/root/usr/share/gnome-shell/extensions/$uuid" "$XDG_DATA_HOME/gnome-shell/extensions/"
done
for package in infinity-terminal infinity-updater; do
    cp -a "$repo/packages/$package/root/usr/share/gnome-shell/extensions/." "$XDG_DATA_HOME/gnome-shell/extensions/"
done
cp -a "$repo/tests/shell-smoke" "$XDG_DATA_HOME/gnome-shell/extensions/infinity-smoke@test"
for schemas in "$XDG_DATA_HOME"/gnome-shell/extensions/*/schemas; do glib-compile-schemas --strict "$schemas"; done
cmp "$repo/root/usr/share/gnome-shell/extensions/nowplay@LalaloyXyz/ui.js" "$XDG_DATA_HOME/gnome-shell/extensions/nowplay@LalaloyXyz/ui.js"
sha256sum "$XDG_DATA_HOME/gnome-shell/extensions/nowplay@LalaloyXyz/ui.js"
if grep -n 'const animateUp' "$XDG_DATA_HOME/gnome-shell/extensions/nowplay@LalaloyXyz/ui.js"; then
    echo 'Obsolete recursive equalizer implementation'; exit 1
fi
export SMOKE_LOG="$sandbox/shell.log"
dbus-run-session -- bash -euo pipefail -c '
    gsettings set org.gnome.shell disable-user-extensions false
    gsettings set org.gnome.shell enabled-extensions "[\"infinity-smoke@test\"]"
    gnome-shell --headless --virtual-monitor 1280x800 >"$SMOKE_LOG" 2>&1 &
    shell_pid=$!
    trap '\''kill "$shell_pid" 2>/dev/null || true'\'' EXIT
    for attempt in $(seq 1 90); do
        if grep -q INFINITY_SMOKE_PASS "$SMOKE_LOG"; then
            if grep -q "JS ERROR" "$SMOKE_LOG"; then cat "$SMOKE_LOG"; exit 1; fi
            exit 0
        fi
        if grep -q INFINITY_SMOKE_FAIL "$SMOKE_LOG" || ! kill -0 "$shell_pid" 2>/dev/null; then cat "$SMOKE_LOG"; exit 1; fi
        sleep 1
    done
    cat "$SMOKE_LOG"; exit 1
'
cat "$SMOKE_LOG"
