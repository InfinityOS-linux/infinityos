# Bundled components

| Component | Source | Version | License |
| --- | --- | --- | --- |
| Oh My Zsh | https://github.com/ohmyzsh/ohmyzsh | `48feb570f7b7d80cc7554629ba428c520ea8a3d5`; runtime core and the three configured plugins | MIT, included at `root/usr/share/oh-my-zsh/LICENSE.txt` |
| Powerlevel10k and gitstatus | https://github.com/romkatv/powerlevel10k | `v1.20.0`; the architecture-specific gitstatus daemon is fetched and checksum-checked during the image build | MIT, included at `root/usr/share/oh-my-zsh/custom/themes/powerlevel10k/LICENSE` |
| IBM Plex Sans | https://github.com/IBM/plex/releases/tag/%40ibm/plex-sans%401.1.0 | `1.1.0`; 16 TTF faces from the upstream release | OFL-1.1, included at `root/usr/share/licenses/infinityos-plex-sans/LICENSE.txt` |
| Iosevka Term | https://github.com/be5invis/Iosevka/releases/tag/v34.9.0 | `34.9.0`; four TTF faces extracted from `PkgTTF-IosevkaTerm-34.9.0.zip` (SHA-256 `1c0b8ac68ca210cc253c1833619d37ed2227d96fbdda0a36231375828b7bd6fb`) at image build | OFL-1.1, included at `root/usr/share/licenses/infinityos-iosevka/LICENSE.md` |
| Proview | https://github.com/emanuelelongo/proview/releases/tag/v1.4 | `v1.4`; upstream AppImage installed for ARM64 or x86_64 with SHA-256 verification | AGPL-3.0, included at `root/usr/share/licenses/infinityos-proview/LICENSE.txt` |
| Window Is Ready - Notification Remover | https://extensions.gnome.org/extension/1007/window-is-ready-notification-remover/ | 28, SHA-256 `abe4be91ad0a7086899ff4d92e463149c26b56e20291e75aa8e4443b57926cd6` of the upstream ZIP | Apache-2.0, included beside the extension |
| Orchis Theme | https://github.com/vinceliuice/Orchis-theme | `a4c48a425e63808345e824495964bd9c2f462e04`, built as `Orchis-Purple-Dark-Compact` and `Orchis-Purple-Light-Compact` with `compact` and `macos` tweaks | GPL-3.0, included at `root/usr/share/themes/Orchis-Purple-Dark-Compact/COPYING` |
| GNOME Control Center UI templates | https://gitlab.gnome.org/GNOME/gnome-control-center | 50.4, adjusted to hide Accent Color and Support GNOME at `root/usr/share/infinityos/settings-overlays/` | GPL-2.0-or-later |
| Kora icon theme | https://github.com/bikass/kora | `v2.0.6` (`58ed0dd8bfda26fbff0b424c46c9bd2c43fa1527`), main `kora` variant; InfinityTerminal icon adapts `apps/scalable/terminal.svg` with the Infinity logo | GPL-3.0, extracted to `/usr/share/licenses/kora/LICENSE` during image build |
| OpenLogi application icon | https://github.com/AprilNEA/OpenLogi/blob/master/crates/openlogi-desktop/icon/AppIcon.icns | Converted to PNG for InfinityLauncher | MIT or Apache-2.0; upstream license files at https://github.com/AprilNEA/OpenLogi |
| Desktop Icons NG (DING) | https://extensions.gnome.org/extension/2087/desktop-icons-ng-ding/ | 99 for GNOME 50, SHA-256 `f5f80d3371f00b7f3fd073d33c90f1c18750f006a284e76f37c1973685a33acc` of the upstream ZIP | GPL-3.0, included beside the extension |
| WACK Sonoma Lockscreen | https://github.com/rinzler69-wastaken/wack-sonoma-lockscreen | `e8c162421d6bf2adf17cce840f33c5bfb8d4b317`, user-session files packaged as in the upstream `make pack` target | GPL-3.0, included beside the extension |
| Bibata Modern Ice cursor | https://github.com/ful1e5/Bibata_Cursor | `v2.0.7`, SHA-256 `a68cae60c4dc706350e194ebc91c5fe48bc7bc9d59e119555834a2a7ee5078ef` of the Linux archive | GPL-3.0, included at `root/usr/share/licenses/Bibata-Modern-Ice/LICENSE` |
| Ghostty / InfinityTerminal | https://ghostty.org/ | 1.3.1, upstream archive SHA-256 `3349d25600ffbda281197a18314f7d18791969cffe9474f0ff16a45a9ebfccdb`, with Infinity OS patch at `ghostty/ghostty-1.3.1-infinity.patch` | MIT, included at `ghostty/GHOSTTY-LICENSE` |

