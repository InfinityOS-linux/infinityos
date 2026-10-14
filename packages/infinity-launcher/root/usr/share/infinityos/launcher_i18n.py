"""Small, bundled InfinityLauncher catalog; English is the fallback language."""

import locale


POLISH = {
    "Assistants and command-line tools": "Asystenci i narzędzia wiersza poleceń",
    "Everyday essentials": "Niezbędne aplikacje na co dzień",
    "Games, launchers and friends": "Gry, launchery i komunikacja",
    "Tools for making things": "Narzędzia do tworzenia",
    "Documents and productivity": "Dokumenty i produktywność",
    "Build your workspace": "Przygotuj środowisko pracy",
    "System": "System", "Gaming": "Gry", "Creative": "Tworzenie",
    "Office": "Biuro", "Programming": "Programowanie",
    "WELCOME TO INFINITY OS": "WITAJ W INFINITY OS",
    "Make it yours. Pick the apps you want, then add more anytime.":
        "Dostosuj system. Wybierz aplikacje, które chcesz zainstalować.",
    "Close": "Zamknij", "Apply": "Zastosuj",
    "Your changes install when you click Apply.":
        "Wybrane aplikacje zainstalują się po kliknięciu Zastosuj.",
    "Run at next startup": "Uruchom przy następnym starcie",
    "View source and releases": "Kod źródłowy i wydania",
    "Installed": "Zainstalowano", "Available on x86_64": "Dostępne na x86_64",
    "Could not install:\n": "Nie udało się zainstalować:\n",
    "Wait for installation to finish.": "Poczekaj na zakończenie instalacji.",
    "Installing {index}/{total}: {name}…": "Instalowanie {index}/{total}: {name}…",
    "Web browsers": "Przeglądarki internetowe", "Media players": "Odtwarzacze multimedialne",
    "Download managers": "Menedżery pobierania", "Email clients": "Klienci poczty",
    "Device tools": "Narzędzia urządzeń", "Game launchers": "Launchery gier",
    "Communication": "Komunikacja", "Other": "Inne", "Image": "Obraz",
    "Video": "Wideo", "Design": "Projektowanie", "More tools": "Więcej narzędzi",
    "Development tools": "Narzędzia programistyczne", "Assistants": "Asystenci",
    "Local models": "Modele lokalne", "Active local model": "Aktywny model lokalny",
    "Office suite": "Pakiet biurowy", "Documents": "Dokumenty",
    "Google's web browser with account sync.": "Przeglądarka Google z synchronizacją konta.",
    "Open-source Chromium web browser.": "Przeglądarka Chromium z otwartym kodem.",
    "Firefox-based browser with a focused workspace.": "Przeglądarka oparta na Firefoxie, stworzona do skupionej pracy.",
    "Web browser with built-in sidebar tools.": "Przeglądarka z narzędziami w panelu bocznym.",
    "Gaming browser with performance controls.": "Przeglądarka dla graczy z kontrolą wydajności.",
    "Privacy-focused Chromium browser.": "Przeglądarka Chromium skupiona na prywatności.",
    "Play video, audio and network streams.": "Odtwarzaj filmy, muzykę i strumienie sieciowe.",
    "Stream music, podcasts and audiobooks.": "Słuchaj muzyki, podcastów i audiobooków.",
    "Lightweight video player with keyboard controls.": "Lekki odtwarzacz filmów sterowany klawiaturą.",
    "Torrent client with search and queue controls.": "Klient torrentów z wyszukiwarką i kolejką pobierania.",
    "Simple, lightweight torrent client.": "Prosty i lekki klient torrentów.",
    "Download files from many hosting services.": "Pobieraj pliki z wielu serwisów hostingowych.",
    "Email, calendar and contacts.": "Poczta, kalendarz i kontakty.",
    "GNOME email, calendar and contacts.": "Poczta, kalendarz i kontakty dla GNOME.",
    "Email client with a unified inbox.": "Klient poczty ze wspólną skrzynką odbiorczą.",
    "Email client with a modern inbox.": "Klient poczty z nowoczesną skrzynką odbiorczą.",
    "Configure Logitech mouse buttons, DPI and SmartShift locally.":
        "Konfiguruj przyciski myszy Logitech, DPI i SmartShift lokalnie.",
    "Steam games and store.": "Gry i sklep Steam.",
    "Epic, GOG and Amazon games.": "Gry z Epic, GOG i Amazon.",
    "Games from multiple stores.": "Gry z różnych sklepów.",
    "Windows games with Wine.": "Gry z Windows przez Wine.",
    "Minecraft instances and modpacks.": "Instancje i paczki modyfikacji Minecrafta.",
    "Controller-first game library.": "Biblioteka gier sterowana padem.",
    "Voice and text chat.": "Rozmowy głosowe i tekstowe.",
    "Alternative Discord client.": "Alternatywny klient Discorda.",
    "Wine environments for Windows apps.": "Środowiska Wine dla aplikacji Windows.",
    "Adobe-style photo editor clone.": "Klon edytora zdjęć Adobe.",
    "Adobe-style vector editor clone.": "Klon edytora grafiki wektorowej Adobe.",
    "Adobe-style photo workflow clone.": "Klon programu Adobe do obróbki zdjęć.",
    "Adobe-style video editor clone.": "Klon edytora wideo Adobe.",
    "Adobe-style visual effects clone.": "Klon programu Adobe do efektów wizualnych.",
    "Adobe-style layout editor clone.": "Klon programu Adobe do składu publikacji.",
    "Adobe-style 3D design clone.": "Klon programu Adobe do projektowania 3D.",
    "Edit raster images.": "Edytuj obrazy rastrowe.",
    "Paint and illustrate.": "Maluj i twórz ilustracje.",
    "Edit vector graphics.": "Edytuj grafikę wektorową.",
    "Model and animate in 3D.": "Modeluj i animuj w 3D.",
    "Edit videos on a timeline.": "Montuj filmy na osi czasu.",
    "Record and stream your screen.": "Nagrywaj i transmituj ekran.",
    "Record and edit audio.": "Nagrywaj i edytuj dźwięk.",
    "Microsoft's code editor.": "Edytor kodu Microsoftu.",
    "Docker's official Fedora packages. Use sudo unless you configure user access.":
        "Oficjalne pakiety Dockera dla Fedory. Użyj sudo lub skonfiguruj dostęp użytkownika.",
    "CLI and Claude web shortcut. Adds a pinned terminal tab.":
        "CLI i skrót do Claude w przeglądarce. Dodaje przypiętą kartę terminala.",
    "CLI and Codex web shortcut. Adds a pinned terminal tab.":
        "CLI i skrót do Codexa w przeglądarce. Dodaje przypiętą kartę terminala.",
    "For 16 GB RAM. Needs about 10 GB free disk; local coding agent.":
        "Dla 16 GB RAM. Wymaga ok. 10 GB wolnego miejsca; lokalny agent programistyczny.",
    "For 24–32 GB RAM. Needs about 11 GB free disk; local coding agent.":
        "Dla 24–32 GB RAM. Wymaga ok. 11 GB wolnego miejsca; lokalny agent programistyczny.",
    "For 64 GB RAM. Needs about 30 GB free disk; local coding agent.":
        "Dla 64 GB RAM. Wymaga ok. 30 GB wolnego miejsca; lokalny agent programistyczny.",
    "Documents, presentations and spreadsheets.": "Dokumenty, prezentacje i arkusze kalkulacyjne.",
    "Adobe-style PDF editor clone.": "Klon edytora PDF Adobe.",
    "Adobe-style document editor clone.": "Klon edytora dokumentów Adobe.",
    "Adobe-style presentation editor clone.": "Klon edytora prezentacji Adobe.",
}


def tr(message):
    language = (locale.getlocale()[0] or "").split("_")[0]
    return POLISH.get(message, message) if language == "pl" else message
