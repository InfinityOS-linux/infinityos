#!/usr/bin/env bash
set -euo pipefail

package=${1:?Usage: packages/build-rpm.sh infinity-config|infinity-launcher|infinity-terminal|infinity-updater|infinityos-repos|infinityos-wallpapers|infinityos-ramdrive|infinityos-shell-extensions}
case "$package" in
  infinity-config) version=1.0.0 ;;
  infinity-launcher) version=1.0.0 ;;
  infinity-terminal) version=1.3.1 ;;
  infinity-updater) version=1.1.0 ;;
  infinityos-repos) version=1.0.0 ;;
  infinityos-wallpapers) version=1.1.0 ;;
  infinityos-ramdrive) version=1.1.0 ;;
  infinityos-shell-extensions) version=1.0.0 ;;
  *) echo "Unknown package: $package" >&2; exit 2 ;;
esac

repo=$(cd "$(dirname "$0")/.." && pwd)
revision=$("$repo/scripts/infinityos-source-revision" "$repo")
work=${INFINITY_PACKAGE_WORK_DIR:-"$repo/.build/rpm/$package"}
rm -rf "$work"
mkdir -p "$work/source/$package-$version" "$work/rpmbuild/SOURCES" "$work/rpmbuild/RPMS"
if [[ -d "$repo/packages/$package/root" ]]; then
  cp -a "$repo/packages/$package/root/." "$work/source/$package-$version/"
fi
install -d "$work/source/$package-$version/usr/share/infinityos/build-revisions"
printf '%s\n' "$revision" > "$work/source/$package-$version/usr/share/infinityos/build-revisions/$package"

if [[ "$package" == infinity-config ]]; then
  install -d "$work/source/$package-$version/usr/share/licenses/infinity-config"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinity-config/COPYING"
elif [[ "$package" == infinity-updater ]]; then
  install -d "$work/source/$package-$version/usr/share/licenses/infinity-updater"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinity-updater/COPYING"
elif [[ "$package" == infinityos-wallpapers ]]; then
  install -d "$work/source/$package-$version/usr/share/backgrounds/infinityos" \
    "$work/source/$package-$version/usr/share/gnome-background-properties" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-wallpapers" \
    "$work/source/$package-$version/etc/dconf/db/gdm.d"
  cp -a "$repo/root/usr/share/backgrounds/infinityos/." \
    "$work/source/$package-$version/usr/share/backgrounds/infinityos/"
  install -m 0644 "$repo/root/etc/dconf/db/gdm.d/00-infinityos" \
    "$work/source/$package-$version/etc/dconf/db/gdm.d/00-infinityos"
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
    "$repo/root/usr/libexec/infinityos-ramdrive-prepare" \
    "$work/source/$package-$version/usr/libexec/"
  install -m 0644 "$repo/root/usr/lib/systemd/system/infinityos-ramdrive.service" \
    "$repo/root/usr/lib/systemd/system/infinityos-ramdrive-prepare.service" \
    "$repo/root/usr/lib/systemd/system/infinityos-ramdrive-prepare.path" \
    "$work/source/$package-$version/usr/lib/systemd/system/"
  install -m 0644 "$repo/root/etc/xdg/autostart/infinityos-ramdrive.desktop" \
    "$repo/root/etc/xdg/autostart/infinityos-ramdrive-guard.desktop" \
    "$work/source/$package-$version/etc/xdg/autostart/"
  install -m 0644 "$repo/COPYING" \
    "$work/source/$package-$version/usr/share/licenses/infinityos-ramdrive/COPYING"
elif [[ "$package" == infinityos-shell-extensions ]]; then
  source_root="$work/source/$package-$version"
  fedora_snapshot="$repo/vendor/gnome-shell/fedora-44/usr/share"
  install -d "$source_root/usr/bin" \
    "$source_root/usr/share/gnome-shell/extensions" \
    "$source_root/usr/share/glib-2.0/schemas" \
    "$source_root/usr/share/infinityos" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions" \
    "$source_root/etc/dconf/db/local.d"
  cp -a "$fedora_snapshot/gnome-shell/extensions/." \
    "$source_root/usr/share/gnome-shell/extensions/"
  cp -a "$repo/root/usr/share/gnome-shell/extensions/." \
    "$source_root/usr/share/gnome-shell/extensions/"
  cp -a "$repo/root/usr/share/infinityos/folder-icons" \
    "$source_root/usr/share/infinityos/"
  install -m 0755 "$repo/root/usr/bin/infinityos-shell-recover" \
    "$source_root/usr/bin/infinityos-shell-recover"
  cp -a "$fedora_snapshot/glib-2.0/schemas/." \
    "$source_root/usr/share/glib-2.0/schemas/"
  install -m 0644 "$repo/root/usr/share/infinityos/gnome-defaults" \
    "$repo/root/usr/share/infinityos/blur-defaults" \
    "$source_root/usr/share/infinityos/"
  ln -s /usr/share/infinityos/gnome-defaults \
    "$source_root/etc/dconf/db/local.d/00-infinityos"
  ln -s /usr/share/infinityos/blur-defaults \
    "$source_root/etc/dconf/db/local.d/01-infinity-blur"
  licenses="$fedora_snapshot/licenses"
  install -m 0644 "$licenses/gpaste-libs/COPYING" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/GPaste-BSD-2-Clause"
  install -m 0644 "$licenses/gnome-shell-extension-appindicator/LICENSE" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/AppIndicator-GPL-2.0"
  install -m 0644 "$licenses/gnome-shell-extension-blur-my-shell/LICENSE" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/BlurMyShell-GPL-3.0"
  install -m 0644 "$licenses/gnome-shell-extension-caffeine/COPYING" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/Caffeine-GPL-2.0"
  install -m 0644 "$licenses/gnome-shell-extension-common/COPYING" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/UserTheme-GPL-2.0"
  install -m 0644 "$licenses/gnome-shell-extension-vertical-workspaces/LICENSE" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/VerticalWorkspaces-GPL-3.0"
  install -m 0644 "$repo/COPYING" \
    "$source_root/usr/share/licenses/infinityos-shell-extensions/InfinityOS-GPL-3.0"
