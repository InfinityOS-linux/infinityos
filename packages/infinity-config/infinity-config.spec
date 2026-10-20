Name:           infinity-config
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS desktop configuration
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinity-config-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       gtk4
Requires:       gsettings-desktop-schemas
Requires:       gnome-extensions-app
Requires:       gnome-control-center
Requires:       infinity-updater
Requires:       infinityos-shell-extensions

%description
Infinity Config adjusts Infinity OS desktop and dock settings.

%prep
%setup -q

%build

%install
cp -a usr %{buildroot}/

%files
%license /usr/share/licenses/infinity-config/COPYING
/usr/share/infinityos/build-revisions/infinity-config
/usr/bin/infinity-config
/usr/share/infinityos/config.py
/usr/share/infinityos/config_backend.py
/usr/share/infinityos/diagnostics.py
/usr/share/applications/org.infinityos.Config.desktop
/usr/share/icons/hicolor/scalable/apps/infinity-config.svg

%changelog
* Mon Oct 19 2026 Infinity OS Contributors <noreply@github.com> - 1.0.0-1
- Add desktop, dock and tweaks configuration interface
