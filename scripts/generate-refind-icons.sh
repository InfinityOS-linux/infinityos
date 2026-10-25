#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
source_dir="$repo/assets/refind-icons"
output_dir="$repo/root/usr/share/infinityos/refind-theme/icons"

for name in infinityos infinityos-check infinityos-live infinityos-recovery infinityos-safe infinityos-esde infinityos-steam; do
    output="os_${name//-/_}.png"
    rsvg-convert -w 128 -h 128 "$source_dir/$name.svg" -o "$output_dir/$output"
done

for direction in left right; do
    rsvg-convert -w 48 -h 48 "$source_dir/arrow-$direction.svg" \
        -o "$output_dir/arrow_$direction.png"
done
