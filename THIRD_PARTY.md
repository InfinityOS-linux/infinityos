# Bundled components

| Component | Source | Version | License |
| --- | --- | --- | --- |
| Oh My Zsh | https://github.com/ohmyzsh/ohmyzsh | `48feb570f7b7d80cc7554629ba428c520ea8a3d5`; runtime core and the three configured plugins | MIT, included at `root/usr/share/oh-my-zsh/LICENSE.txt` |
| Window Is Ready - Notification Remover | https://extensions.gnome.org/extension/1007/window-is-ready-notification-remover/ | 28, SHA-256 `abe4be91ad0a7086899ff4d92e463149c26b56e20291e75aa8e4443b57926cd6` of the upstream ZIP | Apache-2.0, included beside the extension |

Blur My Shell, Powerline, Firefox, drivers, and codecs are installed as signed packages from Fedora or RPM Fusion at image build time. Their versions follow those repositories' updates.

The bundled Flathub remote descriptor (`root/etc/flatpak/remotes.d/flathub.flatpakrepo`) and signing key come from https://flathub.org/repo/flathub.flatpakrepo (retrieved 2026-10-12; SHA-256 `3371dd250e61d9e1633630073fefda153cd4426f72f4afa0c3373ae2e8fea03a`). No Flathub applications are bundled.
