Name:           infinity-setup
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS welcome and application chooser
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinity-setup-%{version}.tar.gz
BuildArch:      noarch
Provides:       infinity-launcher = %{version}-%{release}
Obsoletes:      infinity-launcher < 1.0.1
Requires:       python3-gobject
Requires:       gtk4
Requires:       gdk-pixbuf2

%description
InfinitySetup offers first-login application choices for Infinity OS.

%prep
%setup -q

%build

%install
cp -a usr etc %{buildroot}/

%files
%license /usr/share/licenses/infinity-setup/COPYING
/usr/share/infinityos/build-revisions/infinity-setup
/usr/bin/infinity-setup
/usr/bin/infinity-local-ai
/usr/share/infinityos/launcher.py
/usr/share/infinityos/launcher_i18n.py
/usr/share/infinityos/launcher_backend.py
/usr/share/infinityos/launcher_tv.py
/usr/share/infinityos/launcher-icons/
/usr/share/infinityos/refind-theme/icons/os_infinityos_esde.png
/usr/share/infinityos/refind-theme/icons/os_infinityos_steam.png
/usr/libexec/infinityos-tv-control
/usr/libexec/infinityos-tv-run
/usr/libexec/infinityos-tv-return-desktop
/usr/libexec/infinityos-refind-config
/usr/libexec/infinityos-refind-install
/usr/lib/systemd/system-generators/infinityos-tv-mode-generator
/usr/lib/systemd/system/infinityos-tv@.service
/usr/lib/systemd/system/infinityos-tv@.target
/usr/share/polkit-1/actions/org.infinityos.tv-modes.policy
/usr/share/icons/hicolor/scalable/apps/infinity-*.svg
/usr/share/infinityos/launcher.desktop
/usr/share/infinityos/launcher-appid.desktop
/usr/share/infinityos/launcher-autostart.desktop
/usr/share/applications/infinity-setup.desktop
/usr/share/applications/org.infinityos.Setup.desktop
/usr/share/applications/infinity-launcher.desktop
/usr/share/applications/org.infinityos.Launcher.desktop
/etc/xdg/autostart/infinity-setup.desktop

%changelog
* Mon Oct 12 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Initial package
