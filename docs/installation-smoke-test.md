# Fresh-install smoke test

An ISO content check does not prove that Anaconda ran its post-install script.
Test each release on a **new** UEFI VM with a blank virtual disk. Do not reuse
an installed Infinity OS disk: it can hide a broken installer.

1. Record the ISO path, SHA-256 and source revision. Run
   `scripts/verify-infinity-iso IMAGE.iso REVISION` on a Linux builder.
2. Confirm the ISO opens the themed rEFInd menu, start the live session, then choose the entire blank virtual disk in the graphical
   installer, complete installation, and reboot without the ISO attached.
3. Confirm the rEFInd menu offers Infinity OS and Backups (Btrfs), then log in.
4. Run `sudo /usr/libexec/infinityos-audit-install` in the installed system.
   Every line must be `PASS` and the command must exit 0. Save its output and
   `/var/log/infinityos-boot-install.log` with the release evidence.
5. Open Infinity Config, Launcher, Terminal and Updater; check the wallpaper,
   dock and enabled desktop extensions. Perform one reboot from the installed
   system and run the audit again.

Record ARM and x86_64 results independently. A successful ARM VM install does
not validate x86_64 hardware, NVIDIA detection or firmware updates.

## 2026-10-20 ARM result

- Image: `InfinityOS-44-aarch64-3a68997.iso`, source revision `3a68997`,
  SHA-256 `1121c4cd54be1da419a3cdaec4fa83832775f695fe7803f14c7d47c6965a3633`.
- Test machine: a new Parallels ARM64 UEFI VM, 6 vCPUs, 8 GiB RAM, blank 40 GiB
  virtual disk, Secure Boot off. The installer completed on that disk. The
  installed system booted from the disk twice with the ISO disconnected.
- After the second boot, the current audit returned **14 PASS, 0 FAIL**. The
  image predates the audit change below, so the revised script was copied to
  `/tmp/infinityos-audit-install` and run with `sudo bash` in the installed VM.
  This checks the installed state but does not prove that the revised audit is
  already included in that ISO.
- `bootctl status` reported `systemd-boot 259.9-1.fc44` loaded from
  `/EFI/BOOT/BOOTAA64.EFI` and current entry
  `infinityos-7.2.11-200.fc44.aarch64.conf`. Parallels retained only its
  generic hard-disk NVRAM boot option after reboot. The audit therefore checks
  the active loader and selected entry from `bootctl`, rather than requiring a
  named `BootCurrent` option from `efibootmgr`.
- The wallpaper, dock, first-run Launcher, Infinity Config and Updater were
  visible. The bundled Terminal extension hid a later `gtk-launch` window.
  After copying the revised `extension.js` into the installed VM and restarting
  its graphical session, the initial terminal stayed hidden and a later
  `gtk-launch com.infinityos.GhosTTY` opened a visible window. The revised
  extension is a source fix tested in this VM; it is not present in the tested
  ISO.

**x86_64:** no fresh installation was run. Source and image checks do not
substitute for an installed x86_64 boot, NVIDIA or firmware test.

The [GitHub RPM publication run](https://github.com/InfinityOS-linux/infinityos/actions/runs/39394060346)
for source commit `f7d6f61` completed successfully, including both Terminal
architectures, package signing and Pages deployment. This published the source
fixes as RPMs; it did not rebuild the tested ISO.