elif [[ "$package" == infinity-launcher ]]; then
  install -d "$work/source/$package-$version/usr/bin" \
    "$work/source/$package-$version/usr/share/applications" \
    "$work/source/$package-$version/usr/share/icons/hicolor/scalable/apps" \
    "$work/source/$package-$version/usr/share/infinityos/refind-theme/icons" \
    "$work/source/$package-$version/usr/libexec" \
    "$work/source/$package-$version/usr/lib/systemd/system" \
    "$work/source/$package-$version/usr/lib/systemd/system-generators" \
    "$work/source/$package-$version/usr/share/polkit-1/actions" \
    "$work/source/$package-$version/etc/xdg/autostart" \
    "$work/source/$package-$version/usr/share/licenses/infinity-launcher"
  # App catalog artwork stays private so a future RPM can own its real icon.
  # Only Infinity OS icons used by desktop files or terminal tabs are global.
  install -m 0644 "$repo/packages/infinity-launcher/root/usr/share/infinityos/launcher-icons/"infinity-*.svg \
    "$work/source/$package-$version/usr/share/icons/hicolor/scalable/apps/"
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
  install -m 0755 "$repo/root/usr/libexec/infinityos-tv-control" \
    "$repo/root/usr/libexec/infinityos-tv-run" \
    "$repo/root/usr/libexec/infinityos-tv-return-desktop" \
    "$repo/root/usr/libexec/infinityos-refind-config" \
    "$repo/root/usr/libexec/infinityos-refind-install" \
    "$work/source/$package-$version/usr/libexec/"
  install -m 0755 "$repo/root/usr/lib/systemd/system-generators/infinityos-tv-mode-generator" \
    "$work/source/$package-$version/usr/lib/systemd/system-generators/"
  install -m 0644 "$repo/root/usr/lib/systemd/system/infinityos-tv@.service" \
    "$repo/root/usr/lib/systemd/system/infinityos-tv@.target" \
    "$work/source/$package-$version/usr/lib/systemd/system/"
  install -m 0644 "$repo/root/usr/share/infinityos/refind-theme/icons/os_infinityos_esde.png" \
    "$repo/root/usr/share/infinityos/refind-theme/icons/os_infinityos_steam.png" \
    "$work/source/$package-$version/usr/share/infinityos/refind-theme/icons/"
  install -m 0644 "$repo/root/usr/share/polkit-1/actions/org.infinityos.tv-modes.policy" \
    "$work/source/$package-$version/usr/share/polkit-1/actions/"
else
  if [[ -n ${INFINITY_GHOSTTY_INSTALL_DIR:-} ]]; then
    [[ -x "$INFINITY_GHOSTTY_INSTALL_DIR/usr/bin/ghostty" ]] || {
      echo 'INFINITY_GHOSTTY_INSTALL_DIR has no Ghostty binary' >&2; exit 2;
    }
    [[ -f "$INFINITY_GHOSTTY_INSTALL_DIR/usr/share/infinityos/ghostty-build-revision" ]] && \
      [[ $(<"$INFINITY_GHOSTTY_INSTALL_DIR/usr/share/infinityos/ghostty-build-revision") == "$revision" ]] || {
        echo 'Prebuilt Ghostty does not match this Infinity OS source revision' >&2; exit 2;
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
if [[ "$package" == infinityos-shell-extensions ]]; then
  # Build inside the container filesystem. Docker Desktop presents files on a
  # macOS bind mount as executable, which makes RPM's shebang check reject
  # upstream JavaScript modules that are data files rather than commands.
  docker run --rm ${INFINITY_TARGET_PLATFORM:+--platform "$INFINITY_TARGET_PLATFORM"} \
    -v "$work/rpmbuild/SOURCES:/source:ro" \
    -v "$work/rpmbuild/RPMS:/output" \
    -v "$repo/packages/$package/$package.spec:/build/$package.spec:ro" \
    fedora:44 sh -ec 'dnf -y --disablerepo=updates install rpm-build && \
      mkdir -p /build/rpmbuild/SOURCES && cp -a /source/. /build/rpmbuild/SOURCES/ && \
      rpmbuild -bb --define "_topdir /build/rpmbuild" \
        --define "infinity_release '${INFINITY_PACKAGE_RELEASE:-1}'" \
        "/build/'"$package"'.spec" && \
      cp -a /build/rpmbuild/RPMS/. /output/'
else
  docker run --rm ${INFINITY_TARGET_PLATFORM:+--platform "$INFINITY_TARGET_PLATFORM"} \
    -v "$work/rpmbuild:/build/rpmbuild" \
    -v "$repo/packages/$package/$package.spec:/build/$package.spec:ro" \
    fedora:44 sh -ec 'dnf -y --disablerepo=updates install rpm-build && rpmbuild -bb \
      --define "_topdir /build/rpmbuild" \
      --define "infinity_release '${INFINITY_PACKAGE_RELEASE:-1}'" \
      "/build/'"$package"'.spec"'
fi

mkdir -p "$repo/.build/rpm-output"
find "$work/rpmbuild/RPMS" -name '*.rpm' -exec cp -f {} "$repo/.build/rpm-output/" \;
