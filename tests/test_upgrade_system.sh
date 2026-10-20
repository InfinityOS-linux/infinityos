#!/usr/bin/env bash
# Run in a disposable Fedora container as root; never on an installed system.
set -euo pipefail
[[ -f /.dockerenv && $EUID -eq 0 ]] || { echo 'Container root required' >&2; exit 2; }

script=/work/packages/infinity-updater/root/usr/libexec/infinityos-upgrade-system
fake=$(mktemp -d)
trap 'rm -rf "$fake"' EXIT
mkdir -p "$fake/bin" /etc/snapper/configs /.snapshots
touch /etc/snapper/configs/root
printf '#!/bin/sh\necho btrfs\n' > "$fake/bin/findmnt"
printf '#!/bin/sh\nexit 0\n' > "$fake/bin/mountpoint"
printf '#!/bin/sh\necho snapper >> "$TEST_LOG"\nif [ "${SNAPPER_FAIL:-0}" = 1 ]; then exit 1; fi\necho 17\n' > "$fake/bin/snapper"
printf '#!/bin/sh\necho dnf >> "$TEST_LOG"\n' > "$fake/bin/dnf"
chmod +x "$fake/bin/"*
export PATH="$fake/bin:$PATH" TEST_LOG="$fake/log"

"$script" > "$fake/output"
[[ $(cat "$fake/log") == $'snapper\ndnf' ]]
grep -Fq 'root snapshot #17 created' "$fake/output"

: > "$fake/log"
if SNAPPER_FAIL=1 "$script" > "$fake/output" 2>&1; then
    echo 'An RPM upgrade ran despite snapshot failure' >&2
    exit 1
fi
[[ $(cat "$fake/log") == snapper ]]
grep -Fq 'could not create the pre-update snapshot' "$fake/output"
echo 'Updater snapshot gate: OK'
