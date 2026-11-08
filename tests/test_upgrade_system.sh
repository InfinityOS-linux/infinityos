#!/usr/bin/env bash
# Run in a disposable Fedora container as root; never on an installed system.
set -euo pipefail
[[ -f /.dockerenv && $EUID -eq 0 ]] || { echo 'Container root required' >&2; exit 2; }

script="$(cd "$(dirname "$0")/.." && pwd)"/packages/infinity-updater/root/usr/libexec/infinityos-upgrade-system
fake=$(mktemp -d)
trap 'rm -rf "$fake"' EXIT
mkdir -p "$fake/bin" /etc/snapper/configs /.snapshots
touch /etc/snapper/configs/root
printf '#!/bin/sh\necho btrfs\n' > "$fake/bin/findmnt"
printf '#!/bin/sh\nexit 0\n' > "$fake/bin/mountpoint"
printf '#!/bin/sh\necho "dnf $*" >> "$TEST_LOG"\nif [ "${DNF_FAIL:-0}" = 1 ]; then exit 1; fi\n' > "$fake/bin/dnf"
chmod +x "$fake/bin/"*
export PATH="$fake/bin:$PATH" TEST_LOG="$fake/log"

"$script" > "$fake/output"
grep -Fq 'dnf -y upgrade --offline' "$fake/log"
grep -Fq 'dnf -y offline reboot' "$fake/log"
grep -Fq 'System update prepared' "$fake/output"

: > "$fake/log"
if DNF_FAIL=1 "$script" > "$fake/output" 2>&1; then
    echo 'An unsuccessful download was marked ready' >&2
    exit 1
fi
[[ $(wc -l < "$fake/log") -eq 1 ]]
echo 'Updater offline preparation gate: OK'
