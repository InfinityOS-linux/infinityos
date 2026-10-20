# Fresh-install smoke test

An ISO content check does not prove that Anaconda ran its post-install script.
Test each release on a **new** UEFI VM with a blank virtual disk. Do not reuse
an installed Infinity OS disk: it can hide a broken installer.

1. Record the ISO path, SHA-256 and source revision. Run
   `scripts/verify-infinity-iso IMAGE.iso REVISION` on a Linux builder.
2. Boot the ISO, choose the entire blank virtual disk in the graphical
   installer, complete installation, and reboot without the ISO attached.
3. Confirm the systemd-boot menu offers Infinity OS and Backups, then log in.
4. Run `sudo /usr/libexec/infinityos-audit-install` in the installed system.
   Every line must be `PASS` and the command must exit 0. Save its output and
   `/var/log/infinityos-boot-install.log` with the release evidence.
5. Open Infinity Config, Launcher, Terminal and Updater; check the wallpaper,
   dock and enabled desktop extensions. Perform one reboot from the installed
   system and run the audit again.

Record ARM and x86_64 results independently. A successful ARM VM install does
not validate x86_64 hardware, NVIDIA detection or firmware updates.
