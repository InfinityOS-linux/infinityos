Name:           infinityos-ramdrive
Version:        1.1.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS RAMDrive setup and shutdown protection
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinityos-ramdrive-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       xdg-user-dirs

%description
Creates protected RAMDrive storage with a removable desktop shortcut, warns
before orderly shutdown when it contains files, and clears its contents only
when shutdown proceeds.

%prep
%setup -q

%build

%install
cp -a usr etc %{buildroot}/

%posttrans
if [ -d /run/systemd/system ]; then
    /usr/bin/systemctl daemon-reload >/dev/null 2>&1 || :
    /usr/bin/systemctl enable --now infinityos-ramdrive-prepare.path >/dev/null 2>&1 || :
    /usr/bin/systemctl start infinityos-ramdrive-prepare.service >/dev/null 2>&1 || :
fi

%files
%license /usr/share/licenses/infinityos-ramdrive/COPYING
/usr/share/infinityos/build-revisions/infinityos-ramdrive
/usr/libexec/infinityos-ramdrive
/usr/libexec/infinityos-ramdrive-shutdown
%attr(0755,root,root) /usr/libexec/infinityos-ramdrive-guard
/usr/libexec/infinityos-ramdrive-prepare
/usr/lib/systemd/system/infinityos-ramdrive.service
/usr/lib/systemd/system/infinityos-ramdrive-prepare.service
/usr/lib/systemd/system/infinityos-ramdrive-prepare.path
/etc/xdg/autostart/infinityos-ramdrive.desktop
/etc/xdg/autostart/infinityos-ramdrive-guard.desktop

%changelog
* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.1.0-1
- Protect RAMDrive storage while allowing removal of its desktop shortcut

* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Package RAMDrive with a GNOME shutdown warning