Performance configuration in `root/usr/share/infinityos/performance/` is adapted from [Bazzite's desktop zram, inotify, and networking settings](https://github.com/ublue-os/bazzite/tree/main/system_files/desktop/shared) and [Nobara's disk scheduler rules](https://github.com/Nobara-Project/rpm-sources/blob/main/baseos/nobara-login/60-ioschedulers.rules). These are configuration values and short udev rules, not bundled binaries.

InfinityLauncher displays application icons bundled under `packages/infinity-launcher/root/usr/share/infinityos/launcher-icons/`. Flatpak app icons come from the applications' Flathub metadata; Craft icons come from the corresponding [Storytold](https://github.com/storytold) repositories. OpenGamepadUI's icon comes from [its upstream repository](https://github.com/ShadowBlip/OpenGamepadUI), Docker's from [Simple Icons](https://simpleicons.org/), and the Claude and Codex icons from InfinityTerminal's existing assets. Product names and logos belong to their respective owners.

Orchis was built on Fedora 44 using `sassc` and `./install.sh -d /out -t purple -c dark -s compact --tweaks compact macos --shell 48` and the same command with `-c light`. Its complete upstream source at the pinned commit is archived at `assets/third-party/Orchis-theme-a4c48a425e63-source.tar.xz` (SHA-256 `5ac61bcba8117c339267b1f593b41716c42e668bf125eef8e07f637adfbe65f7`). The image bundles only the GNOME/GTK parts of the generated theme. Upstream currently provides GNOME Shell styles through version 48; GNOME 50 compatibility of that stylesheet needs a visual boot test. The Fedora `gnome-shell-extension-user-theme` and `gtk-murrine-engine` packages provide the Shell theme loader and GTK 2 engine.

Infinity OS darkens the generated dark Orchis GTK 3, GTK 4, and GNOME Shell neutral surfaces and replaces light Shell submenus, quick-toggle menus, and overview search with dark purple variants. The original upstream source archive remains unchanged.

Kora's pinned source archive is `root/usr/share/infinityos/kora-v2.0.6.tar.gz` (SHA-256 `159bdb7a09409a12e54a71136ec8889c51b0bf7c145c8b20e3509dc1e90089bd`). The image setup extracts the main icon theme and license, regenerates its icon cache, and removes the archive from the installed system.

DING is unpacked from its pinned GNOME Extensions ZIP into `root/usr/share/gnome-shell/extensions/ding@rastersoft.com`; its GSettings schema is compiled during image setup. Bibata Modern Ice is extracted from `root/usr/share/infinityos/Bibata-Modern-Ice-v2.0.7.tar.xz` into the installed icon themes. Both are enabled only for Infinity OS profiles.

Blur My Shell, Powerline Symbols fonts, Firefox, drivers, and codecs are installed as signed packages from Fedora or RPM Fusion at image build time. Their versions follow those repositories' updates.

The bundled Flathub remote descriptor (`root/etc/flatpak/remotes.d/flathub.flatpakrepo`) and signing key come from https://flathub.org/repo/flathub.flatpakrepo (retrieved 2026-10-12; SHA-256 `3371dd250e61d9e1633630073fefda153cd4426f72f4afa0c3373ae2e8fea03a`). No Flathub applications are bundled.
