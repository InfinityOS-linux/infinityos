"""Small built-in translation catalog for the updater window."""

import locale


POLISH = {
    'Infinity OS Updates': 'Aktualizacje Infinity OS',
    'System packages · Flatpaks · Device firmware':
        'Pakiety systemowe · Flatpaki · Oprogramowanie urządzeń',
    'Check again': 'Sprawdź ponownie',
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
