"""AI settings translations follow the desktop locale."""
import locale

POLISH = {
    'Free space: {size:.1f} GiB': 'Wolne miejsce: {size:.1f} GiB',
    'Server reachable. Memory use grows with context size and model architecture; the model name is not a RAM guarantee.': 'Serwer odpowiada. Zużycie pamięci zależy od kontekstu i architektury modelu; nazwa modelu nie gwarantuje wymagań RAM.',
    'Context budget: {factor:.1f}× 4096 tokens. Actual RAM use depends on the model and cache.': 'Budżet kontekstu: {factor:.1f}× 4096 tokenów. Rzeczywiste zużycie RAM zależy od modelu i cache.',

    'Wait for the current AI operation to finish.': 'Poczekaj na zakończenie bieżącej operacji AI.',
    'Accounts and local models': 'Konta i modele lokalne',
    'Refresh': 'Odśwież', 'Sign in': 'Zaloguj', 'Sign out': 'Wyloguj',
    'Provider usage': 'Zużycie u dostawcy', 'Not signed in': 'Nie zalogowano',
    'Signed in as: {account}': 'Zalogowano jako: {account}',
    'Plan: {plan}': 'Plan: {plan}', 'Loading…': 'Wczytywanie…',
    'Status unavailable. Check the connection and refresh.': 'Status niedostępny. Sprawdź połączenie i odśwież.',
    'Usage unavailable through the provider CLI.': 'Dane o zużyciu niedostępne przez aplikację dostawcy.',
    '{name}: {left}% remaining ({minutes} min window)': '{name}: pozostało {left}% (okno {minutes} min)',
    'Resets: {time}': 'Odnowienie: {time}', 'Credits: {balance}': 'Kredyty: {balance}',
    'Unlimited credits': 'Kredyty bez limitu', 'Total tokens used: {tokens}': 'Łącznie zużyte tokeny: {tokens}',
    'Local model': 'Model lokalny', 'Model': 'Model', 'Context (tokens)': 'Kontekst (tokeny)',
    'Maximum response (tokens)': 'Maksymalna odpowiedź (tokeny)', 'Temperature': 'Temperatura',
    'Apply model settings': 'Zastosuj ustawienia modelu', 'Import GGUF…': 'Importuj GGUF…',
    'Choose a GGUF model': 'Wybierz model GGUF', 'Choose': 'Wybierz', 'Cancel': 'Anuluj',
    'Model storage': 'Katalog modeli', 'Copy models to another folder…': 'Skopiuj modele do innego katalogu…',
    'Choose an empty folder accessible to the Ollama service.': 'Wybierz pusty katalog dostępny dla usługi Ollama.',
    'Copies all models and restarts Ollama. Old files are kept. Administrator authentication is required.':
        'Kopiuje wszystkie modele i uruchamia ponownie Ollama. Stare pliki pozostają. Wymagane uwierzytelnienie administratora.',
    'Working…': 'Trwa operacja…', 'Saved. New settings apply to new AI sessions.': 'Zapisano. Nowe ustawienia dotyczą nowych sesji AI.',
    'Operation failed. Check the provider or local service and try again.': 'Operacja nie powiodła się. Sprawdź dostawcę lub usługę lokalną i spróbuj ponownie.',
    'Storage unavailable': 'Katalog niedostępny',
    'Response length must not exceed context size.': 'Długość odpowiedzi nie może przekraczać rozmiaru kontekstu.',
    'Sign out of {provider}?': 'Wylogować z {provider}?',
    'Other sessions using this account may also be signed out.': 'Inne sesje korzystające z tego konta mogą również zostać wylogowane.',
    'Choose model in terminal': 'Wybierz model w terminalu',
    'Use /model in the provider terminal to select its model.': 'Użyj /model w terminalu dostawcy, aby wybrać jego model.',
}


def tr(message):
    return POLISH.get(message, message) if (locale.getlocale()[0] or '').split('_')[0] == 'pl' else message
