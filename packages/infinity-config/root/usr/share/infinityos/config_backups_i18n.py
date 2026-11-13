"""English and Polish recovery UI strings."""
import locale

POLISH = {
    'Last complete backup: {date}': 'Ostatnia pełna kopia: {date}',

    'Backups': 'Kopie zapasowe',
    'Refresh': 'Odśwież', 'Delete': 'Usuń', 'Cancel': 'Anuluj',
    'Loading snapshots…': 'Wczytywanie migawek…',
    'Deleting snapshot…': 'Usuwanie migawki…',
    'Snapshot deleted.': 'Migawka została usunięta.',
    'Snapshots refreshed.': 'Lista migawek została odświeżona.',
    'No snapshots yet.': 'Nie ma jeszcze migawek.',
    'Backups are not initialized. Install InfinityOS on Btrfs to use system snapshots.':
        'Kopie nie zostały zainicjowane. Zainstaluj InfinityOS na Btrfs, aby korzystać z migawek systemu.',
    'System + /var; /home is preserved during restoration.':
        'System + /var; przywracanie zachowuje /home.',
    'Incomplete or older backup; cannot restore system + /var.':
        'Niekompletna lub starsza kopia; nie można przywrócić systemu wraz z /var.',
    'Create or restore backups by restarting and choosing Backups in the boot menu. Updates create a backup after restart.':
        'Aby utworzyć lub przywrócić kopię, uruchom komputer ponownie i wybierz Backups w menu rozruchowym. Aktualizacje tworzą kopię po restarcie.',
    'Snapshots on this disk do not protect against disk failure.':
        'Migawki na tym dysku nie chronią przed jego awarią.',
    'Administrator authentication is required to view or delete system snapshots.':
        'Przeglądanie i usuwanie migawek systemu wymaga uwierzytelnienia administratora.',
    'Delete snapshot #{number}?': 'Usunąć migawkę nr {number}?',
    'This permanently deletes this recovery point and its /var copy. Current system files and /home are kept.':
        'Trwale usunie ten punkt przywracania wraz z kopią /var. Bieżące pliki systemu i /home pozostaną.',
    'Operation failed or authentication was cancelled. Refresh to check the current state and retry.':
        'Operacja nie powiodła się lub anulowano uwierzytelnienie. Odśwież listę, aby sprawdzić stan i ponowić próbę.',
    'Error details': 'Szczegóły błędu',
    'Wait for the current backup operation to finish.': 'Poczekaj na zakończenie bieżącej operacji kopii zapasowych.',
}


def tr(message):
    return POLISH.get(message, message) if (locale.getlocale()[0] or '').split('_')[0] == 'pl' else message
