Name:           infinityos-ramdrive
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS RAMDrive setup and shutdown protection
License:        GPL-3.0-or-later
URL:            https://gitlab.com/godorowski/infinityos
Source0:        infinityos-ramdrive-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       xdg-user-dirs

%description
Creates the desktop RAMDrive, warns before orderly shutdown when it contains
files, and clears its contents only when shutdown proceeds.

%prep
%setup -q

%build

%install
cp -a usr etc %{buildroot}/

%files
%license /usr/share/licenses/infinityos-ramdrive/COPYING
/usr/libexec/infinityos-ramdrive
/usr/libexec/infinityos-ramdrive-shutdown
/usr/libexec/infinityos-ramdrive-guard
/usr/lib/systemd/system/infinityos-ramdrive.service
/etc/xdg/autostart/infinityos-ramdrive.desktop
/etc/xdg/autostart/infinityos-ramdrive-guard.desktop

%post
%systemd_post infinityos-ramdrive.service

%preun
%systemd_preun infinityos-ramdrive.service

%postun
%systemd_postun_with_restart infinityos-ramdrive.service

%changelog
* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Package RAMDrive with a GNOME shutdown warning
