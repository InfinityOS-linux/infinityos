Name:           infinityos-repos
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS signed RPM repository configuration
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinityos-repos-%{version}.tar.gz
BuildArch:      noarch
Requires:       dnf5

%description
Configures the signed Infinity OS RPM repository and initializes metadata
signature trust for unattended system updates.

%prep
%setup -q

%build

%install
cp -a etc usr %{buildroot}/

%post
if [ -d /run/systemd/system ]; then
    systemctl disable infinityos-repo-trust.service >/dev/null 2>&1 || :
    systemctl enable infinityos-repo-trust.timer >/dev/null 2>&1 || :
fi

%files
%license /usr/share/licenses/infinityos-repos/COPYING
/usr/share/infinityos/build-revisions/infinityos-repos
%config(noreplace) /etc/yum.repos.d/infinityos.repo
/etc/pki/rpm-gpg/RPM-GPG-KEY-infinityos
/usr/lib/systemd/system/infinityos-repo-trust.service
/usr/lib/systemd/system/infinityos-repo-trust.timer

%changelog
* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Manage the signed RPM repository and first boot trust
