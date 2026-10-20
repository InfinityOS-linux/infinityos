Name:           infinityos-shell-extensions
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Versioned Infinity OS GNOME Shell extensions and desktop defaults
License:        GPL-3.0-only AND GPL-3.0-or-later AND GPL-2.0-only AND GPL-2.0-or-later AND BSD-2-Clause AND Apache-2.0
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinityos-shell-extensions-%{version}.tar.gz
BuildArch:      noarch
Requires:       gnome-shell >= 50
Requires:       gnome-shell < 51
Requires:       gpaste-ui >= 50.6
Requires:       glib2
Requires:       dconf
Requires:       python3-gobject

# Adopt the six Fedora extension directories so that only an Infinity OS RPM
# may update their code. The GPaste service remains Fedora-managed.
Provides:       gnome-shell-extension-gpaste = 50.6-1.fc44
Provides:       gnome-shell-extension-appindicator = 64-1.fc44
Provides:       gnome-shell-extension-blur-my-shell = 72-1.fc44
Provides:       gnome-shell-extension-caffeine = 60-2.fc44
Provides:       gnome-shell-extension-user-theme = 50.4-1.fc44
Provides:       gnome-shell-extension-vertical-workspaces = 50.2-1.fc44
Obsoletes:      gnome-shell-extension-gpaste < 9999
Obsoletes:      gnome-shell-extension-appindicator < 9999
Obsoletes:      gnome-shell-extension-blur-my-shell < 9999
Obsoletes:      gnome-shell-extension-caffeine < 9999
Obsoletes:      gnome-shell-extension-user-theme < 9999
Obsoletes:      gnome-shell-extension-vertical-workspaces < 9999

%description
Ships the GNOME extensions and desktop defaults tested together for Infinity
OS 44. Fedora updates cannot replace an enabled extension independently of
the matching Infinity OS package release.

%prep
%setup -q

%build

%install
cp -a usr etc %{buildroot}/

%posttrans
glib-compile-schemas /usr/share/glib-2.0/schemas || :
for uuid in \
    ding@rastersoft.com \
    wack-lockscreen-clock@rinzler69-wastaken.github.com \
    wack-shell@rinzler69-wastaken.github.com \
    tilingshell@ferrarodomenico.com \
    dash2dock-animated@infinityos.org; do
    glib-compile-schemas "/usr/share/gnome-shell/extensions/$uuid/schemas" || :
done
dconf update || :

%files
/usr/bin/infinityos-shell-recover
/usr/share/infinityos/build-revisions/infinityos-shell-extensions
/usr/share/infinityos/gnome-defaults
/usr/share/infinityos/blur-defaults
/etc/dconf/db/local.d/00-infinityos
/etc/dconf/db/local.d/01-infinity-blur
/usr/share/gnome-shell/extensions/GPaste@gnome-shell-extensions.gnome.org/
/usr/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com/
/usr/share/gnome-shell/extensions/blur-my-shell@aunetx/
/usr/share/gnome-shell/extensions/caffeine@patapon.info/
/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/
/usr/share/gnome-shell/extensions/ding@rastersoft.com/
/usr/share/gnome-shell/extensions/tilingshell@ferrarodomenico.com/
/usr/share/gnome-shell/extensions/user-theme@gnome-shell-extensions.gcampax.github.com/
/usr/share/gnome-shell/extensions/vertical-workspaces@G-dH.github.com/
/usr/share/gnome-shell/extensions/wack-lockscreen-clock@rinzler69-wastaken.github.com/
/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/
/usr/share/gnome-shell/extensions/windowIsReady_Remover@nunofarruca@gmail.com/
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.appindicator.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.blur-my-shell.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.caffeine.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.user-theme.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.vertical-workspaces.gschema.xml
%license /usr/share/licenses/infinityos-shell-extensions/*

%changelog
* Sun Oct 18 2026 Infinity OS Contributors <noreply@infinityos.eu> - 1.0.0-1
- Adopt tested GNOME extension snapshots and desktop defaults
