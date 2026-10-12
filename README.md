# Infinity OS

Infinity OS is a Fedora 44 Workstation remix with a customized GNOME desktop. This repository contains its image definition. It is based on Fedora's [KIWI descriptions](https://forge.fedoraproject.org/releng/kiwi-descriptions), branch `f44`.

The Infinity OS image profiles use Fedora's `generic-release` and `generic-logos` packages in place of Fedora's trademarked release and logo packages. Fedora and RPM Fusion remain the package sources. The visible system identity, wallpaper, icon and Plymouth startup screen use Infinity OS branding, with `#645394` as the base color. GNOME's built-in `purple` accent is the closest available system accent; the exact hex value is used in the artwork.

GNOME Initial Setup uses the Infinity OS welcome illustration through a GResource overlay scoped to its systemd user services. Check the resource path when upgrading GNOME Initial Setup.

## Included in the image

- Firefox as the default browser, GNOME Builder, and GNOME Extensions.
- Blur My Shell, Window Is Ready - Notification Remover, and AppIndicator, enabled for new users.
- Flathub as a system-wide Flatpak remote, with GNOME Software support for Flatpak apps.
- Minimize and maximize titlebar buttons; Alt+Tab switches windows rather than applications.
- Orchis Purple Dark Compact as the default GTK and GNOME Shell theme, with a compact Shell panel and macOS-style window buttons on the left.
- GameMode, MangoHud, Gamescope, and gamepad permissions; Steam and Lutris on `x86_64`.
- Zsh as the default shell for new accounts, Oh My Zsh, Powerline, and Powerline fonts.
- Fedora Mesa drivers and Intel/AMD firmware on x86_64; NVIDIA `akmod-nvidia` and userspace driver on x86_64.
- Broad FFmpeg and GStreamer codec support from RPM Fusion.
- Light and dark Infinity OS wallpapers, logo, boot splash, GNOME defaults, and custom GNOME Initial Setup welcome artwork.

Orchis is bundled as prebuilt theme assets, so image builds do not fetch or compile it. The User Themes extension loads its GNOME Shell stylesheet; GTK 4/libadwaita styling is linked into each new account's configuration. GTK 4/libadwaita and Flatpak apps may render some controls differently from GTK 3, especially after GNOME upgrades. The system's native purple accent remains the closest built-in match to `#645394`.

Fedora and Fedora Updates remain the base repositories. [RPM Fusion Free and Nonfree](https://rpmfusion.org/) supply codecs and the NVIDIA driver. Their signed release packages are installed into the image so updates continue to use those repositories. Fedora's third-party repositories are enabled during image creation, and GNOME Initial Setup skips its repository opt-in page. This software may have licensing or patent restrictions in some countries. NVIDIA's kernel module requires a build for the running kernel and may require signing when Secure Boot is enabled.

Gamescope, MangoHud, Steam, and Lutris follow [Bazzite's Fedora-based desktop image](https://github.com/ublue-os/bazzite/blob/main/Containerfile). Infinity OS stays a regular DNF-managed Fedora derivative and uses Fedora's GameMode for on-demand performance instead of Bazzite's image-specific resource service. A moderate `vm.max_map_count=1048576` supports games that use many memory mappings. Steam launch options can use `gamemoderun %command%`, optionally prefixed with `mangohud`. Gamescope and MangoHud are installed but not forced on every application. Hardware-specific power, I/O, and security settings from Bazzite are not applied globally.

## Build

Build on Fedora 44 with the target architecture. Install the host tools:

```sh
sudo dnf install kiwi kiwi-systemdeps distribution-gpg-keys
```

For a Live ISO, from this repository:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=iso --image-profile=Infinity-GNOME-Live --output-dir=./outdir
```

The same profile builds `aarch64` on an ARM Fedora host and `x86_64` on an x86_64 Fedora host or CI runner. Apple Silicon Parallels virtualizes ARM Linux; the x86_64 build needs a separate x86_64 builder. `Infinity-GNOME-Disk` is the disk-image profile.

The ARM Live ISO has completed a KIWI build and passed its media check in Parallels on Apple Silicon. The Live desktop started with Infinity OS branding and the purple theme. The build artifact is at `PRO STORAGE/InfinityOS/build/InfinityOS.aarch64-44.iso`; its SHA-256 is recorded beside it. The ARM disk profile built a GPT disk with EFI, boot, and root partitions. Its RAW and VMDK files are in the same build directory; the VMDK passed `qemu-img check`.

The `Infinity OS Installed ARM` Parallels VM boots from `PRO STORAGE/InfinityOS/build/parallels/InfinityOS.aarch64-44-generic-initramfs.hdd` and reaches GNOME Initial Setup, showing “Welcome to Infinity OS 44!”. This is a writable, plain Parallels disk converted from the disk image. The first disk attempt used a host-specific initramfs that could not find its root partition in Parallels. The existing RAW disk was repaired with a generic initramfs, and `config.sh` now requests generic initramfs generation for future Infinity OS disk builds. A compressed DMG is kept as an intermediate artifact; attaching that DMG directly as a VM hard drive fails because Parallels treats it as read-only. Account creation and a full user login are still pending.

The `/etc/os-release` identity is currently installed by `config.sh` over `generic-release`; a dedicated `infinityos-release` RPM is needed before publishing so future `generic-release` upgrades cannot restore the generic identity. Further desktop changes should be made in this repository and tested in the development VM, then included in a new image build after the planned changes are complete.

## Sources and licensing

This repository follows the upstream Fedora KIWI description's GPL-3.0-or-later license in [COPYING](COPYING). Bundled Oh My Zsh, Orchis and the Window Is Ready extension have their own licenses and pinned source details in [THIRD_PARTY.md](THIRD_PARTY.md). Before distributing an ISO, review the [Fedora Remix guidelines](https://fedoraproject.org/wiki/Remix) and the terms for RPM Fusion and NVIDIA packages.
