Name:           infinityos-wallpapers
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS desktop wallpapers
License:        GPL-3.0-or-later
URL:            https://gitlab.com/godorowski/infinityos
Source0:        infinityos-wallpapers-%{version}.tar.gz
BuildArch:      noarch

%description
Infinity OS wallpapers and their GNOME Backgrounds catalog.

%prep
%setup -q

%build

%install
cp -a usr %{buildroot}/

%files
%license /usr/share/licenses/infinityos-wallpapers/COPYING
/usr/share/infinityos/build-revisions/infinityos-wallpapers
/usr/share/backgrounds/infinityos/
/usr/share/gnome-background-properties/00-infinityos.xml

%changelog
* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Add packaged 4K Infinity OS wallpapers
