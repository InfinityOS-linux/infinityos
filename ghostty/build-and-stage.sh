#!/usr/bin/env bash
set -euo pipefail

description=${1:?Pass the prepared KIWI description directory}
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${INFINITY_GHOSTTY_WORK_DIR:-"$repo/../build/ghostty"}
mkdir -p "$work/source" "$work/install"
archive="$work/ghostty-1.3.1.tar.gz"
if [[ ! -f "$archive" ]]; then
	curl -fL --retry 3 'https://release.files.ghostty.org/1.3.1/ghostty-1.3.1.tar.gz' -o "$archive"
fi
python3 - "$archive" <<'PY'
import hashlib, pathlib, sys
actual = hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()
assert actual == '3349d25600ffbda281197a18314f7d18791969cffe9474f0ff16a45a9ebfccdb', actual
PY

rm -rf "$work/source/ghostty-1.3.1" "$work/install/usr"
tar -xzf "$archive" -C "$work/source"
patch -d "$work/source/ghostty-1.3.1" -p1 < "$repo/ghostty/ghostty-1.3.1-infinity.patch"
rm -f "$work/source/ghostty-1.3.1/src/apprt/gtk/ghostty_resources.c" \
	"$work/source/ghostty-1.3.1/src/apprt/gtk/ghostty_resources.h"

builder=${INFINITY_GHOSTTY_BUILDER_IMAGE:-infinityos-ghostty-builder:f44}
platform_args=()
if [[ -n ${INFINITY_TARGET_PLATFORM:-} ]]; then
	platform_args=(--platform "$INFINITY_TARGET_PLATFORM")
fi
if [[ -z ${INFINITY_GHOSTTY_BUILDER_IMAGE:-} ]]; then
	docker build ${platform_args[@]+"${platform_args[@]}"} -t "$builder" -f "$repo/ghostty/Dockerfile" "$repo/ghostty"
fi
docker run --rm ${platform_args[@]+"${platform_args[@]}"} \
	-v "$work/source/ghostty-1.3.1:/src" \
	-v "$work/install:/out" \
	-v infinityos-zig-cache:/root/.cache/zig \
	-w /src "$builder" \
	bash -lc 'DESTDIR=/out zig build --prefix /usr -Doptimize=ReleaseFast -Dcpu=baseline'

target="$description/root/usr"
install -d "$target/libexec/infinityos" "$target/share"
install -m 0755 "$work/install/usr/bin/ghostty" "$target/libexec/infinityos/ghostty"
cp -a "$work/install/usr/share/ghostty" "$target/share/ghostty"
if [[ -d "$work/install/usr/share/terminfo" ]]; then
	cp -a "$work/install/usr/share/terminfo" "$target/share/terminfo"
fi
printf 'Staged GhosTTY from Ghostty 1.3.1 for %s\n' "$(docker run --rm ${platform_args[@]+"${platform_args[@]}"} "$builder" uname -m)"
