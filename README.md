# Infinity OS

<img src="assets/infinityos-logo.svg" width="112" alt="Infinity OS logo">

**A Fedora 44 Remix built for a polished, personal desktop.** Infinity OS pairs a writable GNOME system with a distinctive purple design, a fast drop-down terminal, a first-run application chooser, and integrated updates. It uses Fedora's familiar DNF package model, so the desktop remains easy to customize and maintain.

This repository is the source for the Infinity OS KIWI images, desktop configuration, InfinityLauncher, InfinityTerminal, InfinityUpdater, RPM packages, and build pipeline.

> **Development status:** the current ARM image is being repaired and has not passed a complete boot and installation test. There is no verified public image release yet. An `x86_64` image requires a separate `x86_64` build host or runner and has not been produced from the current revision.

**Infinity OS is an independent Fedora Remix. It is not provided, supported, or endorsed by the Fedora Project or Red Hat.** Official Fedora Linux is available at [fedoraproject.org](https://fedoraproject.org/).

## Start here

- [Build an image](#build-an-image) from a committed source revision.
- [Package and RPM repository guide](packages/README.md) for application builds and signing.
- [Third-party components](THIRD_PARTY.md) and [redistribution review](docs/REDISTRIBUTION.md) for sources, font licenses, codecs, and driver obligations.
- [Contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md).

## What ships

| Area | Configuration |
| --- | --- |
| Base | Fedora 44 packages, DNF, Fedora Updates, RPM Fusion Free and Nonfree |
| Desktop | GNOME with Orchis Purple Dark Compact by default and an optional Light mode, Kora icons, Bibata cursor, Infinity OS artwork, IBM Plex Sans, and a dark lock screen |
| Storage | Writable Btrfs root, systemd-boot, Snapper timeline and cleanup |
| Applications | Firefox, Flatpak with Flathub, InfinityLauncher, InfinityTerminal; Chrome DRM fallback on ARM64 |
| Development | Zsh with Oh My Zsh and a compact purple Powerlevel10k prompt, Iosevka Term in InfinityTerminal; GNOME Builder |
| Gaming | GameMode, MangoHud, Gamescope, gamepad support; Steam and Lutris on `x86_64` |
| Hardware | Fedora Intel and AMD graphics support; NVIDIA driver branch selected from the GPU's PCI ID during `x86_64` live installation |

## Performance defaults

Infinity OS uses compressed zram swap sized to half of RAM, capped at 16 GiB, with zstd compression. This follows Bazzite's desktop configuration and works with the writable Fedora image and normal DNF updates. The image also raises inotify limits for large game libraries and development projects and enables TCP path-MTU probing when a connection encounters a black hole. Nobara-inspired udev rules select `none` for NVMe, `mq-deadline` for SATA SSDs and eMMC, and `bfq` for rotating SATA disks. These rules apply only to whole disks; unsupported device types keep the kernel's choice.

GameMode, MangoHud, Gamescope, TLP, and the existing bounded `vm.max_map_count` setting remain in place. No OSTree or immutable root is used.

**InfinityLauncher** opens on first login. It groups optional software under AI, System, Gaming, Creative, Office, and Programming. You choose applications and press **Apply** before installation starts. The choices include Steam, Heroic, Lutris, Prism Launcher, creative tools, EuroOffice, OpenRazer, VS Code, Docker CE, Codex, Claude, and three local coding models. Selecting a local model installs Ollama and OpenCode, downloads the model, and configures the terminal agent. A progress strip appears while apps install. Its source and RPM specification live in [`packages/infinity-launcher`](packages/infinity-launcher).

Its footer can schedule one more launch at the next login. The interface follows the session language (Polish and English are bundled). RAMDrive warns through GNOME's shutdown confirmation when it contains files; canceling keeps the session and files, while continuing the shutdown clears the folder. A crash or hard reset leaves its contents intact.

**InfinityTerminal** uses a patched Ghostty renderer and defaults to Iosevka Term. Press **Super+T** or use its GNOME panel icon to show and hide it. The first shell tab stays pinned; Codex and Claude gain pinned tabs when their CLI tools are installed. A selected local model adds a leftmost Infinity AI tab; its context menu opens a separate edit-enabled agent tab. The terminal source and package live in [`packages/infinity-terminal`](packages/infinity-terminal), with the renderer patch in [`ghostty`](ghostty).

On `x86_64` live installations, Anaconda runs [`infinityos-install-nvidia`](root/usr/libexec/infinityos-install-nvidia) against the target machine's PCI ID. It keeps the current RPM Fusion branch for supported new GPUs, switches to the 580xx, 470xx, or 390xx branch for listed legacy GPUs, and removes the preloaded driver when no NVIDIA GPU is present. A failed legacy download is retried after boot when networking is available. NVIDIA's unsigned kernel modules still require Secure Boot to be disabled or their signing key to be enrolled.

GNOME starts with desktop icons, AppIndicator support, dynamic Blur My Shell, the Window Is Ready notification remover, and WACK Sonoma Lockscreen in Cupertino mode. WACK Shell adds the panel menu with a white Infinity logo. The signed `gnome-rounded-blur` helper fixes dynamic blur corners; its COPR repository is restricted to that package. Titlebars show minimize and maximize buttons. **Alt+Tab** switches windows. Firefox keeps **Ctrl+T** for a new tab. Location Services start enabled, and automatic problem reporting starts disabled.

**RAMDrive** keeps its files in a protected folder and offers a removable shortcut on the Desktop plus a bookmark in Files. Deleting the Desktop shortcut leaves the files and Files bookmark intact; the shortcut stays removed on later logins. Existing Desktop RAMDrive files move to protected storage on the first login after upgrading. The storage folder itself cannot be removed by a regular user. Its contents are deleted during an orderly shutdown or reboot. The folder uses disk storage so files remain recoverable after a crash or forced reset; it is not a `tmpfs` RAM disk.

## Packages and updates

Fedora and Fedora Updates provide the base system. RPM Fusion provides multimedia codecs and nonfree hardware packages. The desktop includes Bazaar as its Flatpak app store, Proview as the default PDF and image viewer, and InfinityUpdater for daily RPM and Flatpak update checks. It also includes FFmpeg, GNOME Files archive integration, UnRAR, 7-Zip, TLP, and purple folder icons. IBM Plex Sans is the default from the installer and login screen through the desktop. Microsoft Core Fonts are downloaded and checksum-verified on the installed machine after network access is available; their font files are not distributed in the image. Infinity OS builds `infinity-launcher` and `infinity-terminal` as signed RPMs and publishes them through its own DNF repository. See [`packages/README.md`](packages/README.md) for the build, signing, and release flow. Docker CE uses Docker's official Fedora repository when selected in InfinityLauncher.

Firefox enables Encrypted Media Extensions through an unlocked system policy and obtains supported Widevine modules from Mozilla/Google on compatible platforms. On ARM64, where Firefox's Linux Widevine distribution is still pending, a first-boot timer installs Google's native ARM64 Chrome from Flathub as a DRM-capable fallback. Firefox remains the default browser. Chrome and its Widevine component update through their normal upstream/Flatpak mechanisms; Infinity OS does not redistribute CDM binaries. PlayReady and FairPlay are not provided as general-purpose Linux desktop browser modules. Streaming services can impose their own browser, resolution, or hardware requirements.

The image build requires the Infinity OS RPM repository to be published and reachable. The GitLab pipeline publishes it after a successful build on `main`. Applications installed directly from third-party GitHub releases do not receive updates from the Infinity OS repository.

## Build an image

Use a Fedora 44 host with the target CPU architecture and Btrfs ACL support. Install KIWI and its system dependencies:

```sh
sudo dnf install kiwi kiwi-systemdeps distribution-gpg-keys
```

Commit all image and application changes first. Publish all six Infinity OS RPMs
from that same commit before starting an image build. The wrapper records the
commit in the image, uses a fresh archive of that commit as its KIWI description,
and stops if any installed Infinity OS RPM comes from another commit. It also
rejects uncommitted changes. Previously prepared KIWI roots are not release
inputs; `kiwi-ng system create` on an old root can reproduce old applications.

Build a Live ISO from the repository root:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=iso \
  --image-profile=Infinity-GNOME-Live --output-dir=/var/tmp/infinityos-iso
```

The wrapper checks the media checksum, embedded EROFS filesystem, source
revision, six RPM revisions, and essential desktop files before accepting an
Infinity OS ISO. Run `sudo scripts/verify-infinity-iso IMAGE.iso` again after
copying an image to another machine. An ISO from an old prepared root fails
this check.

Build a writable disk image:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=oem \
  --image-profile=Infinity-GNOME-Disk --output-dir=/var/tmp/infinityos-disk
```

The wrapper runs [`scripts/finalize-infinity-disk`](scripts/finalize-infinity-disk)
after an OEM build. That step checks the embedded revision and applications,
then fixes permissions on the Btrfs root subvolume so desktop services can
start. The resulting RAW disk has a 2 GB EFI partition and Btrfs `root`,
`home`, and `var` subvolumes. Apple Silicon Parallels runs the `aarch64` disk;
building `x86_64` requires an x86_64 Fedora host or CI runner.

The systemd-boot **Backups** entry opens a text console for listing, creating, deleting, and restoring Snapper snapshots of `/`. Snapshots are stored in the separate `infinityos-snapshots` Btrfs subvolume, so they remain available after a restore. The first boot sets this up and switches normal boot entries to the Btrfs default root; subsequent kernel entry changes refresh Backups automatically. A restore creates a safety snapshot of the current root, selects a writable copy of the chosen snapshot as the next default root, and reboots. `/home` and `/var` are separate subvolumes and are not rolled back. The previous root stays on disk under `infinityos-roots` for manual recovery.

## Project layout

- [`InfinityOS.kiwi`](InfinityOS.kiwi), [`repositories/`](repositories), and [`teams/`](teams) define image profiles and package sources.
- [`root/`](root) contains files placed in the image, including GNOME defaults, themes, extensions, and artwork.
- [`config.sh`](config.sh) applies image configuration and enables system services.
- [`packages/`](packages) contains the InfinityLauncher and InfinityTerminal RPMs.
- [`tests/`](tests) contains focused checks for application selection and RAMDrive cleanup.

## Sources and licensing

Infinity OS is based on Fedora's [KIWI descriptions](https://forge.fedoraproject.org/releng/kiwi-descriptions) from the `f44` branch. Project-authored and Fedora-derived build code follows GPL-3.0-or-later in [`LICENSE`](LICENSE); bundled software, fonts, icons, and artwork retain their own licenses. See [`THIRD_PARTY.md`](THIRD_PARTY.md) for component attribution. The image definition requests `generic-release`, `generic-logos`, and `generic-release-notes` in place of Fedora's identity packages; the finished image still needs a package-manifest check before publication. The [redistribution review](docs/REDISTRIBUTION.md) records the Fedora Remix, RPM Fusion, codec, NVIDIA, font, and Proview conditions relevant to a release from Poland.
