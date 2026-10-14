Name:           infinity-updater
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS update indicator and package updater
License:        GPL-3.0-or-later
URL:            https://gitlab.com/godorowski/infinityos
Source0:        infinity-updater-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       gtk4
Requires:       dnf5
Requires:       flatpak
Requires:       polkit
Obsoletes:      gnome-software

%description
Checks Fedora, Infinity OS, and Flatpak updates daily and provides an
Infinity OS styled update window from the GNOME top panel.

%prep
%setup -q

%build

%install
cp -a usr %{buildroot}/

%post
systemctl enable --now infinityos-bazaar-install.timer >/dev/null 2>&1 || :
systemctl --global enable infinity-updater.timer >/dev/null 2>&1 || :

%files
%license /usr/share/licenses/infinity-updater/COPYING
/usr/bin/infinity-updater
/usr/share/infinityos/updater/
/usr/share/applications/org.infinityos.Updater.desktop
/usr/share/icons/hicolor/scalable/apps/org.infinityos.Updater.svg
/usr/share/icons/hicolor/scalable/status/infinity-update-available-symbolic.svg
/usr/share/gnome-shell/extensions/infinity-updater@infinityos.org/
/usr/lib/systemd/user/infinity-updater.service
/usr/lib/systemd/user/infinity-updater.timer
/usr/lib/systemd/system/infinityos-bazaar-install.service
/usr/lib/systemd/system/infinityos-bazaar-install.timer
/usr/libexec/infinityos-install-bazaar

%changelog
* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Initial daily update indicator and Bazaar installer
