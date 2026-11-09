"""Small, bundled InfinitySetup catalog; English is the fallback language."""

import locale


POLISH = {
    "Installation complete.": "Instalacja ukończona.",
    "TV Mode is installed. Open Steam from the desktop to finish its first update.":
        "TV Mode jest zainstalowany. Otwórz Steam z pulpitu, aby dokończyć jego pierwszą aktualizację.",
    "Install the new native Epic Games Launcher Preview.": "Zainstaluj nowy, natywny Epic Games Launcher Preview.",
    "Play supported Game Pass and Microsoft Store games. Requires a purchase or subscription. ARM support is experimental.":
        "Graj w obsługiwane gry z Game Pass i Microsoft Store. Wymagany zakup lub subskrypcja. Obsługa ARM jest eksperymentalna.",
    "Downloaded models": "Pobrane modele",
    "Active custom model": "Aktywny własny model",
    "AI changed in InfinityConfig. Review your selection again.": "AI zmieniono w InfinityConfig. Sprawdź ponownie swój wybór.",
    "Downloaded; inactive": "Pobrany; nieaktywny",
    "Not downloaded": "Niepobrany",
    "Retry pending changes": "Ponów niezastosowane zmiany",
    "Install PDFCraft, WordCraft, GridCraft and DeckCraft. Manage each app separately.":
        "Zainstaluj PDFCraft, WordCraft, GridCraft i DeckCraft. Zarządzaj każdą aplikacją osobno.",
    "Manage this model in InfinityConfig.": "Zarządzaj tym modelem w InfinityConfig.",
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
    "Your changes take effect when you click Apply.":
        "Zmiany zostaną wprowadzone po kliknięciu Zastosuj.",
    "View source and releases": "Kod źródłowy i wydania",
    "Official website": "Oficjalna strona",
    "Open installer": "Otwórz instalator",
    "Opening installer in Lutris…": "Otwieranie instalatora w Lutris…",
    "Finish installation in Lutris.": "Dokończ instalację w Lutris.",
    "Could not open installer:": "Nie udało się otworzyć instalatora:",
    "Installed": "Zainstalowano", "Only available on x64 computers": "Dostępne tylko na komputerach x64",
    "Could not install:\n": "Nie udało się zainstalować:\n",
    "Could not apply changes:\n": "Nie udało się wprowadzić zmian:\n",
    "Wait for installation to finish.": "Poczekaj na zakończenie instalacji.",
    "Installing {index}/{total}: {name}…": "Instalowanie {index}/{total}: {name}…",
    "Applying {index}/{total}: {name}…": "Wprowadzanie zmian {index}/{total}: {name}…",
    "Web browsers": "Przeglądarki internetowe", "Media players": "Odtwarzacze multimedialne",
    "Download managers": "Menedżery pobierania", "Email clients": "Klienci poczty",
    "System maintenance": "Konserwacja systemu",
    "Device tools": "Narzędzia urządzeń", "Windows apps": "Aplikacje Windows",
    "Game launchers": "Launchery gier",
    "Selecting a TV boot entry signs in to your account automatically.":
        "Wybranie trybu TV przy starcie automatycznie loguje na Twoje konto.",
    "EmulationStation (ES-DE)": "EmulationStation (ES-DE)",
    "Steam Big Picture": "Steam Big Picture",
    "Browse your own ROMs in /emulation/roms; place BIOS files in /emulation/bios.":
        "Przeglądaj własne ROM-y w /emulation/roms; pliki BIOS umieść w /emulation/bios.",
    "Start Steam fullscreen without the GNOME desktop.":
        "Uruchamiaj Steam na pełnym ekranie bez pulpitu GNOME.",
    "Enabled": "Włączono",
    "Xbox Controller": "Kontroler Xbox", "Audio": "Dźwięk",
    "Communication": "Komunikacja", "Other": "Inne", "Image": "Obraz",
    "Video": "Wideo", "Design": "Projektowanie", "More tools": "Więcej narzędzi",
    "Development tools": "Narzędzia programistyczne", "Assistants": "Asystenci",
    "Local models": "Modele lokalne", "Active local model": "Aktywny model lokalny",
    "Office suite": "Pakiet biurowy", "Documents": "Dokumenty",
    "Browse the web and sync bookmarks with Google.":
        "Przeglądaj internet i synchronizuj zakładki z Google.",
    "Browse the web with an open-source browser.":
        "Przeglądaj internet w przeglądarce z otwartym kodem.",
    "Browse the web with tabs arranged in workspaces.":
        "Przeglądaj internet i porządkuj karty w przestrzeniach.",
    "Browse the web with a built-in sidebar.": "Przeglądaj internet z wygodnym panelem bocznym.",
    "Browse the web with tools for gaming.": "Przeglądaj internet z dodatkowymi narzędziami dla graczy.",
    "Browse the web with built-in ad blocking.": "Przeglądaj internet z wbudowanym blokowaniem reklam.",
    "Play videos, music and online streams.": "Odtwarzaj filmy, muzykę i transmisje internetowe.",
    "Listen to music and podcasts online.": "Słuchaj muzyki i podcastów w internecie.",
    "Play videos with a lightweight player.": "Odtwarzaj filmy w lekkim odtwarzaczu.",
    "Download and manage torrents.": "Pobieraj torrenty i zarządzaj nimi.",
    "Download torrents with a simple app.": "Pobieraj torrenty w prostej aplikacji.",
    "Download files from many websites.": "Pobieraj pliki z wielu stron internetowych.",
    "Manage email, calendars and contacts.": "Obsługuj pocztę, kalendarze i kontakty.",
    "Manage email, calendars and contacts in GNOME.": "Obsługuj pocztę, kalendarze i kontakty w GNOME.",
    "Read email from several accounts in one inbox.": "Czytaj pocztę z kilku kont w jednej skrzynce.",
    "Read and organize email from several accounts.": "Czytaj i porządkuj pocztę z kilku kont.",
    "See what uses disk space and remove unneeded files.":
        "Sprawdź, co zajmuje miejsce na dysku, i usuń zbędne pliki.",
    "Share screens, files and controls between devices.":
        "Udostępniaj ekrany i pliki oraz steruj innymi urządzeniami.",
    "Set up Logitech mouse buttons and sensitivity.": "Ustaw przyciski i czułość myszy Logitech.",
    "Enable and configure Razer gaming devices.": "Uruchom i skonfiguruj urządzenia Razer.",
    "Run Windows easily on this system.": "Uruchom w łatwy sposób Windowsa na tym systemie.",
    "Buy, install and play games from Steam.": "Kupuj, instaluj i uruchamiaj gry ze Steam.",
    "Could not disable Steam TV Mode; Steam was left installed.":
        "Nie udało się wyłączyć Steam TV Mode; Steam pozostał zainstalowany.",
    "Install and play games from Epic Games.": "Instaluj i uruchamiaj gry z Epic Games.",
    "Install and play Blizzard games through Lutris.":
        "Instaluj i uruchamiaj gry Blizzarda przez Lutris.",
    "Install and play games from Epic, GOG and Amazon.": "Instaluj gry z Epic, GOG i Amazon.",
    "Install and manage games from many stores.": "Instaluj gry z różnych sklepów i zarządzaj nimi.",
    "Run Windows games on Linux with Wine.": "Uruchamiaj gry z Windowsa na Linuksie przez Wine.",
    "Manage Minecraft versions and modpacks.": "Zarządzaj wersjami Minecrafta i paczkami modów.",
    "Browse and launch games using a controller.": "Przeglądaj i uruchamiaj gry za pomocą pada.",
    "Install and update tools for Windows games.": "Instaluj i aktualizuj narzędzia do gier z Windowsa.",
    "Use an Xbox controller by USB or wireless dongle.":
        "Podłącz pad Xbox przez USB lub adapter bezprzewodowy.",
    "Use an Xbox controller over Bluetooth.": "Podłącz pad Xbox przez Bluetooth.",
    "Talk with friends by voice and text.": "Rozmawiaj ze znajomymi głosowo i przez wiadomości.",
    "Use Discord with extra customization.": "Korzystaj z Discorda z dodatkowymi opcjami wyglądu.",
    "Run Windows apps in separate Wine environments.":
        "Uruchamiaj aplikacje Windows w osobnych środowiskach Wine.",
    "The image editor you already know how to use.": "Edytor obrazów, który już znasz.",
    "Vector illustration, with familiar tools and editable effects.":
        "Ilustracje wektorowe ze znajomymi narzędziami i edytowalnymi efektami.",
    "Your photos. Your pixels. Your machine.": "Twoje zdjęcia. Twoje piksele. Twój komputer.",
    "Professional video editing, rebuilt from scratch.":
        "Profesjonalny montaż wideo, zbudowany od podstaw.",
    "Motion graphics and visual effects.": "Grafika ruchoma i efekty wizualne.",
    "Page layout and publishing.": "Skład stron i publikowanie.",
    "Computer-aided drafting, with a familiar workflow.":
        "Projektowanie wspomagane komputerowo w znajomym środowisku.",
    "Interface design and prototyping.": "Projektowanie interfejsów i prototypowanie.",
    "Parametric 3D CAD, with editable sketches and solids.":
        "Parametryczne projektowanie 3D z edytowalnymi szkicami i bryłami.",
    "Build materials with node graphs.": "Twórz materiały za pomocą grafów węzłów.",
    "Paint textures on 3D models.": "Maluj tekstury na modelach 3D.",
    "Record, edit and mix your audio.": "Nagrywaj, edytuj i miksuj dźwięk.",
    "Edit photos and other images.": "Edytuj zdjęcia i inne obrazy.",
    "Paint and draw digital art.": "Maluj i rysuj cyfrowe ilustracje.",
    "Create and edit vector graphics.": "Twórz i edytuj grafikę wektorową.",
    "Create 3D models and animations.": "Twórz modele 3D i animacje.",
    "Edit videos on a timeline.": "Montuj filmy na osi czasu.",
    "Record your screen and stream video.": "Nagrywaj ekran i prowadź transmisje wideo.",
    "Record and edit audio.": "Nagrywaj i edytuj dźwięk.",
    "Write and edit code.": "Pisz i edytuj kod.",
    "See how any website, app or game works, then build your own.":
        "Zobacz, jak działa dowolna strona, aplikacja lub gra, a potem zbuduj własną.",
    "Run apps in isolated containers.": "Uruchamiaj aplikacje w odizolowanych kontenerach.",
    "Use Claude in the browser and terminal.": "Korzystaj z Claude w przeglądarce i terminalu.",
    "Use Codex in the browser and terminal.": "Korzystaj z Codexa w przeglądarce i terminalu.",
    "Run a local AI coding assistant. Needs 10 GB of disk space.":
        "Uruchom lokalnego asystenta AI do kodu. Potrzebuje 10 GB miejsca na dysku.",
    "Run a local AI coding assistant. Needs 11 GB of disk space.":
        "Uruchom lokalnego asystenta AI do kodu. Potrzebuje 11 GB miejsca na dysku.",
    "Run a local AI coding assistant. Needs 30 GB of disk space.":
        "Uruchom lokalnego asystenta AI do kodu. Potrzebuje 30 GB miejsca na dysku.",
    "Create documents, spreadsheets and presentations.": "Twórz dokumenty, arkusze i prezentacje.",
    "The open-source PDF workbench.": "Otwarte narzędzie do pracy z plikami PDF.",
    "The familiar word processor, native and offline.":
        "Znany edytor tekstu, działający natywnie i bez internetu.",
    "Spreadsheets you already know how to use.": "Arkusze kalkulacyjne, które już znasz.",
    "Create slides, tell stories and present.": "Twórz slajdy, opowiadaj historie i prezentuj.",
}


def tr(message):
    language = (locale.getlocale()[0] or "").split("_")[0]
    return POLISH.get(message, message) if language == "pl" else message
