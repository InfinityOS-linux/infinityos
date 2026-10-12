# Infinity OS

Infinity OS is a Fedora 44 Workstation remix with a customized GNOME desktop. This repository contains its image definition. It is based on Fedora's [KIWI descriptions](https://forge.fedoraproject.org/releng/kiwi-descriptions), branch `f44`.

The Infinity OS image profiles use Fedora's `generic-release` and `generic-logos` packages in place of Fedora's trademarked release and logo packages. Fedora and RPM Fusion remain the package sources. The visible system identity, wallpaper, icon and Plymouth startup screen use Infinity OS branding, with `#645394` as the base color. GNOME's built-in `purple` accent is the closest available system accent; the exact hex value is used in the artwork.

GNOME Initial Setup uses the Infinity OS welcome illustration through a GResource overlay scoped to its systemd user services. Check the resource path when upgrading GNOME Initial Setup.

## Included in the image

- Firefox as the default browser, GNOME Builder, and GNOME Extensions; GNOME Tour is omitted in favor of Infinity Launcher.
- Blur My Shell, Window Is Ready - Notification Remover, AppIndicator, and Desktop Icons NG (DING), enabled for new users. DING allows files and folders on the desktop.
- Flathub as a system-wide Flatpak remote, with GNOME Software support for Flatpak apps.
- Minimize and maximize titlebar buttons; Alt+Tab switches windows rather than applications.
- GhosTTY opens or hides with Super+T, leaving Ctrl+T available for a new Firefox tab.
- GhosTTY uses a patched Ghostty renderer, a GNOME Shell panel button, and a persistent user service. Codex and Claude CLI tabs appear when their commands are installed; the first shell tab stays pinned.
- Infinity Launcher starts on first login with System, Gaming, Creative, Programming, and AI tabs; selections install only after Save.
- The disk image uses systemd-boot, a writable Btrfs root, and automatic Snapper timelines and cleanup.
- Orchis Purple Dark Compact as the default GTK and GNOME Shell theme, Kora icons, Bibata Modern Ice cursors, a compact Shell panel, and macOS-style window buttons on the left.
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

Before building the image, run `ghostty/build-and-stage.sh DESCRIPTION_DIR` to compile the patched Ghostty 1.3.1 for the target architecture and stage its binary and resources in a copy of this KIWI description. Set `INFINITY_TARGET_PLATFORM=linux/arm64` or `linux/amd64` when building on a different host architecture. Keep the staged binary architecture the same as the image architecture.

Build the disk from that staged description on a Fedora host with Btrfs ACL support, using a local build target:

```sh
sudo kiwi-ng --type=oem --profile=Infinity-GNOME-Disk --kiwi-file=InfinityOS.kiwi system build --description /path/to/staged-description --target-dir /var/tmp/infinityos-build
sudo ./scripts/finalize-infinity-disk /var/tmp/infinityos-build/InfinityOS.aarch64-44.raw
```

Change the RAW filename to the output for the target architecture. The finalizer corrects KIWI's `0700` root subvolume permissions to `0755`; without this, non-root system services fail at boot. The `kiwi-build` wrapper runs it automatically for `Infinity-GNOME-Disk`. Docker Desktop's LinuxKit kernel lacks Btrfs ACL support, so it cannot finish this disk profile correctly. The Fedora ARM Builder VM on Apple Silicon can build it. A future `x86_64` build uses the same staged description and command on an `x86_64` Fedora host or CI runner.

The ARM disk image is at `PRO STORAGE/InfinityOS/build/InfinityOS.aarch64-44-next.raw`, with a compressed `.raw.zst` beside it. It has a 2 GB EFI partition and a writable Btrfs partition with `root`, `home`, and `var` subvolumes. The GPT passed `sgdisk -v`. The current Live ISO predates the disk changes and needs a later rebuild before distribution.

The `Infinity OS 44 ARM` Parallels VM boots from `PRO STORAGE/InfinityOS/build/parallels/InfinityOS-44-arm.hdd` into a regular GNOME session. The disk is a writable plain Parallels image. Infinity Launcher and GhosTTY run in the development VM; GhosTTY's outside-click behavior still needs an input test because Parallels did not forward automated clicks to the guest. `config.sh` requests a generic initramfs so the VM can find its root partition in Parallels.

The `/etc/os-release` identity is currently installed by `config.sh` over `generic-release`; a dedicated `infinityos-release` RPM is needed before publishing so future `generic-release` upgrades cannot restore the generic identity. Further desktop changes should be made in this repository and tested in the development VM, then included in a new image build after the planned changes are complete.

## Sources and licensing

This repository follows the upstream Fedora KIWI description's GPL-3.0-or-later license in [COPYING](COPYING). Bundled Oh My Zsh, Orchis and the Window Is Ready extension have their own licenses and pinned source details in [THIRD_PARTY.md](THIRD_PARTY.md). Before distributing an ISO, review the [Fedora Remix guidelines](https://fedoraproject.org/wiki/Remix) and the terms for RPM Fusion and NVIDIA packages.
