# Fedora 45 / GNOME 51 migration inventory

Source branch: `fedora-45-gnome-51`, forked from `main` at `45a5880`.
Target: Infinity OS 2.0 for `aarch64` and `x86_64`.
This is a development checklist. Source checks do not establish that an ISO boots or installs.

| Area | Features to preserve | Source or check | Status |
| --- | --- | --- | --- |
| Base and repositories | Fedora 45, DNF5, Fedora Updates, RPM Fusion Free/Nonfree, signed Infinity OS RPM repository, restricted rounded-blur COPR, Docker CE when selected | `InfinityOS.kiwi`, `repositories/`, `packages/infinityos-repos/` | Source moved; signed Fedora 45 Infinity OS repository absent |
| Image formats | ARM64 and x86_64 live ISO, writable OEM disk, EFI media check and basic graphics entry, image provenance checks | `kiwi-build`, `scripts/finalize-infinity-*`, `scripts/verify-infinity-iso` | Source moved; image build pending |
| Installation | Branded welcome and Web UI, Btrfs target and compression, rEFInd installation, NVIDIA PCI detection on x86_64, post-install audit | `config.sh`, `root/usr/libexec/infinityos-liveinstall-boot-setup`, `root/usr/libexec/infinityos-install-nvidia` | Source moved; fresh VM install pending |
| Boot and recovery | rEFInd theme and entries, kernel updates to ESP, Snapper root snapshots, Btrfs backup menu and restore | `root/usr/libexec/infinityos-refind-*`, `root/usr/libexec/infinityos-backups-*` | Unit checks pass; boot and restore pending |
| GNOME desktop | GNOME 51, GDM, dark/light Orchis, Kora icons, Bibata cursor, IBM Plex and Iosevka fonts, wallpapers, purple folder icons, branded Settings and lock screen | `root/usr/share/infinityos/`, `root/etc/dconf/`, `root/etc/environment.d/` | GNOME 51.1 templates ported; visual VM check pending |
| GNOME extensions | DING desktop icons, animated dock, V-Shell, Blur My Shell, AppIndicator, Caffeine, GPaste, User Themes, Tiling Shell, WACK Shell and lock screen, Window Is Ready Remover, Terminal and Updater panel integrations | `root/usr/share/gnome-shell/extensions/`, `vendor/gnome-shell/fedora-45/`, `scripts/verify-gnome-extension-contracts` | 14 enabled UUIDs pass metadata contract and the RPM builds; live Shell check pending |
| InfinitySetup | First run, Polish/English UI, AI/System/Gaming/Creative/Office/Programming choices, Steam on ARM, Epic AppImage, Heroic, Lutris/Battle.net, Prism, Ollama/OpenCode models, VS Code, Docker, Codex and Claude | `packages/infinity-setup/`, `tests/test_launcher_backend.py` | Source and unit checks pass; install choices pending |
| InfinityTerminal | Ghostty renderer, dropdown and Super+T, pinned shell/AI/CLI tabs, prompt editing shortcuts, resize and panel control | `packages/infinity-terminal/`, `ghostty/`, `tests/terminal-resize.test.mjs` | Source and unit checks pass; Fedora 45 RPMs build on ARM64 and x86_64; live session pending |
| Infinity Config | Cursor and dock size, Settings/Extensions/Updater shortcuts, private diagnostics | `packages/infinity-config/`, `tests/test_config_*.py` | Unit checks pass; live UI pending |
| InfinityUpdater | RPM and Flatpak updates, fwupd, pre-upgrade Btrfs snapshot, release signature verification and guarded base upgrade | `packages/infinity-updater/`, `tests/test_updater.py` | Unit checks pass; real transactions pending |
| RAMDrive | Protected storage, Desktop shortcut and Files bookmark, shutdown warning, orderly cleanup, crash retention | `packages/infinityos-ramdrive/`, `tests/test_ramdrive.py` | Unit checks pass; session and reboot pending |
| Media, gaming and hardware | Firefox/Widevine policy, GNOME Software, mpv, Proview, codecs, archive tools, GameMode, MangoHud, Gamescope NVIDIA fix, gamepads, TLP, graphics firmware | `teams/workstation.xml`, `packages/gamescope/`, `root/` | Package resolution and hardware checks pending |
| Performance defaults | zram/zstd, inotify limits, path-MTU probing, storage schedulers, map count | `root/usr/share/infinityos/performance/`, `config.sh` | Source preserved; runtime values pending |

## Verification still required before release

- [x] Run existing Python and Node behavior tests on the migration branch.
- [x] Check GNOME 51 extension metadata and compare current Settings templates with GNOME Control Center 51.1.
- [x] Build all eight source-stamped Fedora 45 RPMs on both target architectures and the x86_64 Gamescope RPM. The branch workflow builds without publishing.
- [ ] Publish a signed Fedora 45 RPM repository without replacing the Fedora 44 channel.
- [ ] Build and verify the ARM64 ISO from the exact RPM source commit.
- [ ] Boot and install the ARM64 ISO in a new UEFI VM; run `infinityos-audit-install`, exercise every desktop extension and core app, reboot, test snapshots and restore.
- [ ] Repeat install and NVIDIA/Gamescope checks on x86_64 hardware or VM.
- [ ] Copy the verified ARM64 ISO to the Desktop and verify its checksum there.

Fedora 44 to 45 is a base upgrade. InfinityUpdater currently blocks this change during a running session; installed 1.0 systems need a separately validated migration procedure or a fresh 2.0 installation.
