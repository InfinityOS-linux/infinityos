# Infinity OS recovery

System package updates are downloaded during the normal session. Restart when ready:
DNF installs the prepared transaction before the desktop and ordinary services start.
A required Btrfs recovery point is created immediately before installation. If the
backup fails, installation does not start. InfinityUpdater shows failures and their
log, and allows another attempt after reboot.

A complete recovery point contains the root filesystem and `/var`, either as one
root snapshot or as a matched pair when `/var` is a separate subvolume. `/home`
must be mounted separately; unsupported layouts stop the backup before updating. It does not
include `/home`, EFI firmware, device firmware or the EFI system partition. It is
not a substitute for an external backup against disk failure.

## Restore

1. Restart and select **Backups** in the Infinity OS boot menu.
2. Find a snapshot whose description begins **System + /var**.
3. Choose **r**, enter its number and type **RESTORE**.
4. The tool first saves the current system and `/var`. It prepares writable copies
   of the selected root and `/var`, then switches the default Btrfs root. The new
   root's mount table refers to its matching `/var`; `/home` remains unchanged.
5. Press Enter to restart. The previous root and service data are retained.

Older root-only snapshots cannot restore `/var`, so the new restore command refuses
them. A snapshot is also refused if its required `/var` companion is missing or writable.
Backups stop when `/var` contains nested subvolumes, rather than silently excluding
container or database data. Separate filesystems mounted below `/var` must likewise
be handled before creating a complete backup.

Snapshots use Snapper's number retention policy. Orphaned `/var` companions are
removed on the next successful backup. Deleting a complete snapshot in the Backups
menu removes both parts. Restored writable roots are retained for recovery and are
not automatically deleted.

## Tests

Run `tests/test_recovery_btrfs.sh` only in a disposable privileged Fedora container
with `snapper` and `rpm-build`. It creates a sparse temporary Btrfs disk, installs
and updates a real fixture RPM through DNF offline mode, executes the production
restore function, and checks system data, `/var`, and preserved `/home` data.
The service manager is stubbed to prevent rebooting the container host. This test
does not verify a real EFI boot, physical storage failures, or application-specific
migration of databases between versions.

## Polski

Aktualizacje pakietów systemowych są pobierane w działającej sesji i instalowane po
restarcie, przed uruchomieniem pulpitu. Przed instalacją powstaje obowiązkowa kopia
systemu i `/var`. Błąd kopii zatrzymuje aktualizację.

Aby przywrócić: w menu rozruchowym wybierz **Backups**, znajdź kopię **System + /var**,
naciśnij **r**, podaj numer i wpisz **RESTORE**. Następnie uruchom ponownie komputer.
Przywrócone zostają system i dane usług w `/var`; pliki w `/home` zostają zachowane.
Stare kopie obejmujące tylko system nie nadają się do takiego przywracania. Kopia na
tym samym dysku nie chroni przed awarią dysku — ważne pliki kopiuj także poza komputer.
