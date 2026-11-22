#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
output="$repo/.build/rpm-output"
mkdir -p "$output"

docker run --rm \
  -e INFINITY_PACKAGE_RELEASE="${INFINITY_PACKAGE_RELEASE:-1}" \
  -v "$repo/packages/nautilus:/source:ro" \
  -v "$output:/output" \
  fedora:45 bash -euo pipefail -c '
    dnf -qy install dnf5-plugins fedora-gpg-keys rpm-build patch
    rpmkeys --import /usr/share/pki/rpm-gpg/RPM-GPG-KEY-fedora-45-primary
    mkdir -p /build/rpmbuild/SOURCES
    dnf -qy download --srpm --destdir=/build nautilus
    shopt -s nullglob
    sources=(/build/nautilus-51.*.src.rpm)
    [[ ${#sources[@]} -eq 1 ]]
    rpmkeys --checksig "${sources[0]}" | grep -q "digests signatures OK"
    release=$(rpm -qp --qf "%{RELEASE}" "${sources[0]}")
    [[ "$release" =~ ^[[:alnum:].]+$ && "$INFINITY_PACKAGE_RELEASE" =~ ^[0-9]+$ ]]
    rpm -i --define "_topdir /build/rpmbuild" "${sources[0]}"
    spec=/build/rpmbuild/SPECS/nautilus.spec
    cp /source/sidebar-automount.patch /build/rpmbuild/SOURCES/
    grep -Eq "^%autosetup([[:space:]]|$)" "$spec"
    sed -i -e "/^Release:/cRelease: ${release}.infinityos.${INFINITY_PACKAGE_RELEASE}\nSource900: sidebar-automount.patch" \
      -e "/^%autosetup/a patch --fuzz=0 -p1 < %{SOURCE900}" "$spec"
    dnf -qy builddep "$spec"
    rpmbuild -bb --define "_topdir /build/rpmbuild" "$spec"
    arch=$(uname -m)
    apps=(/build/rpmbuild/RPMS/"$arch"/nautilus-51.*.rpm)
    extensions=(/build/rpmbuild/RPMS/"$arch"/nautilus-extensions-51.*.rpm)
    [[ ${#apps[@]} -eq 1 && ${#extensions[@]} -eq 1 ]]
    rpm -qpl "${apps[0]}" | grep -Fx /usr/bin/nautilus
    cp "${apps[@]}" "${extensions[@]}" /build/rpmbuild/RPMS/"$arch"/nautilus-devel-51.*.rpm /output/
    chmod 644 /output/nautilus-*."$arch".rpm
  '
