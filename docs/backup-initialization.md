# Backup initialization after installation

InfinityUpdater requires an installed Btrfs root, a Snapper root configuration,
a completed backup-setup marker and mounted `/.snapshots` before preparing RPM
updates. These checks do not create backups or change boot configuration on a
user's behalf. The offline updater still creates the complete recovery backup
before installing RPMs.

## Installation and presets

`00-infinityos-backups.preset` enables initialization and recovery-entry services
for both disk images and the payload copied by Anaconda from Live ISO media.
The initialization units exclude a running Live session through the kernel
command line and Live-mount marker, and their ExecCondition requires a Btrfs
root. The disk profile's cleanup timer policy remains unchanged.

The installer registers the services before copying EFI kernels, updating
firmware entries or removing obsolete bootloader services. Any real failure in
these steps still fails installation. Missing optional bootloader unit files
are skipped during disablement, while permission and masking failures remain
fatal. Registration alone does not mark backup initialization complete.

Snapper initialization repairs the copied sysconfig file's SELinux context when
restorecon is available. Full backup setup checks the kernel command line, EFI
mount and completed rEFInd installation before migrating snapshot storage or
changing fstab. Its ready marker is written only after refreshing the recovery
menu succeeds. Interrupted setup can be retried using the same snapshot volume.
Starting reinitialization invalidates any previous success marker until the
recovery entry is refreshed. Restoring an older root copies the current Snapper
initializer, unit and preset along with the backup tools.
The unit conditions permit retries when a marker exists but its required
configuration or snapshot mount is missing.

The updater RPM now owns the Snapper initializer, its unit and the shared preset
alongside the existing backup helpers. Its first installation applies the
preset without starting a filesystem migration inside the RPM transaction.
Package upgrades retain administrator enablement choices. They do not silently
rewrite an installed bootloader or undo intentionally disabled services.

## Diagnosing an existing installation

Collect the boot-install log, the installed-system audit, and the journal for
`infinityos-liveinstall-boot-setup.service`, `infinityos-snapper-setup.service`
and `infinityos-backups-setup.service`. A current RPM version does not identify
the ISO used for installation, and `journalctl -b` covers only the current boot.

The updater distinguishes missing Snapper configuration, incomplete full backup
setup and unmounted snapshot storage. For each, it identifies the responsible
unit and whether it is disabled/masked, failed, or has not completed. It does
not claim that restarting fixes a disabled initialization unit.

After confirming that the EFI/rEFInd installation is complete, an administrator
can enable and start the two initialization services in order. If boot setup is
incomplete, inspect and repair that installation step first. An already affected
system may need this repair before it can install the new RPM through the
updater, because the backup prerequisite deliberately remains enforced.

### Reported stale firmware order and Snapper permission denial

The reported installation failed in `efibootmgr -o`: firmware BootOrder retained
`2002` without a corresponding Boot2002 variable. The previous activation helper
copied that stale reference into the new order, which efibootmgr rejected with
exit status 8. This stopped boot conversion before its completion markers,
obsolete-loader cleanup and the former late backup-service registration.

Activation now reads defined boot entries and the order from one firmware
snapshot, refreshing it after creating an Infinity OS entry. It retains the
relative order of all defined entries, including inactive devices and other
operating systems, and omits dangling references and duplicates. It does not
delete other boot variables. Invalid IDs and actual NVRAM read/create/write
failures remain fatal. An absent BootOrder can start with the defined Infinity
OS entry. The setup RPM delivers both boot-conversion helpers for explicit
administrator retries; its package scripts do not start boot conversion.

The separate Snapper failure was `fopen /etc/sysconfig/snapper ... errno:13`.
This proves a write was denied, but does not alone prove SELinux caused it.
The initializer already restores the expected file context before attempting
Snapper configuration. On an affected old installation, relabel the file and
retry Snapper first:

```sh
sudo restorecon -v /etc/sysconfig/snapper
sudo systemctl restart infinityos-snapper-setup.service
sudo snapper -c root list
```

If that still fails, collect the service journal, `ls -lZ` for the file and
its parent directory, and recent AVC records after reproducing the error.
Do not disable SELinux or broaden file permissions to work around it.
Relabeling alone does not complete the interrupted EFI conversion or full
backup setup. After installing the corrected setup/updater RPMs, retry the
boot-conversion service and then the two backup initialization services, checking
their results and the installed-system audit before attempting normal updates.

## Validation

`tests/test_backup_initialization.py` executes the production shell entry
points in an isolated tree with injected EFI-full, NVRAM, missing-unit,
disable/mask and preflight failures. It also checks the updater's distinct
errors and its refusal to launch a transaction until prerequisites hold.
The context-repair test checks ordering before Snapper configuration and refusal
to record readiness when relabeling fails; it does not simulate SELinux policy.
`tests/test_refind_bootorder.py` executes the activation helper with simulated
firmware including the exact reported missing-2002 order, existing inactive and
other-OS entries, creation of a new entry, absent BootOrder and real I/O errors.

`tests/test_recovery_btrfs.sh` now starts with an uninitialized Btrfs target and
a disposable VFAT ESP. It exercises real systemd preset application, unit
verification, the production Snapper and full-backup initialization scripts,
failure of recovery-menu refresh, refusal of updates after that failure,
successful retry and repeated initialization. It then continues the existing
real offline RPM update and snapshot restoration checks. No running service
manager, physical firmware or actual Anaconda installation is simulated by
those container tests.
