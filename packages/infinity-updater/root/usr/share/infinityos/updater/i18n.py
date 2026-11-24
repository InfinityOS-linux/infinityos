"""Small built-in translation catalog for the updater window."""

import locale


POLISH = {
    'Updates with problems ({count})': 'Aktualizacje z problemami ({count})',
    'Retry this update': 'Ponów tę aktualizację',
    'Flatpak could not verify the update plan.': 'Flatpak nie mógł zweryfikować planu aktualizacji.',
    'Flatpak installation failed.': 'Instalacja aktualizacji Flatpak nie powiodła się.',
    'Flatpak finished, but the same update is still pending. No restart is needed.':
        'Flatpak zakończył pracę, ale ta sama aktualizacja nadal oczekuje. Restart nie jest potrzebny.',
    'Authorizing': 'Autoryzacja',
    'Waiting for compatibility ({count})': 'Oczekują na zgodność ({count})',
    'These packages will be offered automatically when compatible dependencies are available.':
        'Pakiety pojawią się w dostępnych aktualizacjach, gdy będą dostępne zgodne zależności.',
    'No updates ready to install.': 'Brak aktualizacji gotowych do zainstalowania.',
    'Some packages are waiting for compatible versions.': 'Niektóre pakiety oczekują na zgodne wersje.',

    'Last system operation: {status}; backup #{snapshot}': 'Ostatnia operacja systemowa: {status}; kopia #{snapshot}',
    'Restore system and /var from Backups in the boot menu. /home is preserved.': 'System i /var możesz przywrócić przez Backups w menu rozruchowym. /home pozostaje bez zmian.',
    'History': 'Historia', 'No update history yet.': 'Brak historii aktualizacji.',
    'Failed': 'Błąd', 'Completed': 'Ukończono',
    'Downloaded; restart required': 'Pobrano; wymagane ponowne uruchomienie',

    'Downloaded — installs after restart': 'Pobrano — instalacja po ponownym uruchomieniu',
    'Checking: {source}': 'Sprawdzanie: {source}',
    'System packages': 'Pakiety systemowe',
    'InfinityApps apps': 'Aplikacje InfinityApps',
    'System Flatpaks': 'Systemowe Flatpaki',
    'Your Flatpaks': 'Flatpaki użytkownika',
    'Device firmware': 'Oprogramowanie urządzeń',
    'Infinity OS releases': 'Wydania Infinity OS',
    "Firmware updated. Restart may be required.": "Oprogramowanie urządzeń zaktualizowano. Może być wymagany restart.",
    'Error details': 'Szczegóły błędu',
    'Affected RPM builds are skipped. New builds are checked automatically.':
        'Updater pomija wstrzymane wersje i automatycznie sprawdza nowsze wydania pakietów.',
    'The last offline update failed.': 'Ostatnia aktualizacja podczas rozruchu nie powiodła się.',
    'The last offline update was interrupted.': 'Ostatnia aktualizacja podczas rozruchu została przerwana.',
    'The saved RPM transaction could not be read.': 'Nie udało się odczytać zapisanej transakcji RPM.',
    'A complete Btrfs backup could not be created.': 'Nie udało się utworzyć pełnej kopii zapasowej Btrfs.',
    'DNF could not complete the system package installation.': 'DNF nie ukończył instalacji pakietów systemowych.',
    'An RPM file conflicts with a file owned by another package.': 'Plik z pakietu RPM koliduje z plikiem innego pakietu.',
    'Installed packages changed after download. InfinityUpdater can prepare a fresh transaction.':
        'Po pobraniu zmieniły się zainstalowane pakiety. InfinityUpdater może przygotować nową transakcję.',
    'Package installation finished, but update finalization failed.':
        'Instalacja pakietów dobiegła końca, ale finalizacja aktualizacji się nie powiodła.',
    'Recovery backup #{snapshot} is available in the boot menu.':
        'Kopia zapasowa nr {snapshot} jest dostępna w menu rozruchowym.',

    'Updates downloaded, restart to update.':
        'Aktualizacje pobrane, uruchom ponownie, aby zaktualizować.',
    'Infinity OS {version} prepared. Restart to back up and install.':
        'Infinity OS {version} przygotowany. Uruchom ponownie, aby wykonać kopię i zainstalować.',
    'After restart, system and /var are backed up before updating. /home is preserved.':
        'Po restarcie, przed aktualizacją, powstaje kopia systemu i /var. /home zostaje zachowany.',
    'InfinityUpdater': 'InfinityUpdater',
    'System packages · Flatpaks · Device firmware':
        'Pakiety systemowe · Flatpaki · Oprogramowanie urządzeń',
    'Check again': 'Sprawdź ponownie',
    'Updates downloaded': 'Aktualizacje pobrane',
    'Restart to install': 'Restartuj, aby zainstalować',
    'Restart to install the downloaded updates.': 'Uruchom ponownie komputer, aby zainstalować pobrane aktualizacje.',
    'Restart to update': 'Uruchom ponownie, aby zaktualizować',
    'Could not restart the system.': 'Nie udało się uruchomić systemu ponownie.',
    'Install updates': 'Zainstaluj aktualizacje',
    'Upgrade Infinity OS': 'Zaktualizuj Infinity OS',
    'Checking for updates…': 'Sprawdzanie aktualizacji…',
    'Checking package repositories and other sources.':
        'Sprawdzanie repozytoriów pakietów i innych źródeł.',
    'No internet connection': 'Brak połączenia z internetem',
    'Connect to the internet and check again.':
        'Połącz się z internetem i sprawdź ponownie.',
    'Could not confirm whether updates are available.':
        'Nie udało się sprawdzić, czy są dostępne aktualizacje.',
    'Your system is up to date.': 'System jest aktualny.',
    'Some sources could not be checked:\n': 'Nie udało się sprawdzić niektórych źródeł:\n',
    'Last checked: ': 'Ostatnio sprawdzono: ',
    'never': 'nigdy',
    'Infinity OS {version} is available': 'Dostępna jest wersja Infinity OS {version}',
    'First install current system packages, then download and install the new release. '
    'A Btrfs recovery snapshot is created before each system transaction.':
        'Najpierw zainstaluj bieżące aktualizacje pakietów, a następnie pobierz i zainstaluj '
        'nową wersję. Przed każdą zmianą pakietów system tworzy migawkę Btrfs.',
    'This release changes the Fedora base and needs a dedicated migration path.':
        'Ta wersja zmienia bazę Fedory i wymaga osobnej procedury migracji.',
    'Some updates could not be installed.': 'Nie udało się zainstalować części aktualizacji.',
    'RPM updates waiting for compatible dependencies: {packages}':
        'Aktualizacje RPM czekają na zgodne zależności: {packages}',
    'System updates installed. Restart may be required.':
        'Zainstalowano aktualizacje systemu. Może być wymagane ponowne uruchomienie.',
    'Sign out and back in to use updated extensions.':
        'Wyloguj się i zaloguj ponownie, aby korzystać ze zaktualizowanych rozszerzeń.',
    'Updates installed.': 'Zainstalowano aktualizacje.',
    'Infinity OS {version} installed. Restart to use the new release.':
        'Zainstalowano Infinity OS {version}. Uruchom komputer ponownie, aby korzystać z nowej wersji.',
}


def tr(message):
    language = (locale.getlocale()[0] or '').split('_')[0]
    return POLISH.get(message, message) if language == 'pl' else message


def update_count(count):
    language = (locale.getlocale()[0] or '').split('_')[0]
    if language != 'pl':
        return f'{count} available update' + ('' if count == 1 else 's')
    if count == 1:
        return '1 dostępna aktualizacja'
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f'{count} dostępne aktualizacje'
    return f'{count} dostępnych aktualizacji'
