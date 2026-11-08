"""Proton page translations."""
import locale

POLISH = {
    'Proton versions': 'Wersje Protona',
    'Manage compatibility tools for this account and Steam.': 'Zarządzaj narzędziami zgodności dla tego konta i Steama.',
    'Refresh': 'Odśwież', 'Install': 'Zainstaluj', 'Update': 'Aktualizuj',
    'Installed': 'Zainstalowano', 'Remove': 'Usuń', 'Cancel': 'Anuluj',
    'Open folder': 'Otwórz katalog', 'Manage in Steam': 'Zarządzaj w Steamie',
    'Downloaded versions': 'Pobrane wersje', 'No downloaded versions.': 'Brak pobranych wersji.',
    'Available releases': 'Dostępne wydania', 'Loading releases…': 'Wczytywanie wydań…',
    'Release list unavailable. Check your connection and refresh.': 'Lista wydań niedostępna. Sprawdź połączenie i odśwież.',
    'No verified release for this architecture.': 'Brak zweryfikowanego wydania dla tej architektury.',
    'Restart Steam after changes. Updates keep older versions used by your games.':
        'Po zmianach uruchom ponownie Steam. Aktualizacje zachowują starsze wersje używane przez gry.',
    'Official releases': 'Oficjalne wydania', 'Downloading: {percent}%': 'Pobieranie: {percent}%',
    'Installing…': 'Instalowanie…', 'Removing…': 'Usuwanie…',
    'Done. Restart Steam to refresh its compatibility tools.': 'Gotowe. Uruchom ponownie Steam, aby odświeżyć narzędzia zgodności.',
    'Operation failed. Check the connection, available disk space and folder permissions.':
        'Operacja nie powiodła się. Sprawdź połączenie, wolne miejsce i uprawnienia katalogów.',
    'Wait for the current Proton operation to finish.': 'Poczekaj na zakończenie bieżącej operacji Protona.',
    'Remove {name}?': 'Usunąć {name}?',
    'Removes this version from native Steam and Flatpak where listed. Games using it will need another version. Game saves and prefixes are kept.':
        'Usuwa tę wersję z wymienionych katalogów Steama i Flatpaka. Gry korzystające z niej będą wymagały innej wersji. Zapisy gier i prefiksy pozostają.',
    'Installed by Steam; updates and removal are handled by Steam.':
        'Zainstalowane przez Steam; aktualizacje i usuwanie są obsługiwane przez Steam.',
}


def tr(message):
    return POLISH.get(message, message) if (locale.getlocale()[0] or '').split('_')[0] == 'pl' else message
