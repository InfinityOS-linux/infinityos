#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
work=${INFINITY_GAMESCOPE_WORK_DIR:-"$repo/.build/rpm/gamescope"}
rm -rf "$work"
mkdir -p "$work/RPMS"

docker run --rm --platform linux/amd64 \
  -v "$repo/packages/gamescope:/source:ro" \
  -v "$work/RPMS:/output" \
  fedora:45 bash -euo pipefail -c '
    dnf -y install curl dnf5-plugins rpm-build
    mkdir -p /build/rpmbuild/SOURCES
    cp /source/*.patch /source/stb.pc /build/rpmbuild/SOURCES/
    while read -r checksum filename; do
      curl -fL --retry 3 \
        "https://src.fedoraproject.org/repo/pkgs/gamescope/$filename/sha512/$checksum/$filename" \
        -o "/build/rpmbuild/SOURCES/$filename"
      printf "%s  %s\n" "$checksum" "/build/rpmbuild/SOURCES/$filename" | sha512sum -c -
    done < <(sed -n "s/^SHA512 (\([^)]*\)) = \([0-9a-f]*\)$/\2 \1/p" /source/sources)
    dnf -y builddep /source/gamescope.spec
    rpmbuild -bb --define "_topdir /build/rpmbuild" /source/gamescope.spec
    rpmfile=(/build/rpmbuild/RPMS/x86_64/gamescope-3.16.29-*.x86_64.rpm)
    [[ ${#rpmfile[@]} -eq 1 ]]
    [[ $(rpm -qp --qf "%{NAME} %{VERSION}-%{RELEASE} %{ARCH}" "${rpmfile[0]}") == "gamescope 3.16.29-2.infinityos.fc45 x86_64" ]]
    rpm_files=$(rpm -qpl "${rpmfile[0]}")
    grep -qx /usr/bin/gamescope <<< "$rpm_files"
    cp -a "${rpmfile[0]}" /output/
  '

mkdir -p "$repo/.build/rpm-output"
find "$work/RPMS" -name '*.rpm' -exec cp -f {} "$repo/.build/rpm-output/" \;
