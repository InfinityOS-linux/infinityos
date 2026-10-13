#!/usr/bin/env bash
set -euo pipefail

package=${1:?Usage: packages/build-rpm.sh infinity-launcher|infinity-terminal|infinityos-repos|infinityos-wallpapers|infinityos-ramdrive}
case "$package" in
  infinity-launcher) version=1.0.0 ;;
  infinity-terminal) version=1.3.1 ;;
  infinityos-repos) version=1.0.0 ;;
  infinityos-wallpapers) version=1.0.0 ;;
  infinityos-ramdrive) version=1.0.0 ;;
  *) echo "Unknown package: $package" >&2; exit 2 ;;
esac

repo=$(cd "$(dirname "$0")/.." && pwd)
work=${INFINITY_PACKAGE_WORK_DIR:-"$repo/.build/rpm/$package"}
rm -rf "$work"
mkdir -p "$work/source/$package-$version" "$work/rpmbuild/SOURCES" "$work/rpmbuild/RPMS"
if [[ -d "$repo/packages/$package/root" ]]; then
  cp -a "$repo/packages/$package/root/." "$work/source/$package-$version/"
fi

if [[ "$package" == infinityos-wallpapers ]]; then
  install -d "$work/source/$package-$version/usr/share/backgrounds/infinityos" \
    "$work/source/$package-$version/usr/share/gnome-background-properties" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-wallpapers"
  cp -a "$repo/root/usr/share/backgrounds/infinityos/." \
    "$work/source/$package-$version/usr/share/backgrounds/infinityos/"
  install -m 0644 "$repo/root/usr/share/infinityos/background-catalog.xml" \
    "$work/source/$package-$version/usr/share/gnome-background-properties/00-infinityos.xml"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-wallpapers/COPYING"
elif [[ "$package" == infinityos-repos ]]; then
  install -d "$work/source/$package-$version/etc/yum.repos.d" \
    "$work/source/$package-$version/etc/pki/rpm-gpg" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-repos"
  install -m 0644 "$repo/root/usr/share/infinityos/repos/infinityos.repo" \
    "$work/source/$package-$version/etc/yum.repos.d/infinityos.repo"
  install -m 0644 "$repo/root/etc/pki/rpm-gpg/RPM-GPG-KEY-infinityos" \
    "$work/source/$package-$version/etc/pki/rpm-gpg/RPM-GPG-KEY-infinityos"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-repos/COPYING"
elif [[ "$package" == infinityos-ramdrive ]]; then
  install -d "$work/source/$package-$version/usr/libexec" \
    "$work/source/$package-$version/usr/lib/systemd/system" \
    "$work/source/$package-$version/etc/xdg/autostart" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-ramdrive"
  install -m 0755 "$repo/root/usr/libexec/infinityos-ramdrive" \
    "$repo/root/usr/libexec/infinityos-ramdrive-shutdown" \
    "$repo/root/usr/libexec/infinityos-ramdrive-guard" \
    "$work/source/$package-$version/usr/libexec/"
  install -m 0644 "$repo/root/usr/lib/systemd/system/infinityos-ramdrive.service" \
    "$work/source/$package-$version/usr/lib/systemd/system/"
  install -m 0644 "$repo/root/etc/xdg/autostart/infinityos-ramdrive.desktop" \
    "$repo/root/etc/xdg/autostart/infinityos-ramdrive-guard.desktop" \
    "$work/source/$package-$version/etc/xdg/autostart/"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-ramdrive/COPYING"
elif [[ "$package" == infinity-launcher ]]; then
  install -d "$work/source/$package-$version/usr/bin" \
    "$work/source/$package-$version/usr/share/applications" \
    "$work/source/$package-$version/etc/xdg/autostart" \
    "$work/source/$package-$version/usr/share/licenses/infinity-launcher"
  install -m 0755 "$repo/packages/infinity-launcher/root/usr/bin/infinity-launcher" \
    "$work/source/$package-$version/usr/bin/infinity-launcher"
  install -m 0644 "$repo/packages/infinity-launcher/root/usr/share/infinityos/launcher.desktop" \
    "$work/source/$package-$version/usr/share/applications/infinity-launcher.desktop"
  install -m 0644 "$repo/packages/infinity-launcher/root/usr/share/infinityos/launcher-appid.desktop" \
    "$work/source/$package-$version/usr/share/applications/org.infinityos.Launcher.desktop"
  install -m 0644 "$repo/packages/infinity-launcher/root/usr/share/infinityos/launcher-autostart.desktop" \
    "$work/source/$package-$version/etc/xdg/autostart/infinity-launcher.desktop"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinity-launcher/COPYING"
else
  if [[ -n ${INFINITY_GHOSTTY_INSTALL_DIR:-} ]]; then
    [[ -x "$INFINITY_GHOSTTY_INSTALL_DIR/usr/bin/ghostty" ]] || {
      echo 'INFINITY_GHOSTTY_INSTALL_DIR has no Ghostty binary' >&2; exit 2;
    }
    install -d "$work/source/$package-$version/usr/libexec/infinityos" \
      "$work/source/$package-$version/usr/share"
    install -m 0755 "$INFINITY_GHOSTTY_INSTALL_DIR/usr/bin/ghostty" \
      "$work/source/$package-$version/usr/libexec/infinityos/ghostty"
    cp -a "$INFINITY_GHOSTTY_INSTALL_DIR/usr/share/ghostty" \
      "$work/source/$package-$version/usr/share/ghostty"
    cp -a "$INFINITY_GHOSTTY_INSTALL_DIR/usr/share/terminfo" \
      "$work/source/$package-$version/usr/share/terminfo"
  else
    INFINITY_GHOSTTY_WORK_DIR="$work/ghostty" \
      "$repo/ghostty/build-and-stage.sh" "$work/source/$package-$version"
  fi
  install -m 0755 "$repo/packages/infinity-terminal/root/usr/bin/infinity-terminal" \
    "$work/source/$package-$version/usr/bin/infinity-terminal"
  ln -s infinity-terminal "$work/source/$package-$version/usr/bin/ghostty"
  install -d "$work/source/$package-$version/usr/share/licenses/infinity-terminal"
  install -m 0644 "$repo/ghostty/GHOSTTY-LICENSE" \
    "$work/source/$package-$version/usr/share/licenses/infinity-terminal/GHOSTTY-LICENSE"
  tar -xOf "$repo/root/usr/share/infinityos/kora-v2.0.6.tar.gz" kora-2.0.6/LICENSE \
    > "$work/source/$package-$version/usr/share/licenses/infinity-terminal/KORA-LICENSE"
fi

COPYFILE_DISABLE=1 tar -czf "$work/rpmbuild/SOURCES/$package-$version.tar.gz" -C "$work/source" "$package-$version"
docker run --rm ${INFINITY_TARGET_PLATFORM:+--platform "$INFINITY_TARGET_PLATFORM"} \
  -v "$work/rpmbuild:/build/rpmbuild" \
  -v "$repo/packages/$package/$package.spec:/build/$package.spec:ro" \
  fedora:44 sh -ec 'dnf -y --disablerepo=updates install rpm-build && rpmbuild -bb \
    --define "_topdir /build/rpmbuild" \
    --define "infinity_release '${INFINITY_PACKAGE_RELEASE:-1}'" \
    "/build/'"$package"'.spec"'

mkdir -p "$repo/.build/rpm-output"
find "$work/rpmbuild/RPMS" -name '*.rpm' -exec cp -f {} "$repo/.build/rpm-output/" \;
