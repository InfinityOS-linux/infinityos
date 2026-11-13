"""Application catalog and deferred installation for InfinitySetup."""

import hashlib
import io
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import NamedTuple


class App(NamedTuple):
    category: str
    name: str
    kind: str
    source: str
    description: str
    x86_only: bool = False
    website: str = ""
    group: str = ""
    icon: str = "application-x-executable-symbolic"
    package: str = ""


class LocalModel(NamedTuple):
    remote: str
    disk_gb: int


CRAFT_SUITE = {"storytold/pdfcraft", "storytold/wordcraft", "storytold/gridcraft", "storytold/deckcraft"}


LOCAL_MODELS = {
    "infinity-qwen-9b": LocalModel("hf.co/unsloth/Qwen3.5-9B-GGUF:UD-Q5_K_XL", 10),
    "infinity-gemma-12b": LocalModel("hf.co/unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL", 11),
    "infinity-qwen-35b": LocalModel("hf.co/unsloth/Qwen3.5-35B-A3B-GGUF:UD-Q5_K_XL", 30),
}

GITHUB_APPIMAGES = {
    "domsvoboda/nexus-launcher": ("Xodus-Nexus.AppImage", "org.infinityos.NexusLauncher.desktop",
                              "/usr/share/infinityos/launcher-icons/nexus-launcher.png"),
    "cyb3rl00m/safe-disk-cleaner": ("SafeDiskCleaner.AppImage", "io.github.cyb3rl00m.SafeDiskCleaner.desktop",
                                    "/usr/share/infinityos/launcher-icons/io.github.cyb3rl00m.SafeDiskCleaner.svg"),
    "InukaAsith/TwinDesk": ("TwinDesk.AppImage", "org.infinityos.TwinDesk.desktop",
                            "video-display-symbolic"),
}


DRIVERS = {
    "xone": ("dlundqvist/xone", "f2aa9fe01103d7600553b505b298ff0bd47ff280",
             "a41601d1c4eb974fe5f9edd8e5ed45ef738e73b8f478e5e605cc59cd9a9960fc", "xone", "0.5.8"),
    "xpadneo": ("atar-axis/xpadneo", "e8f103a77f777c2c54536dd947969cf228699c13",
                "3e37e6d774ad6bd0e0f49d0854e30b715851b845520155cbaa428ca90d4780ac", "hid-xpadneo", "v0.10.5"),
}
XONE_FIRMWARES = {
    "02e6": ("https://catalog.s.download.windowsupdate.com/d/msdownload/update/driver/drvs/2017/03/2ea9591b-f751-442c-80ce-8f4692cdc67b_6b555a3a288153cf04aec6e03cba360afe2fce34.cab",
             "FW_ACC_00U.bin", "080ce4091e53a4ef3e5fe29939f51fd91f46d6a88be6d67eb6e99a5723b3a223"),
    "02fe": ("https://catalog.s.download.windowsupdate.com/c/msdownload/update/driver/drvs/2017/07/1cd6a87c-623f-4407-a52d-c31be49e925c_e19f60808bdcbfbd3c3df6be3e71ffc52e43261e.cab",
             "FW_ACC_00U.bin", "48084d9fa53b9bb04358f3bb127b7495dc8f7bb0b3ca1437bd24ef2b6eabdf66"),
    "02f9": ("https://catalog.s.download.windowsupdate.com/c/msdownload/update/driver/drvs/2017/06/1dbd7cb4-53bc-4857-a5b0-5955c8acaf71_9081931e7d664429a93ffda0db41b7545b7ac257.cab",
             "FW_ACC_CL.bin", "0023a7bae02974834500c665a281e25b1ba52c9226c84989f9084fa5ce591d9b"),
    "091e": ("https://catalog.s.download.windowsupdate.com/d/msdownload/update/driver/drvs/2017/08/aeff215c-3bc4-4d36-a3ea-e14bfa8fa9d2_e58550c4f74a27e51e5cb6868b10ff633fa77164.cab",
             "FW_ACC_BR.bin", "e2710daf81e7b36d35985348f68a81d18bc537a2b0c508ffdfde6ac3eae1bad7"),
}


