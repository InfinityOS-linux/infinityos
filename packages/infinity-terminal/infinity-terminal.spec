Name:           infinity-terminal
%global debug_package %{nil}
%global _build_id_links none
Version:        1.3.1
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Infinity OS drop-down terminal based on Ghostty
License:        MIT AND GPL-3.0-or-later
URL:            https://gitlab.com/godorowski/infinityos
Source0:        infinity-terminal-%{version}.tar.gz
ExclusiveArch:  aarch64 x86_64
Requires:       gnome-shell

%description
InfinityTerminal combines a patched Ghostty renderer with an Infinity OS
GNOME Shell controller and a persistent user service.

%prep
%setup -q

%build

%install
cp -a usr %{buildroot}/

%posttrans
glib-compile-schemas /usr/share/gnome-shell/extensions/ghostty@infinityos.org/schemas || :

%files
%license /usr/share/licenses/infinity-terminal/GHOSTTY-LICENSE
%license /usr/share/licenses/infinity-terminal/KORA-LICENSE
/usr/bin/infinity-terminal
/usr/bin/ghostty
/usr/libexec/infinityos/ghostty
/usr/lib/systemd/user/ghostty.service
/usr/share/applications/com.infinityos.GhosTTY.desktop
/usr/share/gnome-shell/extensions/ghostty@infinityos.org/
/usr/share/icons/hicolor/scalable/apps/com.infinityos.GhosTTY.svg
/usr/share/icons/hicolor/scalable/apps/infinity-*.svg
/usr/share/infinityos/ghostty/
/usr/share/ghostty/
/usr/share/terminfo/

%changelog
* Mon Oct 12 2026 Infinity OS Contributors <noreply@gitlab.com> - 1.3.1-1
- Initial package
