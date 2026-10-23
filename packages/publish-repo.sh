#!/usr/bin/env bash
set -euo pipefail

rpms=${1:?Pass the directory containing built RPMs}
public=${2:?Pass the static repository output directory}
repo=$(cd "$(dirname "$0")/.." && pwd)
readarray -t release < <(python3 - "$repo/releases/stable.json" <<'PY'
import json
import re
import sys
data = json.load(open(sys.argv[1], encoding='utf-8'))
version = data['version']
fedora = data['fedora_release']
if not re.fullmatch(r'[1-9][0-9]*\.[0-9]+(?:\.[0-9]+)?', version) or type(fedora) is not int or fedora != 44:
    raise SystemExit('Invalid Infinity OS release metadata')
print(version)
print(fedora)
PY
)
[[ ${#release[@]} -eq 2 ]] || { echo 'Invalid release metadata' >&2; exit 1; }
version=${release[0]}
fedora=${release[1]}
fingerprint=0CEBC6680F0EF50BD376CBB034715734803514AC
rpm --import "$repo/root/etc/pki/rpm-gpg/RPM-GPG-KEY-infinityos"

for arch in aarch64 x86_64; do
  dir="$public/rpm/$fedora/releases/$version/$arch"
  mkdir -p "$dir"
  for required in infinity-config infinity-setup infinity-updater infinityos-repos infinityos-wallpapers infinityos-ramdrive infinityos-shell-extensions infinity-terminal; do
    compgen -G "$rpms/$required-*.noarch.rpm" >/dev/null || \
      compgen -G "$rpms/$required-*.$arch.rpm" >/dev/null || {
        echo "Missing $required RPM for $arch" >&2; exit 1;
      }
  done
  for rpmfile in "$rpms"/*.rpm; do
    [[ -f "$rpmfile" ]] || continue
    rpmarch=$(rpm -qp --qf '%{ARCH}' "$rpmfile")
    if [[ "$rpmarch" == noarch || "$rpmarch" == "$arch" ]]; then
      cp "$rpmfile" "$dir/"
    fi
  done
  for rpmfile in "$dir"/*.rpm; do
    rpmsign --addsign --define "_gpg_name $fingerprint" "$rpmfile"
    rpm --checksig "$rpmfile" | grep -q 'digests signatures OK'
  done
  createrepo_c "$dir"
  gpg --batch --yes --armor --detach-sign -o "$dir/repodata/repomd.xml.asc" \
    "$dir/repodata/repomd.xml"
  gpg --batch --verify "$dir/repodata/repomd.xml.asc" "$dir/repodata/repomd.xml"
  if [[ $version == 1.0 ]]; then
    mkdir -p "$public/rpm/$fedora/$arch"
    cp -a "$dir/." "$public/rpm/$fedora/$arch/"
  fi
done

install -d "$public/releases"
install -m 0644 "$repo/releases/stable.json" "$public/releases/stable.json"
gpg --batch --yes --armor --detach-sign -o "$public/releases/stable.json.asc" \
  "$public/releases/stable.json"
gpg --batch --verify "$public/releases/stable.json.asc" "$public/releases/stable.json"
cp "$repo/root/etc/pki/rpm-gpg/RPM-GPG-KEY-infinityos" "$public/RPM-GPG-KEY-infinityos"
printf 'Infinity OS RPM repository\n' > "$public/index.html"
