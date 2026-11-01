# Quick regression checks: Infinity OS versus Fedora

Use these three gates after changing an Infinity OS feature. They test the parts
added to or changed from Fedora; they do not rebuild Fedora's own test suite.
Run each gate on the new source revision, not on a prepared root from an older
build. A green source gate does not prove that an ISO boots.

| Gate | Command | Where | Typical use |
| --- | --- | --- | --- |
| Source | `scripts/test-infinity-delta source` | Checkout with Python 3 and Node | After each change; about 7 seconds locally |
| Built ISO | `sudo scripts/test-infinity-delta iso IMAGE.iso REVISION` | Fedora Linux on the ISO's CPU architecture | After every new ISO; checks checksum, rEFInd, EROFS, SELinux, package provenance and branded files |
| Installed VM | `sudo /usr/libexec/infinityos-audit-install`, then `/usr/libexec/infinityos-audit-desktop` without sudo | Freshly installed UEFI VM, logged into GNOME | After each image build; checks installed boot and live desktop state |

The source gate runs all Python tests, **all** Node tests and the GNOME
extension contract check. CI uses this same command. The ISO gate delegates to
the existing `verify-infinity-iso` and requires root for read-only loop mounts.
Pass the full Git commit as `REVISION` when checking an image from another
checkout. The installed desktop audit needs a fresh default user session: it
checks GNOME 51, all 14 enabled extensions, the 13 expected to be active in a
normal session, and RAMDrive's protected folder, Desktop link and Files bookmark.
WACK Lockscreen is enabled but is expected to run only on the unlock screen.

## What the gates cover

| Infinity OS change versus Fedora | Source gate | ISO gate | Installed VM / visual check |
| --- | --- | --- | --- |
| Identity, signed RPM sources and exact build revision | release and provenance tests | OS identity, eight RPM stamps, package manifest | `systemctl status infinityos-repo-trust.service`; refresh the signed repo before release |
| Branded Anaconda WebUI, Polish strings, music and Btrfs installation | installer and live boot tests, including audio | bundled WebUI assets and required `%post` conversion | Install on a **blank** disk; inspect welcome and success screens, then reboot |
| rEFInd live menu, installed EFI boot and Backups entry | boot, rEFInd and Btrfs tests | live EFI partition, media check, kernel and initramfs | Boot from disk; run installed audit; open Backups and test restore in a disposable VM |
| GNOME 51 look: wallpaper, themes, icons, fonts and Settings overlays | GNOME overlay, theme and contract tests | installed assets, defaults and extension metadata | Log in, switch light/dark, open Settings and lock screen |
| 14 bundled extensions, animated dock and panel buttons | extension contract and Node behavior tests | metadata and default enablement | Desktop audit, then use DING, dock, Terminal/Updater buttons and lock screen |
| InfinitySetup, Config, Terminal, Updater and TV modes | launcher, config, terminal, updater and TV unit tests | RPM presence and revision | Open each app; change and restore dock size; check ARM/x86 option gating |
| RAMDrive and Snapper recovery | RAMDrive and backup tests | service files and installed audit | Desktop audit; create/clear a RAMDrive file and create a Snapper snapshot |
| Gaming, NVIDIA and performance defaults | NVIDIA selection and source tests | package presence and hooks | x86_64 GPU/VM test, zram and Btrfs compression checks |

## Ten-minute VM pass after a new ISO

1. Create a **new** UEFI VM with a blank disk. Boot the ISO through its rEFInd
   menu, then install to the whole disk. Check the Polish completion text and
   both visible buttons. Remove the ISO for the first disk boot.
2. Confirm the installed rEFInd menu has **Infinity OS** and **Backups (Btrfs)**.
   Log in and run both installed audits above. Every check must be `PASS`; both
   commands must exit 0. Save the output with the ISO checksum and revision.
3. Open InfinitySetup, Infinity Config, InfinityTerminal and InfinityUpdater.
   Check the wallpaper, desktop icons, dock and custom lock screen. Change a
   dock setting and restore it. Create then clear a disposable RAMDrive file.
   Create a Snapper snapshot and confirm it appears in the Backups menu.
4. Reboot once from the installed system and run the audits again. On a
   disposable VM, restore the snapshot and check that the system still boots.
5. Before a stable release, verify the public signed Infinity OS repository
   with `sudo dnf --refresh makecache --repo infinityos`. A preview built from
   local unsigned RPMs cannot satisfy this release gate.

When InfinitySetup's installer code changes, test one option for every changed
installation method (Flatpak, DNF, GitHub RPM, AppImage, npm or local model) in
a disposable VM; the quick pass does not install all 63 choices. Test NVIDIA,
Gamescope, hardware firmware and the x86_64 installer on that architecture.
Record these outcomes separately from ARM. The longer fresh-install procedure
is in [installation-smoke-test.md](installation-smoke-test.md).
