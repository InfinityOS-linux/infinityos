Name:           infinity-launcher
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS welcome and application chooser
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinity-launcher-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       gtk4

%description
InfinityLauncher offers first-login application choices for Infinity OS.

%prep
%setup -q

%build

%install
cp -a usr etc %{buildroot}/

%files
%license /usr/share/licenses/infinity-launcher/COPYING
/usr/share/infinityos/build-revisions/infinity-launcher
/usr/bin/infinity-launcher
/usr/bin/infinity-local-ai
/usr/share/infinityos/launcher.py
/usr/share/infinityos/launcher_i18n.py
/usr/share/infinityos/launcher_backend.py
/usr/share/infinityos/launcher-icons/
/usr/share/icons/hicolor/128x128/apps/*.png
/usr/share/icons/hicolor/scalable/apps/*.svg
/usr/share/infinityos/launcher.desktop
/usr/share/infinityos/launcher-appid.desktop
/usr/share/infinityos/launcher-autostart.desktop
/usr/share/applications/infinity-launcher.desktop
/usr/share/applications/org.infinityos.Launcher.desktop
/etc/xdg/autostart/infinity-launcher.desktop

%changelog
* Mon Oct 12 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Initial package
