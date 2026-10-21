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
    "Official website": "Oficjalna strona",
    "Open installer": "Otwórz instalator",
    "Opening installer in Lutris…": "Otwieranie instalatora w Lutris…",
    "Finish installation in Lutris.": "Dokończ instalację w Lutris.",
    "Could not open installer:": "Nie udało się otworzyć instalatora:",
    "Installed": "Zainstalowano", "Available on x86_64": "Dostępne na x86_64",
    "Could not install:\n": "Nie udało się zainstalować:\n",
    "Wait for installation to finish.": "Poczekaj na zakończenie instalacji.",
    "Installing {index}/{total}: {name}…": "Instalowanie {index}/{total}: {name}…",
    "Web browsers": "Przeglądarki internetowe", "Media players": "Odtwarzacze multimedialne",
    "Download managers": "Menedżery pobierania", "Email clients": "Klienci poczty",
    "System maintenance": "Konserwacja systemu",
    "Device tools": "Narzędzia urządzeń", "Windows apps": "Aplikacje Windows",
    "Game launchers": "Launchery gier",
    "Xbox Controller": "Kontroler Xbox", "Audio": "Dźwięk",
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
    "Inspect disk usage and choose safe cleanup actions with clear explanations.":
        "Sprawdź zajęte miejsce i wybierz działania porządkowe z jasnymi objaśnieniami.",
    "Configure Logitech mouse buttons, DPI and SmartShift locally.":
        "Konfiguruj przyciski myszy Logitech, DPI i SmartShift lokalnie.",
    "Drivers and daemon for Razer devices; log out and back in after installation.":
        "Sterowniki i usługa dla urządzeń Razer; po instalacji wyloguj się i zaloguj ponownie.",
    "Steam games and store.": "Gry i sklep Steam.",
    "Native Linux Preview from Epic Games.": "Natywna wersja Preview dla Linuksa od Epic Games.",
    "Windows launcher; install through Lutris and Wine.":
        "Launcher Windows; zainstaluj przez Lutris i Wine.",
    "Epic, GOG and Amazon games.": "Gry z Epic, GOG i Amazon.",
    "Games from multiple stores.": "Gry z różnych sklepów.",
    "Windows games with Wine.": "Gry z Windows przez Wine.",
    "Minecraft instances and modpacks.": "Instancje i paczki modyfikacji Minecrafta.",
    "Controller-first game library.": "Biblioteka gier sterowana padem.",
    "Manage Proton, Wine, DXVK and VKD3D versions for game launchers.":
        "Zarządzaj wersjami Proton, Wine, DXVK i VKD3D dla launcherów gier.",
    "xone driver for wired Xbox controllers and the Xbox Wireless Adapter; installs dongle firmware.":
        "Sterownik xone dla przewodowych kontrolerów Xbox i adaptera bezprzewodowego; instaluje firmware adaptera.",
    "xpadneo Bluetooth driver for Xbox controllers; pair the controller after installation.":
        "Sterownik Bluetooth xpadneo dla kontrolerów Xbox; sparuj kontroler po instalacji.",
    "Voice and text chat.": "Rozmowy głosowe i tekstowe.",
    "Alternative Discord client.": "Alternatywny klient Discorda.",
    "Wine environments for Windows apps.": "Środowiska Wine dla aplikacji Windows.",
    "Run Windows apps in a container-backed VM; requires KVM, 4 GB RAM and 32 GB free space.":
        "Uruchamiaj aplikacje Windows w maszynie wirtualnej; wymaga KVM, 4 GB RAM i 32 GB wolnego miejsca.",
    "Open-source photo editor built in Rust.": "Edytor zdjęć o otwartym kodzie, napisany w Rust.",
    "Create and edit vector art in an open-source Rust app.": "Twórz i edytuj grafikę wektorową w aplikacji Rust o otwartym kodzie.",
    "Edit photos non-destructively in an open-source Rust app.": "Edytuj zdjęcia bez naruszania oryginałów w aplikacji Rust o otwartym kodzie.",
    "Edit video on a nonlinear timeline in an open-source Rust app.": "Montuj wideo na nieliniowej osi czasu w aplikacji Rust o otwartym kodzie.",
    "Create motion graphics and composite visual effects.": "Twórz animowaną grafikę i łącz efekty wizualne.",
    "Design pages and publication layouts in an open-source Rust app.": "Projektuj strony i układy publikacji w aplikacji Rust o otwartym kodzie.",
    "Computer-aided design and drafting in an open-source Rust app.": "Projektowanie i rysowanie CAD w aplikacji Rust o otwartym kodzie.",
    "Design and prototype interfaces with frames, components and layouts (early alpha).":
        "Projektuj i prototypuj interfejsy z ramkami, komponentami i układami (wczesna alfa).",
    "Record, edit and mix multitrack audio (pre-alpha).":
        "Nagrywaj, edytuj i miksuj dźwięk wielościeżkowy (przed alfą).",
    "Edit raster images.": "Edytuj obrazy rastrowe.",
    "Paint and illustrate.": "Maluj i twórz ilustracje.",
    "Edit vector graphics.": "Edytuj grafikę wektorową.",
    "Model and animate in 3D.": "Modeluj i animuj w 3D.",
    "Edit videos on a timeline.": "Montuj filmy na osi czasu.",
    "Record and stream your screen.": "Nagrywaj i transmituj ekran.",
    "Record and edit audio.": "Nagrywaj i edytuj dźwięk.",
    "Microsoft's code editor.": "Edytor kodu Microsoftu.",
    "Docker's official packages. Use sudo unless you configure user access.":
        "Oficjalne pakiety Dockera. Użyj sudo lub skonfiguruj dostęp użytkownika.",
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
    "Documents, spreadsheets, presentations and PDFs.":
        "Dokumenty, arkusze kalkulacyjne, prezentacje i pliki PDF.",
    "Read and edit PDF documents in an open-source Rust app.": "Czytaj i edytuj PDF w aplikacji Rust o otwartym kodzie.",
    "Create and edit word-processing documents in an open-source Rust app.":
        "Twórz i edytuj dokumenty tekstowe w aplikacji Rust o otwartym kodzie.",
    "Create spreadsheets for data and tables in an open-source Rust app.":
        "Twórz arkusze kalkulacyjne dla danych i tabel w aplikacji Rust o otwartym kodzie.",
    "Create presentations and slide shows in an open-source Rust app.":
        "Twórz prezentacje i pokazy slajdów w aplikacji Rust o otwartym kodzie.",
}


def tr(message):
    language = (locale.getlocale()[0] or "").split("_")[0]
    return POLISH.get(message, message) if language == "pl" else message
