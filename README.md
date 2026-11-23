# Infinity OS

<img src="assets/infinityos-logo.svg" width="112" alt="Infinity OS logo">

**Infinity OS is an independent Fedora Remix built for a polished, personal desktop.** Infinity OS pairs a writable GNOME system with a distinctive purple design, a fast drop-down terminal, a first-run application chooser, and integrated updates. It uses Fedora's familiar DNF package model, so the desktop remains easy to customize and maintain.

This repository is the source for the Infinity OS KIWI images, desktop configuration, InfinityApps, InfinityTerminal, InfinityUpdater, RPM packages, and build pipeline.

**Infinity OS 2.0** uses Fedora 45 and GNOME 51, with live ISO images for `x86_64` and `aarch64`. Visit the [download page](https://infinityos.eu/download) for published images, checksums, and installation instructions, and [News](https://infinityos.eu/news) for release changes.

**Infinity OS is an independent Fedora Remix. It is not provided, supported, or endorsed by the Fedora Project or Red Hat.** Official Fedora Linux is available at [fedoraproject.org](https://fedoraproject.org/).

## Start here

- [Download Infinity OS 2.0](https://infinityos.eu/download).
- [Join the InfinityOS Discord community](https://discord.gg/QA8N3XKsH8) for help, ideas, and release discussion.
- [Build an image](#build-an-image) from a committed source revision.
- [Package and RPM repository guide](packages/README.md) for application builds and signing.
- [Third-party components](THIRD_PARTY.md) and [redistribution review](docs/REDISTRIBUTION.md) for sources, font licenses, codecs, and driver obligations.
- [Contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md).

## What ships

| Area | Configuration |
| --- | --- |
| Base | Fedora 45 packages, DNF, Fedora Updates, RPM Fusion Free and Nonfree |
| Desktop | GNOME 51 with Orchis Purple Dark Compact by default and an optional Light mode, Kora icons, a Bibata-based cursor theme with Infinity OS hand cursors, Infinity OS artwork, IBM Plex Sans, and a dark lock screen |
| Storage | Writable Btrfs root, rEFInd, and offline Snapper recovery points covering the system and `/var` |
| Applications | Firefox, GNOME Software, Flatpak with Flathub, mpv, Proview, InfinityApps, InfinityConfig, InfinityUpdater, and InfinityTerminal |
| Development | Zsh with Oh My Zsh and a compact purple Powerlevel10k prompt, Iosevka Term in InfinityTerminal |
| Gaming | GameMode, MangoHud, Gamescope, gamepad support; Steam and Lutris available through InfinityApps |
| Hardware | Fedora Intel and AMD graphics support; NVIDIA driver branch selected from the GPU's PCI ID during `x86_64` live installation |

## Performance defaults

Infinity OS uses compressed zram swap sized to half of RAM, capped at 16 GiB, with zstd compression. This follows Bazzite's desktop configuration and works with the writable Fedora image and normal DNF updates. The image also raises inotify limits for large game libraries and development projects and enables TCP path-MTU probing when a connection encounters a black hole. Nobara-inspired udev rules select `none` for NVMe, `mq-deadline` for SATA SSDs and eMMC, and `bfq` for rotating SATA disks. These rules apply only to whole disks; unsupported device types keep the kernel's choice.

GameMode, MangoHud, Gamescope, TLP, and the existing bounded `vm.max_map_count` setting remain in place. No OSTree or immutable root is used.

**InfinityApps** opens on first login. It groups optional software under AI, System, Gaming, Creative, Office, and Programming. You choose applications and press **Apply** before installation starts. The choices include Steam, Epic Games Launcher Preview, Heroic, Lutris, Prism Launcher, creative tools, EuroOffice, OpenRazer, VS Code, Docker CE, Codex, Claude, and three local coding models. On x86_64, Epic's native Linux launcher is downloaded from Epic's Debian package and extracted into the user's application directory. The Battle.net row opens its interactive installer in Lutris. Selecting a local model installs Ollama and OpenCode, downloads the model, and configures the terminal agent. A progress strip appears while apps install. Its source and RPM specification live in [`packages/infinity-setup`](packages/infinity-setup).
On ARM64, the Steam choice installs Valve's native public beta client; game compatibility depends on the machine's graphics stack and any needed FEX or Proton setup.
Steam TV Mode reserves tty1 exclusively, including on systems using KMSCon, and drops inherited PAM capabilities before starting its session bus and compositor. Seat access uses systemd-logind. On x86_64, Steam uses RPM Fusion's native RPM with 64-bit and 32-bit graphics libraries; see [Steam packaging](#steam-packaging). The first Steam launch may take longer while the client downloads and installs its updates.

**InfinityConfig** opens from the application grid when needed. Its Design tab lets you resize the cursor and dock from 20% to 200%, with the shipped sizes at 100%. You can also set natural scrolling independently for the mouse and touchpad. Tweaks opens system tools and diagnostics. The AI, Gaming, and Backups pages manage their respective settings. It uses the same visual language as InfinityApps and is packaged in [`packages/infinity-config`](packages/infinity-config).

InfinityApps opens automatically once after installation; after you close it, you can reopen it from the application grid. The interface follows the session language (Polish and English are bundled). If RAMDrive contains files, GNOME's restart confirmation appears in the upper-right corner with **Remove & Restart** and **Save files**. Saving moves the files to **Saved Files** on the Desktop before restarting; a failure stops the restart. Escape cancels before an operation starts. A crash or hard reset leaves RAMDrive contents intact. See [RAMDrive restart choices](docs/ramdrive-restart.md).

**InfinityTerminal** uses a patched Ghostty renderer and defaults to Iosevka Term. Press **Super+T**, click the handle below the clock, or drag the handle to reveal it. It also opens from the application grid. The configurable strip above the terminal offers hardware readings and widgets such as weather, timers, network traffic, and world clocks. The first shell tab stays pinned; Codex and Claude gain pinned tabs when their CLI tools are installed. A selected local model adds a leftmost Infinity AI tab; its context menu opens a separate edit-enabled agent tab. The terminal source and package live in [`packages/infinity-terminal`](packages/infinity-terminal), with the renderer patch in [`ghostty`](ghostty).

At the Zsh prompt, **Shift+Arrow** selects command text, **Ctrl+Shift+Left/Right** selects whole words, and typing, pasting, or Backspace replaces the selection. **Alt+C** copies it to the system clipboard; **Alt+Up/Down** searches command history by the prefix already typed. Ghostty also provides **Ctrl+Shift+F** for scrollback search, **Ctrl+Shift+P** for its command palette, and **Ctrl+Shift+Page Up/Down** to jump between prompts. In terminal output, select text with the pointer first, then Shift+Arrow extends that selection.

On `x86_64` live installations, Anaconda runs [`infinityos-install-nvidia`](root/usr/libexec/infinityos-install-nvidia) against the target machine's PCI ID. The live image does not preload the proprietary driver or its settings app. On a compatible NVIDIA machine, the installer adds the current RPM Fusion driver or the matching 580xx, 470xx, or 390xx legacy branch to the installed system. On Intel and AMD machines it installs none of them. Before installation succeeds, the installer builds and verifies NVIDIA modules for every installed kernel, rebuilds its initramfs, and refreshes the copy used by rEFInd. A failed download or module build stops installation with an error instead of deferring driver setup to the first graphical session. Compatible NVIDIA installations require network access for the driver and matching kernel development files. NVIDIA's unsigned kernel modules still require Secure Boot to be disabled or their signing key to be enrolled.

GNOME starts with desktop icons, AppIndicator support, dynamic Blur My Shell, and the Window Is Ready notification remover. Locking the session uses the native GNOME lock screen. WACK Shell puts the Infinity logo on the panel's overview button. The signed `gnome-rounded-blur` helper fixes dynamic blur corners; its COPR repository is restricted to that package. Titlebars show minimize and maximize buttons. **Alt+Tab** switches windows. Firefox keeps **Ctrl+T** for a new tab. Location Services start enabled, and automatic problem reporting starts disabled.

The desktop extensions and their default settings ship in the signed `infinityos-shell-extensions` RPM. Its source includes Infinity OS modifications and pinned Fedora 45 snapshots for GPaste, AppIndicator Support, Blur My Shell, User Themes, and V-Shell, plus a GNOME 51 compatible Caffeine release. Fedora package updates cannot replace those extension files independently; Infinity OS updates them together after compatibility checks. InfinityUpdater detects and installs newer signed extension RPMs through the normal system update flow; log out and back in to load the new extension code. User overrides in dconf remain possible.

The extension RPM pins the tested GNOME Shell major version, and GitHub's RPM workflow checks every enabled extension's metadata before publishing. If an extension prevents the desktop from loading, log in on a text console and run `infinityos-shell-recover --list`, then `infinityos-shell-recover --disable UUID`. `--disable-all` provides a minimal session; `--restore-defaults` restores the packaged selection. Run these commands as the affected user, without sudo.

Infinity Config's Tweaks tab opens Extensions, system settings and Updates. It can save a private diagnostic JSON report under `~/.local/state/infinityos/diagnostics/`; the report contains package versions, GNOME and backup state, but no logs, hostname, network identifiers or account names. It lists enabled packaged extensions and only a count of other extensions. The full boot audit in `docs/installation-smoke-test.md` requires sudo.

**RAMDrive** keeps its files in a protected folder and offers a removable shortcut on the Desktop plus a bookmark in Files. Deleting the Desktop shortcut leaves the files and Files bookmark intact; the shortcut stays removed on later logins. Existing Desktop RAMDrive files move to protected storage on the first login after upgrading. The storage folder itself cannot be removed by a regular user. Its contents are deleted during an orderly shutdown or reboot. The folder uses disk storage so files remain recoverable after a crash or forced reset; it is not a `tmpfs` RAM disk.

## Packages and updates

InfinityUpdater downloads system RPM updates during the desktop session and installs the prepared transaction after restart, before ordinary services start. Immediately before installation, it requires a complete Snapper recovery point covering the system and `/var`. If backup creation fails, installation does not start. The rEFInd **Backups** entry creates and restores these recovery points; InfinityConfig lists and deletes them. `/home`, the EFI system partition, and device firmware are outside the backup. See [Recovery](docs/recovery.md) for the supported layout and restore process.

Packages explicitly skipped by DNF because of dependency compatibility appear in a separate **Waiting for compatibility** group. They are excluded from the available-update count until they become installable. Failed repository downloads receive one metadata refresh and retry; failures remain visible and preserve the existing pending update. See [Updater recovery](docs/updater-recovery.md) for manual recovery commands.

Fedora and Fedora Updates provide the base system. RPM Fusion provides multimedia codecs and nonfree hardware packages. The desktop includes GNOME Software for applications, mpv as the default video player, Proview as the default PDF and image viewer, and InfinityUpdater for periodic RPM and Flatpak update checks. GNOME Software's own update checks are disabled to avoid duplicate notifications. It also includes FFmpeg, GNOME Files archive integration, UnRAR, 7-Zip, TLP, and purple folder icons. IBM Plex Sans is the default from the installer and login screen through the desktop. Microsoft Core Fonts are downloaded and checksum-verified on the installed machine after network access is available; their font files are not distributed in the image. Infinity OS builds `infinity-setup` and `infinity-terminal` as signed RPMs and publishes them through its own DNF repository. See [`packages/README.md`](packages/README.md) for the build, signing, and release flow. Docker CE uses Docker's official Fedora repository when selected in InfinityApps.

Firefox enables Encrypted Media Extensions through an unlocked system policy and obtains supported Widevine modules from Mozilla/Google on compatible platforms. Firefox remains the default browser. Chrome is available as an optional InfinityApps selection and is not installed automatically. Infinity OS does not redistribute CDM binaries. PlayReady and FairPlay are not provided as general-purpose Linux desktop browser modules. Streaming services can impose their own browser, resolution, or hardware requirements.

The image build requires the Infinity OS RPM repository to be published and reachable. GitHub Actions publishes it after a successful build on `main`. Third-party GitHub applications are not republished in the Infinity OS RPM repository. InfinityUpdater separately checks supported GitHub RPM and AppImage applications installed through InfinityApps, alongside RPM, Flatpak, and firmware updates.

## Build an image

Run the [Infinity OS versus Fedora regression gates](docs/infinityos-delta-tests.md)
after source changes and after each new ISO build.

Use a Fedora 45 host with the target CPU architecture and Btrfs ACL support. Install KIWI and its system dependencies:

```sh
sudo dnf install kiwi kiwi-systemdeps distribution-gpg-keys erofs-utils dosfstools xorriso isomd5sum bsdtar
```

Commit all image and application changes first. Publish all eight Infinity OS RPMs
from that same commit before starting an image build. The wrapper records the
commit in the image, uses a fresh archive of that commit as its KIWI description,
and stops if any installed Infinity OS RPM comes from another commit. It also
rejects uncommitted changes. Previously prepared KIWI roots are not release
inputs; `kiwi-ng system create` on an old root can reproduce old applications.

Each build resolves the latest stable Proview and Iosevka releases, requires upstream SHA-256 digests, and stages their matching license files. Exact versions, download URLs, and checksums are recorded inside the image at `/usr/share/infinityos/upstream-versions.json`. Resolution failure stops the build instead of falling back to an older release.

Build a Live ISO from the repository root:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=iso \
  --image-profile=Infinity-GNOME-Live --output-dir=/var/tmp/infinityos-iso
```

The wrapper checks the media checksum, embedded EROFS filesystem, source
revision, eight RPM revisions, and essential desktop files before accepting an
Infinity OS ISO. Run `sudo scripts/verify-infinity-iso IMAGE.iso` again after
copying an image to another machine. An ISO from an old prepared root fails
this check. On Fedora 45 the wrapper also prepares a fresh bootstrap root with
Fedora DNF before KIWI installs the rest of the live image, so RPM `sysusers`
hooks have their interpreter available. It also stages the Fedora, RPM Fusion,
Infinity OS, and COPR signing keys before KIWI validates package repositories.
An existing output directory is refused.

Build a writable disk image:

```sh
sudo ./kiwi-build --kiwi-file=InfinityOS.kiwi --image-type=oem \
  --image-profile=Infinity-GNOME-Disk --output-dir=/var/tmp/infinityos-disk
```

The wrapper runs [`scripts/finalize-infinity-disk`](scripts/finalize-infinity-disk)
after an OEM build. KIWI uses its `custom` bootloader mode and does not install
systemd-boot in the disk image. The finalizer checks the embedded revision and applications,
then installs rEFInd, writes the Btrfs recovery entry, and fixes permissions
on the Btrfs root subvolume so desktop services can start. The resulting RAW disk has a 2 GB EFI partition and Btrfs `root`,
`home`, and `var` subvolumes. Building `x86_64` requires an x86_64 Fedora host or CI runner.

The rEFInd **Backups (Btrfs)** entry opens a text console for listing, creating, deleting, and restoring complete system recovery points. Snapshots are stored in the separate `infinityos-snapshots` Btrfs subvolume, so they remain available after a restore. The first boot sets this up and switches normal boot entries to the Btrfs default root; subsequent kernel entry changes refresh Backups automatically. A restore first saves the current system and `/var`, prepares writable copies of the selected recovery point, and switches the default root and its matching `/var`. `/home` is preserved. Older root-only or incomplete backups cannot be selected. Previous roots and service data remain on disk for recovery.

Published x86_64 and aarch64 live ISOs boot through rEFInd. The ISO finalizer enlarges the EFI partition and places the live kernel and initramfs there, avoiding firmware-dependent ISO9660 loading. The menu offers the live session, media check, and basic graphics mode. KIWI uses GRUB while composing the ISO, but the published EFI image contains rEFInd. Anaconda creates kernel metadata with `bootloader --location=none`; the required post script installs rEFInd before reporting success. The installed system boots through rEFInd with Infinity OS and Backups (Btrfs) entries. Unused GRUB EFI, shim, and systemd-boot packages are removed from installed systems. Fedora still requires `grub2-common` and `grub2-tools` for Anaconda and `grubby`, so those packages remain in the live root and installed system. The target root must be Btrfs. The shipped rEFInd binary is unsigned, so disable Secure Boot before installation. Legacy BIOS boot is not supported. An installer failure leaves its log at `/var/log/infinityos-boot-install.log` on the target system.

## Project layout

- [`InfinityOS.kiwi`](InfinityOS.kiwi), [`repositories/`](repositories), and [`teams/`](teams) define image profiles and package sources.
- [`root/`](root) contains files placed in the image, including GNOME defaults, themes, extensions, and artwork.
- [`config.sh`](config.sh) applies image configuration and enables system services.
- [`packages/`](packages) contains the Infinity OS application, repository, wallpaper, RAMDrive, and desktop extension RPMs.
- [`tests/`](tests) contains source, application, native GNOME, GTK, package compatibility, ISO, and Btrfs recovery checks.

## Sources and licensing

Infinity OS is based on Fedora's [KIWI descriptions](https://forge.fedoraproject.org/releng/kiwi-descriptions) from the `f44` branch, ported to Fedora 45 in this branch. Project-authored and Fedora-derived build code follows GPL-3.0-or-later in [`LICENSE`](LICENSE); bundled software, fonts, icons, and artwork retain their own licenses. See [`THIRD_PARTY.md`](THIRD_PARTY.md) for component attribution. The image definition requests `generic-release`, `generic-logos`, and `generic-release-notes` in place of Fedora's identity packages. Review the finished image's package manifest for each new release. The [redistribution review](docs/REDISTRIBUTION.md) records the Fedora Remix, RPM Fusion, codec, NVIDIA, font, and Proview conditions relevant to a release from Poland.

### Steam packaging

InfinityApps installs Steam from RPM Fusion on x86_64, together with 32-bit and
64-bit Mesa DRI, Vulkan Freeworld and VA-API Freeworld libraries. If an RPM Fusion
NVIDIA driver is installed, its matching 32-bit libraries are installed too.
Steam TV Mode starts the same native client in Gamescope. ARM64 retains the
separate Valve ARM client. Proton versions managed by InfinityConfig are already
installed into the native Steam compatibility-tools directory.

When installing the RPM, Setup removes an existing Steam Flatpak only after the
RPM installation succeeds. It does not migrate Flatpak games or settings.
