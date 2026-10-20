Name:           infinity-updater
Version:        1.1.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS update indicator and package updater
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinity-updater-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       gtk4
Requires:       dnf5
Requires:       flatpak
Requires:       fwupd
Requires:       polkit
Requires:       snapper
Requires:       gnupg2
Requires:       infinityos-repos >= 1.0.0
Requires:       infinityos-shell-extensions >= 1.0.0

%description
Checks Fedora, Infinity OS, Flatpak, and device firmware updates periodically and provides an
Infinity OS styled update window from the GNOME top panel.

%prep
%setup -q

%build

%install
cp -a usr %{buildroot}/

%post
# Previous releases enabled a one-shot Bazaar installer. Stop it during RPM upgrades.
systemctl disable --now infinityos-bazaar-install.timer >/dev/null 2>&1 || :
systemctl --global enable infinity-updater.timer >/dev/null 2>&1 || :

%files
%license /usr/share/licenses/infinity-updater/COPYING
/usr/share/infinityos/build-revisions/infinity-updater
/usr/bin/infinity-updater
/usr/libexec/infinityos-upgrade-system
/usr/libexec/infinityos-upgrade-release
/usr/share/infinityos/updater/
/usr/share/applications/org.infinityos.Updater.desktop
/usr/share/icons/hicolor/scalable/apps/org.infinityos.Updater.svg
/usr/share/icons/hicolor/scalable/status/infinity-update-available-symbolic.svg
/usr/share/gnome-shell/extensions/infinity-updater@infinityos.org/
/usr/lib/systemd/user/infinity-updater.service
/usr/lib/systemd/user/infinity-updater.timer

%changelog
* Tue Oct 20 2026 Infinity OS Contributors <noreply@infinityos.eu> - 1.1.0-1
- Detect signed Infinity OS releases and upgrade after current RPMs are installed

* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Initial daily update indicator
