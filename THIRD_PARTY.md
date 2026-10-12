# Bundled components

| Component | Source | Version | License |
| --- | --- | --- | --- |
| Oh My Zsh | https://github.com/ohmyzsh/ohmyzsh | `48feb570f7b7d80cc7554629ba428c520ea8a3d5`; runtime core and the three configured plugins | MIT, included at `root/usr/share/oh-my-zsh/LICENSE.txt` |
| Window Is Ready - Notification Remover | https://extensions.gnome.org/extension/1007/window-is-ready-notification-remover/ | 28, SHA-256 `abe4be91ad0a7086899ff4d92e463149c26b56e20291e75aa8e4443b57926cd6` of the upstream ZIP | Apache-2.0, included beside the extension |
| Orchis Theme | https://github.com/vinceliuice/Orchis-theme | `a4c48a425e63808345e824495964bd9c2f462e04`, built as `Orchis-Purple-Dark-Compact` with `compact` and `macos` tweaks | GPL-3.0, included at `root/usr/share/themes/Orchis-Purple-Dark-Compact/COPYING` |

Orchis was built on Fedora 44 with `sassc` using `./install.sh -d /out -t purple -c dark -s compact --tweaks compact macos --shell 48`. Its complete upstream source at the pinned commit is archived at `assets/third-party/Orchis-theme-a4c48a425e63-source.tar.xz` (SHA-256 `5ac61bcba8117c339267b1f593b41716c42e668bf125eef8e07f637adfbe65f7`). The image bundles only the GNOME/GTK parts of the generated theme. Upstream currently provides GNOME Shell styles through version 48; GNOME 50 compatibility of that stylesheet needs a visual boot test. The Fedora `gnome-shell-extension-user-theme` and `gtk-murrine-engine` packages provide the Shell theme loader and GTK 2 engine.

Blur My Shell, Powerline, Firefox, drivers, and codecs are installed as signed packages from Fedora or RPM Fusion at image build time. Their versions follow those repositories' updates.

The bundled Flathub remote descriptor (`root/etc/flatpak/remotes.d/flathub.flatpakrepo`) and signing key come from https://flathub.org/repo/flathub.flatpakrepo (retrieved 2026-10-12; SHA-256 `3371dd250e61d9e1633630073fefda153cd4426f72f4afa0c3373ae2e8fea03a`). No Flathub applications are bundled.