APPS = (
    App("System", "Google Chrome", "flatpak", "com.google.Chrome", "Browse the web and sync bookmarks with Google.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Chromium", "flatpak", "org.chromium.Chromium", "Browse the web with an open-source browser.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Zen Browser", "flatpak", "app.zen_browser.zen", "Browse the web with tabs arranged in workspaces.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Opera", "flatpak", "com.opera.Opera", "Browse the web with a built-in sidebar.", True, group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Opera GX", "flatpak", "com.opera.opera-gx", "Browse the web with tools for gaming.", True, group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Brave", "flatpak", "com.brave.Browser", "Browse the web with built-in ad blocking.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "VLC", "flatpak", "org.videolan.VLC", "Play videos, music and online streams.", group="Media players", icon="applications-multimedia-symbolic"),
    App("System", "Spotify", "flatpak", "com.spotify.Client", "Listen to music and podcasts online.", True, group="Media players", icon="com.spotify.Client"),
    App("System", "mpv", "dnf", "mpv", "Play videos with a lightweight player.", group="Media players", icon="io.mpv.Mpv"),
    App("System", "qBittorrent", "flatpak", "org.qbittorrent.qBittorrent", "Download and manage torrents.", group="Download managers", icon="folder-download-symbolic"),
    App("System", "Transmission", "flatpak", "com.transmissionbt.Transmission", "Download torrents with a simple app.", group="Download managers", icon="folder-download-symbolic"),
    App("System", "JDownloader 2", "flatpak", "org.jdownloader.JDownloader", "Download files from many websites.", group="Download managers", icon="folder-download-symbolic"),
    App("System", "Thunderbird", "flatpak", "org.mozilla.thunderbird", "Manage email, calendars and contacts.", True, group="Email clients", icon="mail-unread-symbolic"),
    App("System", "Evolution", "flatpak", "org.gnome.Evolution", "Manage email, calendars and contacts in GNOME.", group="Email clients", icon="mail-unread-symbolic"),
    App("System", "BlueMail", "flatpak", "net.blix.BlueMail", "Read email from several accounts in one inbox.", True, group="Email clients", icon="mail-unread-symbolic"),
    App("System", "Mailspring", "flatpak", "com.getmailspring.Mailspring", "Read and organize email from several accounts.", group="Email clients", icon="mail-unread-symbolic"),
    App("System", "Safe Disk Cleaner", "github-appimage", "cyb3rl00m/safe-disk-cleaner", "See what uses disk space and remove unneeded files.", website="https://github.com/cyb3rl00m/safe-disk-cleaner", group="System maintenance", icon="io.github.cyb3rl00m.SafeDiskCleaner"),
    App("System", "TwinDesk", "github-appimage", "InukaAsith/TwinDesk", "Share screens, files and controls between devices.", True, website="https://github.com/InukaAsith/TwinDesk", group="Device tools", icon="video-display-symbolic"),
    App("System", "OpenLogi", "github-rpm", "AprilNEA/OpenLogi", "Set up Logitech mouse buttons and sensitivity.", website="https://github.com/AprilNEA/OpenLogi", group="Device tools", icon="openlogi"),
    App("System", "OpenRazer", "dnf", "openrazer-meta", "Enable and configure Razer gaming devices.", website="https://github.com/openrazer/openrazer", group="Device tools", icon="openrazer"),
    App("System", "WinBoat", "winboat-rpm", "winboat-org/winboat", "Run Windows easily on this system.", True, website="https://github.com/winboat-org/winboat", group="Windows apps", icon="winboat", package="winboat"),
    App("Gaming", "Steam", "dnf", "com.valvesoftware.Steam", "Buy, install and play games from Steam.", group="Game launchers", icon="applications-games-symbolic", package="steam"),
    App("Gaming", "Epic Games Launcher", "epic-native", "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncher-x86_64.deb", "Install the new native Epic Games Launcher Preview.", True, website="https://launcher.epicgames.com/", group="Game launchers", icon="epic-games-launcher"),
    App("Gaming", "Blizzard Battle.net", "lutris-installer", "battlenet-standard", "Install and play Blizzard games through Lutris.", True, website="https://download.battle.net/", group="Game launchers", icon="battle-net"),
    App("Gaming", "Nexus Launcher (Gamepass)", "github-appimage", "domsvoboda/nexus-launcher", "Play supported Game Pass and Microsoft Store games. Requires a purchase or subscription. ARM support is experimental.", website="https://github.com/domsvoboda/nexus-launcher", group="Game launchers", icon="nexus-launcher"),
    App("Gaming", "Heroic Games Launcher", "flatpak", "com.heroicgameslauncher.hgl", "Install and play games from Epic, GOG and Amazon.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Lutris", "flatpak", "net.lutris.Lutris", "Install and manage games from many stores.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Faugus Launcher", "flatpak", "io.github.Faugus.faugus-launcher", "Run Windows games on Linux with Wine.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Prism Launcher", "flatpak", "org.prismlauncher.PrismLauncher", "Manage Minecraft versions and modpacks.", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "OpenGamepadUI", "github-rpm", "shadowblip/OpenGamepadUI", "Browse and launch games using a controller.", group="Game launchers", icon="opengamepadui"),
    App("Gaming", "ProtonPlus", "flatpak", "com.vysp3r.ProtonPlus", "Install and update tools for Windows games.", website="https://protonplus.vysp3r.com/", group="Game launchers", icon="com.vysp3r.ProtonPlus"),
    App("Gaming", "Xbox Controller · USB / Dongle", "driver", "xone", "Use an Xbox controller by USB or wireless dongle.", website="https://github.com/dlundqvist/xone", group="Xbox Controller", icon="input-gaming-symbolic"),
    App("Gaming", "Xbox Controller · Bluetooth", "driver", "xpadneo", "Use an Xbox controller over Bluetooth.", website="https://github.com/atar-axis/xpadneo", group="Xbox Controller", icon="bluetooth-symbolic"),
    App("Gaming", "Discord", "discord-rpm", "com.discordapp.Discord", "Talk with friends by voice and text.", True, website="https://discord.com/download", group="Communication", icon="com.discordapp.Discord", package="discord"),
    App("Gaming", "Vesktop", "flatpak", "dev.vencord.Vesktop", "Use Discord with extra customization.", group="Communication", icon="mail-message-new-symbolic"),
    App("Gaming", "Bottles", "flatpak", "com.usebottles.bottles", "Run Windows apps in separate Wine environments.", True, group="Other", icon="applications-system-symbolic"),
    App("Creative", "PhotoCraft", "github-rpm", "storytold/photocraft", "The image editor you already know how to use.", website="https://github.com/storytold/photocraft", group="Image", icon="ai.storyteller.photocraft"),
    App("Creative", "VectorCraft", "github-rpm", "storytold/vectorcraft", "Vector illustration, with familiar tools and editable effects.", website="https://github.com/storytold/vectorcraft", group="Image", icon="ai.storyteller.vectorcraft"),
    App("Creative", "LightCraft", "github-rpm", "storytold/lightcraft", "Your photos. Your pixels. Your machine.", website="https://github.com/storytold/lightcraft", group="Image", icon="ai.storyteller.lightcraft"),
    App("Creative", "FilmCraft", "github-rpm", "storytold/filmcraft", "Professional video editing, rebuilt from scratch.", website="https://github.com/storytold/filmcraft", group="Video", icon="ai.storyteller.filmcraft"),
    App("Creative", "EffectCraft", "github-rpm", "storytold/effectcraft", "Motion graphics and visual effects.", website="https://github.com/storytold/effectcraft", group="Video", icon="ai.storyteller.effectcraft"),
    App("Creative", "DesignCraft", "github-rpm", "storytold/designcraft", "Page layout and publishing.", website="https://github.com/storytold/designcraft", group="Design", icon="ai.storyteller.designcraft"),
    App("Creative", "CADCraft", "github-rpm", "storytold/cadcraft", "Computer-aided drafting, with a familiar workflow.", website="https://github.com/storytold/cadcraft", group="Design", icon="ai.storyteller.cadcraft"),
    App("Creative", "FigCraft", "github-rpm", "storytold/figcraft", "Interface design and prototyping.", website="https://github.com/storytold/figcraft", group="Design", icon="ai.storyteller.figcraft"),
    App("Creative", "SolidCraft", "github-rpm", "tangency-labs/solidcraft", "Parametric 3D CAD, with editable sketches and solids.", website="https://github.com/tangency-labs/solidcraft", group="3D", icon="io.tangencylabs.solidcraft"),
    App("Creative", "MaterialCraft", "github-rpm", "storytold/materialcraft", "Build materials with node graphs.", website="https://github.com/storytold/materialcraft", group="3D", icon="ai.storyteller.materialcraft"),
    App("Creative", "TextureCraft", "github-rpm", "storytold/texturecraft", "Paint textures on 3D models.", website="https://github.com/storytold/texturecraft", group="3D", icon="ai.storyteller.texturecraft"),
    App("Creative", "SoundCraft", "github-rpm", "storytold/soundcraft", "Record, edit and mix your audio.", website="https://github.com/storytold/soundcraft", group="Audio", icon="ai.storyteller.soundcraft"),
    App("Creative", "GIMP", "flatpak", "org.gimp.GIMP", "Edit photos and other images.", group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Krita", "flatpak", "org.kde.krita", "Paint and draw digital art.", group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Inkscape", "flatpak", "org.inkscape.Inkscape", "Create and edit vector graphics.", group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Blender", "flatpak", "org.blender.Blender", "Create 3D models and animations.", True, group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Kdenlive", "flatpak", "org.kde.kdenlive", "Edit videos on a timeline.", group="More tools", icon="applications-multimedia-symbolic"),
    App("Creative", "OBS Studio", "flatpak", "com.obsproject.Studio", "Record your screen and stream video.", True, group="More tools", icon="applications-multimedia-symbolic"),
    App("Creative", "Audacity", "flatpak", "org.audacityteam.Audacity", "Record and edit audio.", group="More tools", icon="applications-multimedia-symbolic"),
    App("Programming", "Visual Studio Code", "flatpak", "com.visualstudio.code", "Write and edit code.", group="Development tools", icon="applications-development-symbolic"),
    App("Programming", "Craft Anything", "github-rpm", "storytold/craft-anything", "See how any website, app or game works, then build your own.", website="https://github.com/storytold/craft-anything", group="Development tools", icon="ai.storyteller.craft-anything"),
    App("Programming", "Docker CE", "dnf", "docker-ce", "Run apps in isolated containers.", group="Development tools", icon="docker"),
    App("AI", "Anthropic Claude + Claude Code CLI", "npm", "@anthropic-ai/claude-code", "Use Claude in the browser and terminal.", website="https://claude.ai/", group="Assistants", icon="infinity-claude"),
    App("AI", "OpenAI Codex + Codex CLI", "npm", "@openai/codex", "Install ChatGPT desktop and Codex CLI with InfinityTerminal integration.", website="https://chatgpt.com/codex", group="Assistants", icon="infinity-codex"),
    App("AI", "Qwen3.5 9B Q5 · 16 GB RAM", "local-model", "infinity-qwen-9b", "Run a local AI coding assistant. Needs 10 GB of disk space.", group="Local models", icon="infinity-ai"),
    App("AI", "Gemma 4 12B Q4 · 32 GB RAM", "local-model", "infinity-gemma-12b", "Run a local AI coding assistant. Needs 11 GB of disk space.", group="Local models", icon="infinity-ai"),
    App("AI", "Qwen3.5 35B A3B Q5 · 64 GB RAM", "local-model", "infinity-qwen-35b", "Run a local AI coding assistant. Needs 30 GB of disk space.", group="Local models", icon="infinity-ai"),
    App("Office", "EuroOffice", "github-rpm", "Euro-Office/DesktopEditors", "Create documents, spreadsheets and presentations.", website="https://github.com/Euro-Office/DesktopEditors", group="Office suite", icon="applications-office-symbolic", package="euro-office-euro-office"),
    App("Office", "LibreOffice", "flatpak", "org.libreoffice.LibreOffice", "Create documents, spreadsheets and presentations.", group="Office suite", icon="applications-office-symbolic"),
    App("Office", "PDFCraft", "github-rpm", "storytold/pdfcraft", "The open-source PDF workbench.", website="https://github.com/storytold/pdfcraft", group="Documents", icon="ai.storyteller.pdfcraft"),
    App("Office", "WordCraft", "github-rpm", "storytold/wordcraft", "The familiar word processor, native and offline.", website="https://github.com/storytold/wordcraft", group="Documents", icon="ai.storyteller.wordcraft"),
    App("Office", "GridCraft", "github-rpm", "storytold/gridcraft", "Spreadsheets you already know how to use.", website="https://github.com/storytold/gridcraft", group="Documents", icon="ai.storyteller.gridcraft"),
    App("Office", "DeckCraft", "github-rpm", "storytold/deckcraft", "Create slides, tell stories and present.", website="https://github.com/storytold/deckcraft", group="Documents", icon="ai.storyteller.deckcraft"),
)


def available(app, arch=None):
    if app.source == "com.valvesoftware.Steam":
        return (arch or os.uname().machine) in ("x86_64", "aarch64")
    return not app.x86_only or (arch or os.uname().machine) == "x86_64"


def active_local_model(home=None):
    path = Path(home or Path.home()) / ".config/infinityos/local-ai-model"
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def selected_ai(home=None):
    home = Path(home or Path.home())
    selected = [name for name in ("codex", "claude")
                if (home / f".local/bin/{name}").is_file()
                and (home / f".local/share/applications/infinityos-{name}.desktop").is_file()]
    if active_local_model(home):
        selected.append("local")
    return tuple(selected)


def ollama(path, data=None, timeout=30):
    request = urllib.request.Request("http://127.0.0.1:11434/api/" + path,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Content-Type": "application/json"})
    # Local requests must never travel through a configured HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError("Ollama request failed")
    return result



def valid_model(name):
    return isinstance(name, str) and len(name) <= 200 and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", name)) and ".." not in name



def downloaded_local_models():
    models = ollama('tags', timeout=2)['models']
    if not isinstance(models, list):
        raise ValueError('Invalid local model list')
    return tuple(m['name'] for m in models if isinstance(m, dict) and valid_model(m.get('name')))


def configured_apps(home=None, models=()):
    """Active selection and downloaded weights are independent state."""
    model = active_local_model(home)
    custom = ()
    if model and model not in LOCAL_MODELS:
        custom = (App("AI", model, "local-model", model,
                      "Manage this model in InfinityConfig.", group="Active custom model", icon="infinity-ai"),)
    known = {name.removesuffix(":latest") for name in (*LOCAL_MODELS, model or "")}
    downloaded = tuple(App("AI", name, "local-model", name,
                           "Manage this model in InfinityConfig.", group="Downloaded models", icon="infinity-ai")
                       for name in sorted(set(models)) if name.removesuffix(":latest") not in known)
    return (*custom, *APPS, *downloaded)


def deactivate_local_model(home=None):
    """Stop selecting a local model without deleting its downloaded weights."""
    (Path(home or Path.home()) / ".config/infinityos/local-ai-model").unlink(missing_ok=True)
    if shutil.which("gapplication"):
        subprocess.run(["gapplication", "action", "com.infinityos.GhosTTY",
                        "refresh-cli-tabs"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def removable(app, home=None, known_installed=None):
    """Allow removal of managed clients and individual CraftSuite applications."""
    if app.kind == "github-rpm" and app.source in CRAFT_SUITE:
        return installed(app, home) if known_installed is None else known_installed
    if app.source == "com.valvesoftware.Steam" or app.kind == "discord-rpm":
        return installed(app, home) if known_installed is None else known_installed
    if app.kind == "npm":
        command = "claude" if "anthropic" in app.source else "codex"
        return (Path(home or Path.home()) / ".local/bin" / command).exists()
    return False


def _flatpak_scopes(app):
    scopes = []
    for scope in ("--user", "--system"):
        try:
            result = subprocess.run(["flatpak", "info", scope, app.source],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    check=False)
        except OSError:
            continue
        if result.returncode == 0:
            scopes.append(scope)
    return scopes


def uninstall(app, home=None):
    if not removable(app, home):
        raise ValueError(f"No removable installation for {app.name}.")
    home = Path(home or Path.home())
    if app.kind == "discord-rpm":
        _run(["pkexec", "rpm", "-e", "--", "discord"])
        (home / ".local/share/applications/discord.desktop").unlink(missing_ok=True)
        return
    if app.kind == "github-rpm" and app.source in CRAFT_SUITE:
        # rpm refuses dependent removals instead of cascading to other apps.
        _run(["pkexec", "rpm", "-e", "--", app.package or app.source.rsplit("/", 1)[-1]])
        return
    if app.source == "com.valvesoftware.Steam":
        if os.uname().machine == "aarch64":
            # Keep steamapps and user settings while removing the managed client.
            shutil.rmtree(home / ".local/share/Steam/steamrtarm64")
            (home / ".local/share/applications/steam-arm64.desktop").unlink(missing_ok=True)
        else:
            _run(["pkexec", "rpm", "-e", "--", "steam"])
        return
    _run(["npm", "uninstall", "--global", "--prefix", str(home / ".local"), app.source])
    name = "claude" if "anthropic" in app.source else "codex"
    (home / f".local/share/applications/infinityos-{name}.desktop").unlink(missing_ok=True)
    if shutil.which("gapplication"):
        subprocess.run(["gapplication", "action", "com.infinityos.GhosTTY",
                        "refresh-cli-tabs"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def ollama_binary():
    upstream = Path("/usr/local/bin/ollama")
    return str(upstream) if upstream.exists() else shutil.which("ollama")


def installed_flatpaks():
    """Read installed Flatpak IDs once when building the application catalog."""
    applications = set()
    for scope in ("--user", "--system"):
        try:
            result = subprocess.run(
                ["flatpak", "list", scope, "--app", "--columns=application"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except OSError:
            return None
        if result.returncode:
            return None
        applications.update(result.stdout.splitlines())
    return applications


def installed(app, home=None, flatpak_ids=None, rpm_names=None, model_names=None):
    home = Path(home or Path.home())
    if app.source == "com.valvesoftware.Steam" and os.uname().machine == "aarch64":
        return (os.access(home / ".local/share/Steam/steamrtarm64/steam", os.X_OK) and
                (home / ".local/share/applications/steam-arm64.desktop").is_file())
    if app.kind == "epic-native":
        return ((home / ".local/share/infinityos/epic-launcher/current/usr/bin/EpicGamesLauncher").is_file() and
                (home / ".local/share/applications/epic-games-launcher.desktop").is_file())
    if app.kind == "github-appimage":
        binary, desktop = appimage_paths(app, home)
        return binary.is_file() and desktop.is_file()
    if app.kind == "local-model":
        if model_names is not None:
            return app.source.removesuffix(":latest") in {name.removesuffix(":latest") for name in model_names}
        ollama = ollama_binary()
        return bool(ollama and subprocess.run(
            [ollama, "show", app.source], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=15, check=False).returncode == 0)
    if app.kind == "flatpak":
        # Recognize existing Thunderbird installations while new installs use its current ID.
        ids = (app.source, "org.mozilla.Thunderbird", "org.mozilla.thunderbird_esr") if app.source == "org.mozilla.thunderbird" else (app.source,)
        if flatpak_ids is not None:
            return any(source in flatpak_ids for source in ids)
        return any(
            subprocess.run(["flatpak", "info", scope, source], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, check=False).returncode == 0
            for scope in ("--user", "--system") for source in ids
        )
    if app.kind == "npm":
        command = "claude" if "anthropic" in app.source else "codex"
        return command in selected_ai(home)
    if app.kind == "driver":
        return _driver_module_installed(app.source, DRIVERS[app.source][4]) and (
            app.source != "xone" or _xone_firmware_valid())
    package = app.package or (app.source.rsplit("/", 1)[-1].lower()
                              if app.kind == "github-rpm" else app.source)
    if rpm_names is not None:
        return package in rpm_names
    return subprocess.run(["rpm", "-q", package], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=15, check=False).returncode == 0


def catalog_state(home=None):
    """Collect slow installation state once, outside GTK's main thread."""
    flatpaks = installed_flatpaks()
    if flatpaks is None:
        raise RuntimeError('Could not read installed Flatpak applications.')
    result = subprocess.run(['rpm', '-qa', '--qf', '%{NAME}\n'], capture_output=True,
                            text=True, timeout=15, check=True)
    rpms = set(result.stdout.splitlines())
    try:
        models = downloaded_local_models()
    except (OSError, ValueError, KeyError, RuntimeError):
        models = ()
    apps = configured_apps(home, models)
    states = {app: available(app) and installed(app, home, flatpaks, rpms, models)
              for app in apps if app.kind != 'lutris-installer'}
    return flatpaks, models, states


def _run(command):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)
        output = "".join(char for char in output if char.isprintable() or char in "\n\t")
        if "EAI_AGAIN" in output:
            raise RuntimeError("Could not resolve the package server. Check your internet connection, then press APPLY to retry.")
        raise RuntimeError(output.strip()[-1000:] or f"Command failed with exit code {result.returncode}.")


def _driver_module_installed(driver, version=None):
    if not shutil.which("dkms"):
        return False
    module = DRIVERS[driver][3]
    result = subprocess.run(["dkms", "status", module], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, check=False, timeout=15)
    if result.returncode:
        return False
    return any(line.startswith(f"{module}/{version}," if version else f"{module}/") and
               "installed" in line and os.uname().release in line
               for line in result.stdout.splitlines())


def _xone_firmware_valid(firmware_dir=Path("/lib/firmware")):
    return all((firmware_dir / f"xone_dongle_{pid}.bin").is_file() and
               hashlib.sha256((firmware_dir / f"xone_dongle_{pid}.bin").read_bytes()).hexdigest() == expected
               for pid, (_, _, expected) in XONE_FIRMWARES.items())


def _verified_driver_source(driver, directory):
    repository, commit, expected, _, _ = DRIVERS[driver]
    url = f"https://codeload.github.com/{repository}/tar.gz/{commit}"
    request = urllib.request.Request(url, headers={"User-Agent": "InfinitySetup"})
    with urllib.request.urlopen(request, timeout=60) as response:
        archive = response.read(20_000_001)
    if len(archive) > 20_000_000 or hashlib.sha256(archive).hexdigest() != expected:
        raise RuntimeError(f"{driver} source archive failed checksum verification.")
    root_name = f"{repository.rsplit('/', 1)[-1]}-{commit}"
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        members = tar.getmembers()
        if any(not (member.isfile() or member.isdir()) or
               not (member.name == root_name or member.name.startswith(root_name + "/")) or
               ".." in Path(member.name).parts or member.name.startswith("/")
               for member in members):
            raise RuntimeError(f"{driver} source archive contains unsafe paths.")
        if sum(member.size for member in members) > 80_000_000:
            raise RuntimeError(f"{driver} source archive is too large.")
        for member in members:
            destination = Path(directory) / member.name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
                destination.chmod(member.mode & 0o777)
    return Path(directory) / root_name


def _install_xone_firmware(directory, firmware_dir=Path("/lib/firmware")):
    firmware_dir.mkdir(parents=True, exist_ok=True)
    for pid, (url, member, expected) in XONE_FIRMWARES.items():
        firmware = firmware_dir / f"xone_dongle_{pid}.bin"
        if firmware.is_file() and hashlib.sha256(firmware.read_bytes()).hexdigest() == expected:
            continue
        cab = Path(directory) / f"xone-{pid}.cab"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise RuntimeError(f"Xbox Wireless Adapter {pid} firmware archive is too large.")
        cab.write_bytes(payload)
        extracted = subprocess.run(["bsdtar", "-xOf", str(cab), member],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if extracted.returncode or hashlib.sha256(extracted.stdout).hexdigest() != expected:
            raise RuntimeError(f"Xbox Wireless Adapter {pid} firmware failed checksum verification.")
        temporary = firmware.with_suffix(".tmp")
        temporary.write_bytes(extracted.stdout)
        temporary.chmod(0o644)
        temporary.replace(firmware)
    legacy = firmware_dir / "xow_dongle.bin"
    if legacy.is_file() and hashlib.sha256(legacy.read_bytes()).hexdigest() == "48084d9fa53b9bb04358f3bb127b7495dc8f7bb0b3ca1437bd24ef2b6eabdf66":
        legacy.unlink()


def _old_xone_versions():
    result = subprocess.run(["dkms", "status", "xone"], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, check=False)
    return sorted({match.group(1) for line in result.stdout.splitlines()
                   if (match := re.match(r"^xone/([^,: ]+)", line))})


def _install_driver_as_root(driver):
    if os.geteuid() != 0 or driver not in DRIVERS:
        raise PermissionError("Controller driver installation requires root and a known driver.")
    kernel = os.uname().release
    build_dir = Path(f"/lib/modules/{kernel}/build")
    prerequisites = ["dkms", "gcc", "make", "kernel-headers"]
    if not build_dir.is_dir():
        prerequisites.append(f"kernel-devel-{kernel}")
    if driver == "xone":
        prerequisites.append("bsdtar")
    else:
        prerequisites.extend(("bluez", "bluez-tools"))
    _run(["dnf", "-y", "install", *prerequisites])
    if not build_dir.is_dir():
        raise RuntimeError(f"Kernel headers for {kernel} are missing. Update packages, reboot, then retry.")
    with tempfile.TemporaryDirectory(prefix="infinity-controller-") as directory:
        if not _driver_module_installed(driver, DRIVERS[driver][4]):
            source = _verified_driver_source(driver, directory)
            if driver == "xone":
                version = DRIVERS[driver][4]
                for old_version in _old_xone_versions():
                    _run(["dkms", "remove", "-m", "xone", "-v", old_version, "--all"])
                    old_source = Path("/usr/src") / f"xone-{old_version}"
                    if old_source.is_dir():
                        shutil.rmtree(old_source)
                destination = Path("/usr/src") / f"xone-{version}"
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
                for path in (*destination.rglob("dkms.conf"), *destination.rglob("*.c")):
                    contents = path.read_bytes()
                    if b"#VERSION#" in contents:
                        path.write_bytes(contents.replace(b"#VERSION#", version.encode()))
                if "clang" in Path("/proc/version").read_text(encoding="utf-8"):
                    with (destination / "dkms.conf").open("a", encoding="utf-8") as config:
                        config.write('MAKE[0]="make V=1 LLVM=1 -C ${kernel_source_dir} '
                                     'M=${dkms_tree}/${PACKAGE_NAME}/${PACKAGE_VERSION}/build"\n')
                _run(["dkms", "install", "-m", "xone", "-v", version])
                blacklist = Path("/etc/modprobe.d/xone-blacklist.conf")
                shutil.copyfile(destination / "install/modprobe.conf", blacklist)
            else:
                _run(["bash", str(source / "install.sh")])
        if driver == "xone":
            _install_xone_firmware(directory)
    _run(["depmod", "-a"])
    if driver == "xpadneo":
        _run(["systemctl", "enable", "--now", "bluetooth.service"])


def latest_rpm_asset(app, arch, timeout=30):
    request = urllib.request.Request(f"https://api.github.com/repos/{app.source}/releases/latest",
                                     headers={"User-Agent": "InfinitySetup"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        release = json.load(response)
    release_arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(arch, arch)
    suffixes = (f"-linux-{arch}.rpm", f".{arch}.rpm", f"-linux-{release_arch}.rpm", f"-{arch}.rpm")
    assets = [asset for asset in release.get("assets", ()) if asset["name"].endswith(suffixes)]
    if len(assets) > 1 and all(asset.get("digest") == assets[0].get("digest") for asset in assets):
        assets = [max(assets, key=lambda asset: len(asset["name"]))]
    if len(assets) != 1:
        raise RuntimeError(f"No unique {arch} RPM in the latest {app.name} release.")
    asset = assets[0]
    if Path(asset["name"]).name != asset["name"]:
        raise RuntimeError("Unexpected release filename.")
    digest = asset.get("digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise RuntimeError("Release has no supported SHA-256 checksum.")
    url = asset["browser_download_url"]
    if not url.casefold().startswith(
            f"https://github.com/{app.source}/releases/download/".casefold()):
        raise RuntimeError("Unexpected release download URL.")
    return release, asset


def _latest_rpm(app, arch, directory):
    _release, asset = latest_rpm_asset(app, arch)
    url = asset["browser_download_url"]
    destination = Path(directory) / asset["name"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "InfinitySetup"}), timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    if destination.stat().st_size != asset["size"]:
        raise RuntimeError("Release download size did not match GitHub metadata.")
    with destination.open("rb") as package:
        actual = hashlib.file_digest(package, "sha256").hexdigest()
    if actual.lower() != asset["digest"][7:].lower():
        raise RuntimeError("Release checksum verification failed.")
    destination.chmod(0o644)
    return destination


def latest_appimage_asset(app, arch, timeout=30):
    request = urllib.request.Request(f"https://api.github.com/repos/{app.source}/releases/latest",
                                     headers={"User-Agent": "InfinitySetup"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        release = json.load(response)
    assets = [asset for asset in release.get("assets", ())
              if asset["name"].endswith(tuple(f"-{name}.AppImage" for name in
                  (("aarch64", "arm64") if arch == "aarch64" else (arch,))))]
    if len(assets) != 1:
        raise RuntimeError(f"No unique {arch} AppImage in the latest {app.name} release.")
    asset = assets[0]
    if Path(asset["name"]).name != asset["name"]:
        raise RuntimeError("Unexpected AppImage asset name.")
    url = asset["browser_download_url"]
    if not url.startswith(f"https://github.com/{app.source}/releases/download/"):
        raise RuntimeError("Unexpected release download URL.")
    digest = asset.get("digest", "")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError("Release is missing a SHA256 digest for the AppImage.")
    return release, asset


def _latest_appimage(app, arch, directory):
    _release, asset = latest_appimage_asset(app, arch)
    url = asset["browser_download_url"]
    digest = asset["digest"]
    destination = Path(directory) / asset["name"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "InfinitySetup"}), timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    if destination.stat().st_size != asset["size"]:
        raise RuntimeError("AppImage download size did not match GitHub metadata.")
    with destination.open("rb") as package:
        actual = hashlib.file_digest(package, "sha256").hexdigest()
    if actual != digest.removeprefix("sha256:"):
        raise RuntimeError("AppImage checksum verification failed.")
    with destination.open("rb") as downloaded:
        header = downloaded.read(20)
    machine = {"x86_64": 62, "aarch64": 183}.get(arch)
    if (destination.stat().st_size < 4096 or header[:4] != b"\x7fELF" or
            header[4:6] != b"\x02\x01" or header[8:11] != b"AI\x02" or
            machine is None or int.from_bytes(header[18:20], "little") != machine):
        raise RuntimeError("Release download is not an AppImage.")
    return destination


def appimage_paths(app, home=None):
    binary, desktop, _icon = GITHUB_APPIMAGES[app.source]
    home = Path(home or Path.home())
    return home / ".local/bin" / binary, home / ".local/share/applications" / desktop


def _install_github_appimage(app, home):
    binary, desktop = appimage_paths(app, home)
    icon = GITHUB_APPIMAGES[app.source][2]
    binary.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="infinity-appimage-") as directory:
        package = _latest_appimage(app, os.uname().machine, directory)
        temporary = binary.with_suffix(".tmp")
        shutil.copyfile(package, temporary)
        temporary.chmod(0o755)
        temporary.replace(binary)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        f"[Desktop Entry]\nType=Application\nName={app.name}\n"
        f'Exec=env APPIMAGE_EXTRACT_AND_RUN=1 "{binary}"\n'
        f"Icon={icon}\n"
        "Terminal=false\nCategories=GTK;System;Utility;\n",
        encoding="utf-8",
    )


def _install_steam_rpm(app):
    packages = ["steam", "mesa-dri-drivers.x86_64", "mesa-dri-drivers.i686",
                "mesa-vulkan-drivers-freeworld.x86_64", "mesa-vulkan-drivers-freeworld.i686",
                "mesa-va-drivers-freeworld.x86_64", "mesa-va-drivers-freeworld.i686"]
    # Keep the 32-bit NVIDIA libraries on the already installed driver branch.
    for driver in ("xorg-x11-drv-nvidia-libs", "xorg-x11-drv-nvidia-470xx-libs",
                   "xorg-x11-drv-nvidia-390xx-libs"):
        if subprocess.run(["rpm", "-q", f"{driver}.x86_64"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False).returncode == 0:
            packages.extend((f"{driver}.x86_64", f"{driver}.i686"))
    _run(["pkexec", "dnf", "--refresh", "-y", "install", *packages])
    # Remove the old launcher only after the RPM transaction succeeds.
    for scope in _flatpak_scopes(app):
        command = ["flatpak", "uninstall", scope, "--noninteractive", "--assumeyes", app.source]
        _run(["pkexec", *command] if scope == "--system" else command)


def install(app, home=None, *, defer_system_dependencies=False):
    """Install one selected app. Calling this is the only installation trigger."""
    home = Path(home or Path.home())
    if app.source == "com.valvesoftware.Steam" and os.uname().machine == "aarch64":
        _install_arm_steam(home, install_dependencies=not defer_system_dependencies)
    elif app.source == "com.valvesoftware.Steam":
        _install_steam_rpm(app)
    elif app.kind == "discord-rpm":
        if os.uname().machine != "x86_64":
            raise RuntimeError("Discord's official RPM requires x64.")
        _run(["pkexec", "dnf", "-y", "install",
              "https://discord.com/api/download?platform=linux&format=rpm"])
        desktop = home / ".local/share/applications/discord.desktop"
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            "[Desktop Entry]\nType=Application\nName=Discord\n"
            "Exec=/usr/bin/discord --ozone-platform=wayland --url -- %u\n"
            "Icon=discord\nStartupWMClass=discord\nTerminal=false\n"
            "Categories=Network;InstantMessaging;\nMimeType=x-scheme-handler/discord;\n",
            encoding="utf-8",
        )
        # Keep the Flatpak profile; remove its launcher only after RPM installation succeeds.
        for scope in _flatpak_scopes(app):
            command = ["flatpak", "uninstall", scope, "--noninteractive", "--assumeyes", app.source]
            _run(["pkexec", *command] if scope == "--system" else command)
    elif app.kind == "local-model":
        _install_local_model(app, home)
    elif app.kind == "epic-native":
        _install_epic_native(app, home)
    elif app.kind == "github-appimage":
        if app.source not in GITHUB_APPIMAGES:
            raise ValueError(f"No AppImage installation source for {app.name}.")
        if app.source == "domsvoboda/nexus-launcher":
            _run(["pkexec", "dnf", "-y", "install", "curl", "tar", "xz", "fuse",
                  "webkit2gtk4.1", "gtk3", "nss", "libXtst", "alsa-lib", "desktop-file-utils"])
        _install_github_appimage(app, home)
    elif app.kind == "flatpak":
        _run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
              "https://dl.flathub.org/repo/flathub.flatpakrepo"])
        _run(["flatpak", "install", "--user", "--noninteractive", "--assumeyes", "flathub", app.source])
    elif app.kind == "github-rpm":
        with tempfile.TemporaryDirectory(prefix="infinity-setup-") as directory:
            package = _latest_rpm(app, os.uname().machine, directory)
            _run(["pkexec", "dnf", "-y", "install", str(package)])
    elif app.kind == "winboat-rpm":
        with tempfile.TemporaryDirectory(prefix="infinity-setup-") as directory:
            package = _latest_rpm(app, os.uname().machine, directory)
            _run(["pkexec", "dnf", "-y", "install", "podman", "podman-compose",
                  "freerdp", str(package)])
    elif app.kind == "driver":
        if app.source not in DRIVERS:
            raise ValueError(f"Unknown controller driver: {app.source}")
        _run(["pkexec", "/usr/bin/python3", str(Path(__file__).resolve()),
              "--install-driver", app.source])
    elif app.kind == "dnf":
        if app.source == "mpv":
            _run(["pkexec", "dnf", "-y", "install", "mpv"])
        elif app.source == "docker-ce":
            if not Path("/etc/yum.repos.d/docker-ce.repo").exists():
                _run(["pkexec", "dnf", "config-manager", "addrepo", "--from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo"])
            _run(["pkexec", "dnf", "--enablerepo=docker-ce-stable", "-y", "install", "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"])
            _run(["pkexec", "systemctl", "enable", "--now", "docker.service"])
        elif app.source == "openrazer-meta":
            _run(["pkexec", "dnf", "config-manager", "addrepo", "--from-repofile=https://openrazer.github.io/hardware:razer.repo"])
            _run(["pkexec", "dnf", "-y", "install", "kernel-devel", "openrazer-meta"])
            _run(["pkexec", "groupadd", "-f", "plugdev"])
            _run(["pkexec", "gpasswd", "-a", pwd.getpwuid(os.getuid()).pw_name, "plugdev"])
        else:
            raise ValueError(f"No DNF installation source for {app.name}.")
    elif app.kind == "npm":
        if app.source == "@openai/codex":
            arch = os.uname().machine
            if arch not in ("x86_64", "aarch64"):
                raise RuntimeError("ChatGPT desktop requires x64 or ARM64.")
            # The official RPM also configures OpenAI's repository for later updates.
            _run(["pkexec", "dnf", "-y", "install",
                  f"https://persistent.oaistatic.com/codex-app-prod/linux/rpm/latest/chatgpt.{arch}.rpm"])
        if not shutil.which("npm"):
            _run(["pkexec", "dnf", "-y", "install", "nodejs-npm"])
        _run(["npm", "install", "--global", "--prefix", str(home / ".local"), app.source])
        desktop_dir = home / ".local/share/applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        name = "Claude" if "anthropic" in app.source else "Codex"
        desktop = desktop_dir / f"infinityos-{name.lower()}.desktop"
        desktop.write_text(
            "[Desktop Entry]\nType=Application\n"
            f"Name={name}\nExec=firefox --new-window {app.website}\n"
            "Icon=web-browser\nCategories=Network;\n",
            encoding="utf-8",
        )
        if shutil.which("gapplication"):
            subprocess.run(
                ["gapplication", "action", "com.infinityos.GhosTTY", "refresh-cli-tabs"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
    else:
        raise ValueError(f"No installation source for {app.name}.")


def _steam_arm_manifest_entry(manifest):
    section = re.search(r'"bins_linuxarm64_linuxarm64"\s*\{([^{}]+)\}', manifest)
    if not section:
        raise RuntimeError("Valve's ARM64 Steam client is missing from the update manifest.")
    fields = dict(re.findall(r'^\s*"(file|size|sha2)"\s*"([^"]+)"',
                             section.group(1), re.MULTILINE))
    filename = fields.get("file", "")
    digest = fields.get("sha2", "")
    size = int(fields.get("size", "0"))
    if (not re.fullmatch(r"bins_linuxarm64_linuxarm64\.zip\.[0-9a-f]{40}", filename)
            or not re.fullmatch(r"[0-9a-f]{64}", digest) or not 0 < size < 500_000_000):
        raise RuntimeError("Invalid ARM64 Steam client metadata from Valve.")
    return filename, digest, size


def _install_arm_steam(home, install_dependencies=True):
    """Install Valve's native ARM64 beta client from its checksummed manifest."""
    manifest_url = "https://client-update.fastly.steamstatic.com/steam_client_publicbeta_linuxarm64"
    with urllib.request.urlopen(manifest_url, timeout=30) as response:
        manifest = response.read(2_000_001)
    if len(manifest) > 2_000_000:
        raise RuntimeError("Steam update manifest is too large.")
    filename, digest, size = _steam_arm_manifest_entry(manifest.decode("utf-8"))
    share = home / ".local/share"
    share.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="infinity-steam-", dir=share) as directory:
        staging = Path(directory)
        archive = staging / "client.zip"
        url = f"https://client-update.steamstatic.com/{filename}"
        request = urllib.request.Request(url, headers={"User-Agent": "InfinitySetup"})
        sha = hashlib.sha256()
        received = 0
        with urllib.request.urlopen(request, timeout=90) as response, archive.open("wb") as output:
            if urllib.parse.urlsplit(response.geturl()).hostname not in (
                    "client-update.steamstatic.com", "client-update.fastly.steamstatic.com"):
                raise RuntimeError("Unexpected Steam download host.")
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > size:
                    raise RuntimeError("Steam client archive exceeds the manifest size.")
                sha.update(chunk)
                output.write(chunk)
        if received != size or sha.hexdigest() != digest:
            raise RuntimeError("Steam client archive failed size or SHA-256 verification.")
        extracted = staging / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(archive) as client:
            members = client.infolist()
            if sum(member.file_size for member in members) > 1_000_000_000:
                raise RuntimeError("Steam client archive expands beyond the expected size.")
            for member in members:
                # Valve's zip mixes Unix and Windows path separators.
                path = PurePosixPath(member.filename.replace("\\", "/"))
                if not path.parts or path.is_absolute() or ".." in path.parts:
                    raise RuntimeError("Steam client archive contains an unsafe path.")
                destination = extracted.joinpath(*path.parts)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif stat.S_ISLNK(member.external_attr >> 16):
                    if member.file_size > 4096:
                        raise RuntimeError("Steam client archive contains an unsafe link.")
                    target = client.read(member).decode("utf-8")
                    link = PurePosixPath(target.replace("\\", "/"))
                    if not link.parts or link.is_absolute() or ".." in link.parts:
                        raise RuntimeError("Steam client archive contains an unsafe link.")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.symlink_to(str(link))
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with client.open(member) as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)
        binary = extracted / "steamrtarm64/steam"
        if not binary.is_file():
            raise RuntimeError("Valve's ARM64 Steam archive has no client binary.")
        if install_dependencies:
            _run(["pkexec", "dnf", "-y", "install", "libva", "libvpx", "ibus-libs"])
        steam_root = share / "Steam"
        for link in extracted.rglob("*"):
            if link.is_symlink():
                destination = steam_root / link.relative_to(extracted)
                if destination.exists() or destination.is_symlink():
                    destination.unlink()
        shutil.copytree(extracted, steam_root, dirs_exist_ok=True, symlinks=True)
    for name in ("steam", "steamwebhelper", "steamwebhelper.sh", "steam_monitor",
                 "reaper", "gameoverlayui", "gldriverquery", "steamsysinfo",
                 "steamerrorreporter", "streaming_client", "fossilize_replay",
                 "vulkandriverquery", "vgui_panel_zoo"):
        executable = steam_root / "steamrtarm64" / name
        if executable.is_file():
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    binary = steam_root / "steamrtarm64/steam"
    (steam_root / "package").mkdir(exist_ok=True)
    (steam_root / "package/beta").write_text("publicbeta\n", encoding="utf-8")
    dot_steam = home / ".steam"
    dot_steam.mkdir(exist_ok=True)
    for link, target in (("steam", steam_root), ("root", steam_root),
                         ("sdkarm64", steam_root / "linuxarm64")):
        destination = dot_steam / link
        if not destination.exists() and not destination.is_symlink():
            destination.symlink_to(target)
    desktop = share / "applications/steam-arm64.desktop"
    desktop.parent.mkdir(exist_ok=True)
    desktop.write_text("[Desktop Entry]\nType=Application\nName=Steam ARM64 (Beta)\n"
                       f'Exec="{binary}"\n'
                       "Icon=/usr/share/infinityos/launcher-icons/com.valvesoftware.Steam.png\n"
                       "Categories=Game;\n", encoding="utf-8")


def open_lutris_installer(app):
    """Install Lutris if needed, then open its interactive Windows installer."""
    if app.kind != "lutris-installer":
        raise ValueError(f"No Lutris installer for {app.name}.")
    command = shutil.which("lutris")
    if not command:
        lutris = next(item for item in APPS if item.name == "Lutris")
        if not installed(lutris):
            install(lutris)
        command = ["flatpak", "run", "net.lutris.Lutris"]
    else:
        command = [command]
    subprocess.Popen(
        [*command, f"lutris:install/{app.source}"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _install_epic_native(app, home):
    root = home / ".local/share/infinityos/epic-launcher"
    root.mkdir(parents=True, exist_ok=True)
    desktop = home / ".local/share/applications/epic-games-launcher.desktop"
    with tempfile.TemporaryDirectory(dir=root, prefix=".download-") as directory:
        directory = Path(directory)
        package = directory / "launcher.deb"
        request = urllib.request.Request(app.source, headers={"User-Agent": "InfinitySetup"})
        with urllib.request.urlopen(request, timeout=60) as response, package.open("wb") as output:
            url = urllib.parse.urlsplit(response.geturl())
            if url.scheme != "https" or not (url.hostname or "").endswith(".epicgames.com"):
                raise RuntimeError("Unexpected Epic Games download URL.")
            expected_size = response.headers.get("Content-Length")
            shutil.copyfileobj(response, output)
        if expected_size and package.stat().st_size != int(expected_size):
            raise RuntimeError("Epic Games download size did not match server metadata.")
        payload = None
        with package.open("rb") as archive:
            if archive.read(8) != b"!<arch>\n":
                raise RuntimeError("Epic Games download is not a Debian package.")
            while header := archive.read(60):
                if len(header) != 60 or header[58:] != b"`\n":
                    raise RuntimeError("Invalid Debian archive header.")
                size = int(header[48:58])
                if not 0 <= size <= 512 * 1024 * 1024:
                    raise RuntimeError("Unexpected Debian archive member size.")
                if header[:16].strip().rstrip(b"/").startswith(b"data.tar."):
                    payload = archive.read(size)
                    if len(payload) != size:
                        raise RuntimeError("Incomplete Debian archive.")
                    break
                archive.seek(size + size % 2, 1)
        if payload is None:
            raise RuntimeError("Epic Games package has no application payload.")
        extracted = directory / "app"
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            archive.extractall(extracted, filter="data")
        binary = extracted / "usr/bin/EpicGamesLauncher"
        with binary.open("rb") as executable:
            header = executable.read(20)
        if header[:5] != b"\x7fELF\x02" or header[18:20] != b"\x3e\x00":
            raise RuntimeError("Epic Games package is not a Linux x64 application.")
        if not (extracted / "usr/lib/epic-games-launcher/libEOSSDK-Linux-Shipping.so").is_file():
            raise RuntimeError("Epic Games package is missing its runtime library.")
        _run(["pkexec", "dnf", "-y", "install", "webkit2gtk4.1", "gtk3", "libayatana-appindicator-gtk3"])
        binary.chmod(0o755)
        with package.open("rb") as downloaded:
            version = hashlib.file_digest(downloaded, "sha256").hexdigest()
        destination = root / version
        if not destination.exists():
            extracted.rename(destination)
        desktop.parent.mkdir(parents=True, exist_ok=True)
        previous = desktop.read_bytes() if desktop.exists() else None
        temporary = desktop.with_suffix(".tmp")
        temporary.write_text(
            "[Desktop Entry]\nType=Application\nName=Epic Games Launcher\n"
            f'Exec="{root}/current/usr/bin/EpicGamesLauncher" %u\n'
            "Icon=/usr/share/infinityos/launcher-icons/epic-games-launcher.svg\n"
            "Terminal=false\nCategories=Game;\nStartupWMClass=EpicGamesLauncher\n"
            "MimeType=x-scheme-handler/com.epicgames.launcher;\n", encoding="utf-8")
        link = directory / "current"
        link.symlink_to(destination.name)
        try:
            temporary.replace(desktop)
            link.replace(root / "current")
        except Exception:
            if previous is None:
                desktop.unlink(missing_ok=True)
            else:
                desktop.write_bytes(previous)
            raise



def _install_local_model(app, home):
    model = LOCAL_MODELS.get(app.source)

    ollama = ollama_binary()
    needs_model = not ollama or subprocess.run([ollama, "show", app.source],
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL, check=False).returncode != 0
    # Fail before installing runtimes when the selected weights cannot fit.
    if needs_model:
        if model is None:
            raise RuntimeError("Import this model again in InfinityConfig.")
        if shutil.disk_usage(home).free < model.disk_gb * 1_000_000_000:
            raise RuntimeError(f"At least {model.disk_gb} GB of free disk space is required.")
        # Fedora's Ollama can predate newly released GGUF architectures. The
        # upstream installer provides the runtime that understands these models.
        with tempfile.TemporaryDirectory(prefix="infinity-ollama-") as directory:
            script = Path(directory) / "install.sh"
            with urllib.request.urlopen("https://ollama.com/install.sh", timeout=30) as response:
                script.write_bytes(response.read())
            _run(["pkexec", "sh", str(script)])
        ollama = ollama_binary()
        if not ollama:
            raise RuntimeError("Ollama installation did not provide an executable.")

    if not (shutil.which("opencode") or (home / ".local/bin/opencode").exists()):
        if not shutil.which("npm"):
            _run(["pkexec", "dnf", "-y", "install", "nodejs-npm"])
        _run(["npm", "install", "--global", "--prefix", str(home / ".local"),
              "opencode-ai@1.19.5"])

    _run(["pkexec", "systemctl", "enable", "--now", "ollama.service"])
    if needs_model:
        _run([ollama, "pull", model.remote])
        with tempfile.TemporaryDirectory(prefix="infinity-model-") as directory:
            modelfile = Path(directory) / "Modelfile"
            modelfile.write_text(f"FROM {model.remote}\nPARAMETER num_ctx 65536\n", encoding="utf-8")
            _run([ollama, "create", app.source, "-f", str(modelfile)])

    config = home / ".config/infinityos/local-ai-model"
    config.parent.mkdir(parents=True, exist_ok=True)
    previous = config.read_bytes() if config.exists() else None
    temporary = config.with_suffix(".tmp")
    temporary.write_text(app.source + "\n", encoding="utf-8")
    temporary.replace(config)
    try:
        _run(["/usr/bin/infinity-local-ai", "--check"])
    except Exception:
        if previous is None:
            config.unlink(missing_ok=True)
        else:
            config.write_bytes(previous)
        raise
    if shutil.which("gapplication"):
        subprocess.run(["gapplication", "action", "com.infinityos.GhosTTY",
                        "refresh-cli-tabs"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--install-driver":
        raise SystemExit("Usage: launcher_backend.py --install-driver xone|xpadneo")
    _install_driver_as_root(sys.argv[2])
