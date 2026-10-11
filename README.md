# Infinity OS

Infinity OS is a Fedora 44 Workstation remix with a customized GNOME desktop. This repository is the image definition, not a released ISO. It is based on Fedora's [KIWI descriptions](https://forge.fedoraproject.org/releng/kiwi-descriptions), branch `f44`.

## Included in the image

- Firefox as the default browser, GNOME Builder, and GNOME Extensions.
- Blur My Shell and Window Is Ready - Notification Remover, enabled for new users.
- Zsh as the default shell for new accounts, Oh My Zsh, Powerline, and Powerline fonts.
- Fedora Mesa drivers and Intel/AMD firmware on x86_64; NVIDIA `akmod-nvidia` and userspace driver on x86_64.
- Broad FFmpeg and GStreamer codec support from RPM Fusion.

Fedora and Fedora Updates remain the base repositories. [RPM Fusion Free and Nonfree](https://rpmfusion.org/) supply codecs and the NVIDIA driver. Their signed release packages are installed into the image so updates continue to use those repositories. This software may have licensing or patent restrictions in some countries. NVIDIA's kernel module requires a build for the running kernel and may require signing when Secure Boot is enabled.

## Build

Build on Fedora 44 with the target architecture. Install the host tools:

```sh
sudo dnf install kiwi kiwi-systemdeps distribution-gpg-keys
```

For a Live ISO, from this repository:

```sh
sudo ./kiwi-build --kiwi-file=Fedora.kiwi --image-type=iso --image-profile=Infinity-GNOME-Live --output-dir=./outdir
```

The same profile builds `aarch64` on an ARM Fedora host and `x86_64` on an x86_64 Fedora host or CI runner. Apple Silicon Parallels virtualizes ARM Linux; the x86_64 build needs a separate x86_64 builder. `Infinity-GNOME-Disk` is the disk-image profile.

The image has not yet completed a full KIWI build. The development VM on the connected PRO STORAGE disk is currently standard Fedora 44, and its first-run account setup must be completed before it can build this definition.

## Sources and licensing

This repository follows the upstream Fedora KIWI description's GPL-3.0-or-later license in [COPYING](COPYING). Bundled Oh My Zsh and the Window Is Ready extension have their own licenses and pinned source details in [THIRD_PARTY.md](THIRD_PARTY.md). Before distributing an ISO, review the [Fedora Remix guidelines](https://fedoraproject.org/wiki/Remix) and the terms for RPM Fusion and NVIDIA packages.
