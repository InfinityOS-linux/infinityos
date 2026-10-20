Name:           infinityos-wallpapers
Version:        1.1.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS desktop wallpapers
License:        GPL-3.0-or-later
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinityos-wallpapers-%{version}.tar.gz
BuildArch:      noarch

%description
Infinity OS wallpapers and their GNOME Backgrounds catalog.

%prep
%setup -q

%build

%install
cp -a usr %{buildroot}/

%transfiletriggerin -- /usr/share/gnome-background-properties/adwaita.xml
# Keep only the blue Adwaita tile hidden, including after gnome-backgrounds updates.
rm -f /usr/share/gnome-background-properties/adwaita.xml

%files
%license /usr/share/licenses/infinityos-wallpapers/COPYING
/usr/share/infinityos/build-revisions/infinityos-wallpapers
/usr/share/backgrounds/infinityos/
/usr/share/gnome-background-properties/00-infinityos.xml

%changelog
* Tue Oct 20 2026 Infinity OS Contributors <noreply@infinityos.eu> - 1.1.0-1
- Add six 4K wallpapers and hide the blue GNOME Adwaita chooser tile

* Wed Oct 14 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.0.0-1
- Add packaged 4K Infinity OS wallpapers
