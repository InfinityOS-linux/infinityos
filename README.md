# Infinity OS

**A Fedora 44 remix with a writable GNOME desktop.** Infinity OS keeps Fedora's DNF package model and builds a distinct desktop around a dark purple identity, a drop-down terminal, and an application chooser for first login. This repository contains the KIWI image definition, desktop defaults, application sources, RPM packaging, and release pipeline.

> **Project status:** active development. The ARM disk image is used in Parallels for desktop testing. Build and installation checks are required before publishing each new image. The same image definition supports `x86_64`, which needs an x86_64 build host or runner.

## What ships

| Area | Configuration |
| --- | --- |
| Base | Fedora 44 packages, DNF, Fedora Updates, RPM Fusion Free and Nonfree |
| Desktop | GNOME with Orchis Purple Dark Compact by default and an optional Light mode, Kora icons, Bibata cursor, Infinity OS artwork, and a dark lock screen |
| Storage | Writable Btrfs root, systemd-boot, Snapper timeline and cleanup |
| Applications | Firefox, Flatpak with Flathub, InfinityLauncher, InfinityTerminal; Chrome DRM fallback on ARM64 |
| Development | Zsh with Oh My Zsh and Powerline; GNOME Builder |
| Gaming | GameMode, MangoHud, Gamescope, gamepad support; Steam and Lutris on `x86_64` |
| Hardware | Fedora Intel and AMD graphics support; NVIDIA packages on `x86_64` |

## Performance defaults

Infinity OS uses compressed zram swap sized to half of RAM, capped at 16 GiB, with zstd compression. This follows Bazzite's desktop configuration and works with the writable Fedora image and normal DNF updates. The image also raises inotify limits for large game libraries and development projects and enables TCP path-MTU probing when a connection encounters a black hole. Nobara-inspired udev rules select `none` for NVMe, `mq-deadline` for SATA SSDs and eMMC, and `bfq` for rotating SATA disks. These rules apply only to whole disks; unsupported device types keep the kernel's choice.

GameMode, MangoHud, Gamescope, TLP, and the existing bounded `vm.max_map_count` setting remain in place. No OSTree or immutable root is used.

**InfinityLauncher** opens on first login. It groups optional software under AI, System, Gaming, Creative, Office, and Programming. You choose applications and press **Apply** before installation starts. The choices include Steam, Heroic, Lutris, Prism Launcher, creative tools, VS Code, Docker CE, Codex, and Claude. Its source and RPM specification live in [`packages/infinity-launcher`](packages/infinity-launcher).

Its footer can schedule one more launch at the next login. The interface follows the session language (Polish and English are bundled). RAMDrive warns through GNOME's shutdown confirmation when it contains files; canceling keeps the session and files, while continuing the shutdown clears the folder. A crash or hard reset leaves its contents intact.

**InfinityTerminal** uses a patched Ghostty renderer. Press **Super+T** or use its GNOME panel icon to show and hide it. The first shell tab stays pinned; Codex and Claude gain pinned tabs when their CLI tools are installed. Their context menus offer a separate red YOLO mode tab. The terminal source and package live in [`packages/infinity-terminal`](packages/infinity-terminal), with the renderer patch in [`ghostty`](ghostty).

GNOME starts with desktop icons, AppIndicator support, dynamic Blur My Shell, the Window Is Ready notification remover, and WACK Sonoma Lockscreen in Cupertino mode. WACK Shell adds the panel menu with a white Infinity logo. The signed `gnome-rounded-blur` helper fixes dynamic blur corners; its COPR repository is restricted to that package. Titlebars show minimize and maximize buttons. **Alt+Tab** switches windows. Firefox keeps **Ctrl+T** for a new tab. Location Services start enabled, and automatic problem reporting starts disabled.

**RAMDrive** is a desktop scratch folder with a memory-chip icon and a bookmark in Files. Its contents are deleted during an orderly shutdown or reboot. The folder uses disk storage so files remain recoverable after a crash or forced reset; it is not a `tmpfs` RAM disk.

## Packages and updates

Fedora and Fedora Updates provide the base system. RPM Fusion provides multimedia codecs and nonfree hardware packages. The desktop includes Bazaar as its Flatpak app store and InfinityUpdater for daily RPM and Flatpak update checks. It also includes FFmpeg, GNOME Files archive integration, UnRAR, 7-Zip, TLP, and purple folder icons. Microsoft Core Fonts are downloaded and checksum-verified on the installed machine after network access is available; font files are not distributed in the image. Infinity OS builds `infinity-launcher` and `infinity-terminal` as signed RPMs and publishes them through its own DNF repository. See [`packages/README.md`](packages/README.md) for the build, signing, and release flow. Docker CE uses Docker's official Fedora repository when selected in InfinityLauncher.

Firefox enables Encrypted Media Extensions through an unlocked system policy and obtains supported Widevine modules from Mozilla/Google on compatible platforms. On ARM64, where Firefox's Linux Widevine distribution is still pending, a first-boot timer installs Google's native ARM64 Chrome from Flathub as a DRM-capable fallback. Firefox remains the default browser. Chrome and its Widevine component update through their normal upstream/Flatpak mechanisms; Infinity OS does not redistribute CDM binaries. PlayReady and FairPlay are not provided as general-purpose Linux desktop browser modules. Streaming services can impose their own browser, resolution, or hardware requirements.

The image build requires the Infinity OS RPM repository to be published and reachable. The GitLab pipeline publishes it after a successful build on `main`. Applications installed directly from third-party GitHub releases do not receive updates from the Infinity OS repository.

## Build an image

Use a Fedora 44 host with the target CPU architecture and Btrfs ACL support. Install KIWI and its system dependencies:

```sh
sudo dnf install kiwi kiwi-systemdeps distribution-gpg-keys
```

Build a Live ISO from the repository root:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=iso \
  --image-profile=Infinity-GNOME-Live --output-dir=/var/tmp/infinityos-iso
```

Build a writable disk image:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=oem \
  --image-profile=Infinity-GNOME-Disk --output-dir=/var/tmp/infinityos-disk
```

The wrapper runs [`scripts/finalize-infinity-disk`](scripts/finalize-infinity-disk) after an OEM build. That step fixes permissions on the Btrfs root subvolume so desktop services can start. The resulting RAW disk has a 2 GB EFI partition and Btrfs `root`, `home`, and `var` subvolumes. Apple Silicon Parallels runs the `aarch64` disk; building `x86_64` requires an x86_64 Fedora host or CI runner.

## Project layout

- [`InfinityOS.kiwi`](InfinityOS.kiwi), [`repositories/`](repositories), and [`teams/`](teams) define image profiles and package sources.
- [`root/`](root) contains files placed in the image, including GNOME defaults, themes, extensions, and artwork.
- [`config.sh`](config.sh) applies image configuration and enables system services.
- [`packages/`](packages) contains the InfinityLauncher and InfinityTerminal RPMs.
- [`tests/`](tests) contains focused checks for application selection and RAMDrive cleanup.

## Sources and licensing

Infinity OS follows Fedora's [KIWI descriptions](https://forge.fedoraproject.org/releng/kiwi-descriptions) on the `f44` branch and retains their GPL-3.0-or-later license in [`COPYING`](COPYING). Fedora's `generic-release` and `generic-logos` packages replace Fedora's trademarked identity packages. See [`THIRD_PARTY.md`](THIRD_PARTY.md) for bundled component sources and licenses. Review the [Fedora Remix guidelines](https://fedoraproject.org/wiki/Remix) and local rules for codecs, RPM Fusion packages, and NVIDIA software before redistributing an image.
