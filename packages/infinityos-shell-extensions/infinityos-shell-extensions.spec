Name:           infinityos-shell-extensions
Version:        1.0.0
Release:        %{?infinity_release}%{!?infinity_release:1}%{?dist}
Summary:        Versioned Infinity OS GNOME Shell extensions and desktop defaults
License:        GPL-3.0-only AND GPL-3.0-or-later AND GPL-2.0-only AND GPL-2.0-or-later AND BSD-2-Clause AND Apache-2.0 AND CC0-1.0
URL:            https://github.com/InfinityOS-linux/infinityos
Source0:        infinityos-shell-extensions-%{version}.tar.gz
BuildArch:      noarch
Requires:       gnome-shell >= 51
Requires:       gnome-shell < 52
Requires:       gpaste-ui >= 51.0
Requires:       glib2
Requires:       dconf
Requires:       python3-gobject
Requires:       librsvg2
Requires:       gettext
Requires:       gnome-rounded-blur

# Adopt the six Fedora extension directories so that only an Infinity OS RPM
# may update their code. The GPaste service remains Fedora-managed.
Provides:       gnome-shell-extension-gpaste = 51.0-1.fc45
Provides:       gnome-shell-extension-appindicator = 66-1.fc45
Provides:       gnome-shell-extension-blur-my-shell = 75-1.fc45
Provides:       gnome-shell-extension-caffeine = 61-1.infinityos.fc45
Provides:       gnome-shell-extension-user-theme = 51.0-1.fc45
Provides:       gnome-shell-extension-vertical-workspaces = 51.0-1.fc45
Obsoletes:      gnome-shell-extension-gpaste < 9999
Obsoletes:      gnome-shell-extension-appindicator < 9999
Obsoletes:      gnome-shell-extension-blur-my-shell < 9999
Obsoletes:      gnome-shell-extension-caffeine < 9999
Obsoletes:      gnome-shell-extension-user-theme < 9999
Obsoletes:      gnome-shell-extension-vertical-workspaces < 9999

%description
Ships the GNOME extensions and desktop defaults tested together for Infinity
OS 45. Fedora updates cannot replace an enabled extension independently of
the matching Infinity OS package release.

%prep
%setup -q

%build

%install
cp -a usr etc %{buildroot}/

%posttrans
/usr/libexec/infinityos-bin-label || :
glib-compile-schemas /usr/share/glib-2.0/schemas || :
for uuid in \
    raccoonlauncher@shimafallah.github.io \
    nowplay@LalaloyXyz \
    ding@rastersoft.com \
    wack-lockscreen-clock@rinzler69-wastaken.github.com \
    wack-shell@rinzler69-wastaken.github.com \
    globalmenu@ShiroOSL.github.io \
    tilingshell@ferrarodomenico.com \
    dash2dock-animated@infinityos.org; do
    glib-compile-schemas "/usr/share/gnome-shell/extensions/$uuid/schemas" || :
done
dconf update || :
if test -d /usr/share/icons/kora/places; then
    /usr/libexec/infinityos-tint-system-icons /usr/share/icons/kora || :
    cp -a /usr/share/infinityos/folder-icons/. /usr/share/icons/kora/places/scalable/ || :
    gtk-update-icon-cache -f -q /usr/share/icons/kora || :
fi
gtk-update-icon-cache -f -q /usr/share/icons/hicolor || :

%transfiletriggerin -- /usr/share/locale/en_GB/LC_MESSAGES
/usr/libexec/infinityos-bin-label || :

%files
/usr/libexec/infinityos-enable-desktop-additions
/etc/xdg/autostart/infinityos-enable-desktop-additions.desktop
/usr/share/gnome-shell/extensions/nowplay@LalaloyXyz/
/usr/share/gnome-shell/extensions/raccoonlauncher@shimafallah.github.io/
/usr/bin/infinityos-shell-recover
/usr/libexec/infinityos-enable-global-menu
/etc/xdg/autostart/infinityos-enable-global-menu.desktop
/usr/libexec/infinityos-tint-system-icons
/usr/libexec/infinityos-bin-label
/usr/share/infinityos/build-revisions/infinityos-shell-extensions
/usr/share/infinityos/gnome-defaults
/usr/share/infinityos/blur-defaults
/usr/share/infinityos/folder-icons/
/usr/share/infinityos/bin.desktop
/usr/share/icons/kora/places/scalable/folder-projects.svg
/usr/share/icons/hicolor/scalable/apps/infinityos-logo.svg
/usr/share/icons/hicolor/scalable/apps/infinityos-panel-mark.svg
/usr/share/icons/hicolor/scalable/apps/infinityos-panel-mark-v2.svg
/usr/share/icons/hicolor/scalable/apps/infinityos-symbolic.svg
/usr/share/icons/hicolor/256x256/apps/infinityos-logo.png
/etc/dconf/db/local.d/00-infinityos
/etc/dconf/db/local.d/01-infinity-blur
/usr/share/gnome-shell/extensions/GPaste@gnome-shell-extensions.gnome.org/
/usr/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com/
/usr/share/gnome-shell/extensions/blur-my-shell@aunetx/
/usr/share/gnome-shell/extensions/caffeine@patapon.info/
/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/
/usr/share/gnome-shell/extensions/ding@rastersoft.com/
/usr/share/gnome-shell/extensions/globalmenu@ShiroOSL.github.io/
/usr/share/gnome-shell/extensions/tilingshell@ferrarodomenico.com/
/usr/share/gnome-shell/extensions/user-theme@gnome-shell-extensions.gcampax.github.com/
/usr/share/gnome-shell/extensions/vertical-workspaces@G-dH.github.com/
/usr/share/gnome-shell/extensions/wack-lockscreen-clock@rinzler69-wastaken.github.com/
/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/
/usr/share/gnome-shell/extensions/windowIsReady_Remover@nunofarruca@gmail.com/
/usr/share/themes/Orchis-Purple-Light-Compact/gnome-shell/gnome-shell.css
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.appindicator.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.blur-my-shell.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.caffeine.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.user-theme.gschema.xml
/usr/share/glib-2.0/schemas/org.gnome.shell.extensions.vertical-workspaces.gschema.xml
%license /usr/share/licenses/infinityos-shell-extensions/*

%changelog
* Sun Oct 18 2026 Infinity OS Contributors <noreply@infinityos.eu> - 1.0.0-1
- Adopt tested GNOME extension snapshots and desktop defaults
