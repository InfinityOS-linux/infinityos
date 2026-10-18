"""Application catalog and deferred installation for InfinityLauncher."""

import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
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


LOCAL_MODELS = {
    "infinity-qwen-9b": LocalModel("hf.co/unsloth/Qwen3.5-9B-GGUF:UD-Q5_K_XL", 10),
    "infinity-gemma-12b": LocalModel("hf.co/unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL", 11),
    "infinity-qwen-35b": LocalModel("hf.co/unsloth/Qwen3.5-35B-A3B-GGUF:UD-Q5_K_XL", 30),
}


APPS = (
    App("System", "Google Chrome", "flatpak", "com.google.Chrome", "Google's web browser with account sync.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Chromium", "flatpak", "org.chromium.Chromium", "Open-source Chromium web browser.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Zen Browser", "flatpak", "app.zen_browser.zen", "Firefox-based browser with a focused workspace.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Opera", "flatpak", "com.opera.Opera", "Web browser with built-in sidebar tools.", True, group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Opera GX", "flatpak", "com.opera.opera-gx", "Gaming browser with performance controls.", True, group="Web browsers", icon="web-browser-symbolic"),
    App("System", "Brave", "flatpak", "com.brave.Browser", "Privacy-focused Chromium browser.", group="Web browsers", icon="web-browser-symbolic"),
    App("System", "VLC", "flatpak", "org.videolan.VLC", "Play video, audio and network streams.", group="Media players", icon="applications-multimedia-symbolic"),
    App("System", "Spotify", "flatpak", "com.spotify.Client", "Stream music, podcasts and audiobooks.", group="Media players", icon="com.spotify.Client"),
    App("System", "mpv", "flatpak", "io.mpv.Mpv", "Lightweight video player with keyboard controls.", group="Media players", icon="applications-multimedia-symbolic"),
    App("System", "qBittorrent", "flatpak", "org.qbittorrent.qBittorrent", "Torrent client with search and queue controls.", group="Download managers", icon="folder-download-symbolic"),
    App("System", "Transmission", "flatpak", "com.transmissionbt.Transmission", "Simple, lightweight torrent client.", group="Download managers", icon="folder-download-symbolic"),
    App("System", "JDownloader 2", "flatpak", "org.jdownloader.JDownloader", "Download files from many hosting services.", group="Download managers", icon="folder-download-symbolic"),
    App("System", "Thunderbird", "flatpak", "org.mozilla.Thunderbird", "Email, calendar and contacts.", True, group="Email clients", icon="mail-unread-symbolic"),
    App("System", "Evolution", "flatpak", "org.gnome.Evolution", "GNOME email, calendar and contacts.", group="Email clients", icon="mail-unread-symbolic"),
    App("System", "BlueMail", "flatpak", "net.blix.BlueMail", "Email client with a unified inbox.", True, group="Email clients", icon="mail-unread-symbolic"),
    App("System", "Mailspring", "flatpak", "com.getmailspring.Mailspring", "Email client with a modern inbox.", group="Email clients", icon="mail-unread-symbolic"),
    App("System", "OpenLogi", "github-rpm", "AprilNEA/OpenLogi", "Configure Logitech mouse buttons, DPI and SmartShift locally.", website="https://github.com/AprilNEA/OpenLogi", group="Device tools", icon="openlogi"),
    App("System", "OpenRazer", "dnf", "openrazer-meta", "Drivers and daemon for Razer devices; restart after installation.", website="https://github.com/openrazer/openrazer", group="Device tools", icon="input-gaming-symbolic"),
    App("Gaming", "Steam", "flatpak", "com.valvesoftware.Steam", "Steam games and store.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Epic Games Launcher", "epic-appimage", "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncher-x86_64.AppImage", "Native Linux Preview from Epic Games.", True, website="https://launcher.epicgames.com/", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Blizzard Battle.net", "lutris-installer", "battlenet-standard", "Windows launcher; install through Lutris and Wine.", True, website="https://download.battle.net/", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Heroic Games Launcher", "flatpak", "com.heroicgameslauncher.hgl", "Epic, GOG and Amazon games.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Lutris", "flatpak", "net.lutris.Lutris", "Games from multiple stores.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Faugus Launcher", "flatpak", "io.github.Faugus.faugus-launcher", "Windows games with Wine.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Prism Launcher", "flatpak", "org.prismlauncher.PrismLauncher", "Minecraft instances and modpacks.", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "OpenGamepadUI", "github-rpm", "shadowblip/OpenGamepadUI", "Controller-first game library.", group="Game launchers", icon="opengamepadui"),
    App("Gaming", "Discord", "flatpak", "com.discordapp.Discord", "Voice and text chat.", True, group="Communication", icon="mail-message-new-symbolic"),
    App("Gaming", "Vesktop", "flatpak", "dev.vencord.Vesktop", "Alternative Discord client.", group="Communication", icon="mail-message-new-symbolic"),
    App("Gaming", "Bottles", "flatpak", "com.usebottles.bottles", "Wine environments for Windows apps.", True, group="Other", icon="applications-system-symbolic"),
    App("Creative", "PhotoCraft", "github-rpm", "storytold/photocraft", "Adobe-style photo editor clone.", website="https://github.com/storytold/photocraft", group="Image", icon="ai.storyteller.photocraft"),
    App("Creative", "VectorCraft", "github-rpm", "storytold/vectorcraft", "Adobe-style vector editor clone.", website="https://github.com/storytold/vectorcraft", group="Image", icon="ai.storyteller.vectorcraft"),
    App("Creative", "LightCraft", "github-rpm", "storytold/lightcraft", "Adobe-style photo workflow clone.", website="https://github.com/storytold/lightcraft", group="Image", icon="ai.storyteller.lightcraft"),
    App("Creative", "FilmCraft", "github-rpm", "storytold/filmcraft", "Adobe-style video editor clone.", website="https://github.com/storytold/filmcraft", group="Video", icon="ai.storyteller.filmcraft"),
    App("Creative", "EffectCraft", "github-rpm", "storytold/effectcraft", "Adobe-style visual effects clone.", website="https://github.com/storytold/effectcraft", group="Video", icon="ai.storyteller.effectcraft"),
    App("Creative", "DesignCraft", "github-rpm", "storytold/designcraft", "Adobe-style layout editor clone.", website="https://github.com/storytold/designcraft", group="Design", icon="ai.storyteller.designcraft"),
    App("Creative", "CADCraft", "github-rpm", "storytold/cadcraft", "Adobe-style 3D design clone.", website="https://github.com/storytold/cadcraft", group="Design", icon="ai.storyteller.cadcraft"),
    App("Creative", "GIMP", "flatpak", "org.gimp.GIMP", "Edit raster images.", group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Krita", "flatpak", "org.kde.krita", "Paint and illustrate.", group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Inkscape", "flatpak", "org.inkscape.Inkscape", "Edit vector graphics.", group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Blender", "flatpak", "org.blender.Blender", "Model and animate in 3D.", True, group="More tools", icon="applications-graphics-symbolic"),
    App("Creative", "Kdenlive", "flatpak", "org.kde.kdenlive", "Edit videos on a timeline.", group="More tools", icon="applications-multimedia-symbolic"),
    App("Creative", "OBS Studio", "flatpak", "com.obsproject.Studio", "Record and stream your screen.", True, group="More tools", icon="applications-multimedia-symbolic"),
    App("Creative", "Audacity", "flatpak", "org.audacityteam.Audacity", "Record and edit audio.", group="More tools", icon="applications-multimedia-symbolic"),
    App("Programming", "Visual Studio Code", "flatpak", "com.visualstudio.code", "Microsoft's code editor.", group="Development tools", icon="applications-development-symbolic"),
    App("Programming", "Docker CE", "dnf", "docker-ce", "Docker's official packages. Use sudo unless you configure user access.", group="Development tools", icon="docker"),
    App("AI", "Anthropic Claude + Claude Code CLI", "npm", "@anthropic-ai/claude-code", "CLI and Claude web shortcut. Adds a pinned terminal tab.", website="https://claude.ai/", group="Assistants", icon="infinity-claude"),
    App("AI", "OpenAI Codex + Codex CLI", "npm", "@openai/codex", "CLI and Codex web shortcut. Adds a pinned terminal tab.", website="https://chatgpt.com/codex", group="Assistants", icon="infinity-codex"),
    App("AI", "Qwen3.5 9B Q5 · 16 GB RAM", "local-model", "infinity-qwen-9b", "For 16 GB RAM. Needs about 10 GB free disk; local coding agent.", group="Local models", icon="infinity-ai"),
    App("AI", "Gemma 4 12B Q4 · 32 GB RAM", "local-model", "infinity-gemma-12b", "For 24–32 GB RAM. Needs about 11 GB free disk; local coding agent.", group="Local models", icon="infinity-ai"),
    App("AI", "Qwen3.5 35B A3B Q5 · 64 GB RAM", "local-model", "infinity-qwen-35b", "For 64 GB RAM. Needs about 30 GB free disk; local coding agent.", group="Local models", icon="infinity-ai"),
    App("Office", "EuroOffice", "github-rpm", "Euro-Office/DesktopEditors", "Documents, spreadsheets, presentations and PDFs.", website="https://github.com/Euro-Office/DesktopEditors", group="Office suite", icon="applications-office-symbolic", package="euro-office-euro-office"),
    App("Office", "LibreOffice", "flatpak", "org.libreoffice.LibreOffice", "Documents, presentations and spreadsheets.", group="Office suite", icon="applications-office-symbolic"),
    App("Office", "PDFCraft", "github-rpm", "storytold/pdfcraft", "Adobe-style PDF editor clone.", website="https://github.com/storytold/pdfcraft", group="Documents", icon="ai.storyteller.pdfcraft"),
    App("Office", "WordCraft", "github-rpm", "storytold/wordcraft", "Adobe-style document editor clone.", website="https://github.com/storytold/wordcraft", group="Documents", icon="ai.storyteller.wordcraft"),
    App("Office", "DeckCraft", "github-rpm", "storytold/deckcraft", "Adobe-style presentation editor clone.", website="https://github.com/storytold/deckcraft", group="Documents", icon="ai.storyteller.deckcraft"),
)


def available(app, arch=None):
    return not app.x86_only or (arch or os.uname().machine) == "x86_64"


def active_local_model(home=None):
    path = Path(home or Path.home()) / ".config/infinityos/local-ai-model"
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def ollama_binary():
    upstream = Path("/usr/local/bin/ollama")
    return str(upstream) if upstream.exists() else shutil.which("ollama")


def installed(app, home=None):
    home = Path(home or Path.home())
    if app.kind == "epic-appimage":
        return ((home / ".local/bin/EpicGamesLauncher.AppImage").is_file() and
                (home / ".local/share/applications/epic-games-launcher.desktop").is_file())
    if app.kind == "local-model":
        ollama = ollama_binary()
        opencode = shutil.which("opencode") or (home / ".local/bin/opencode")
        return bool(ollama and Path(opencode).exists() and subprocess.run(
            [ollama, "show", app.source], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False).returncode == 0)
    if app.kind == "flatpak":
        return any(
            subprocess.run(["flatpak", "info", scope, app.source], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False).returncode == 0
            for scope in ("--user", "--system")
        )
    if app.kind == "npm":
        command = "claude" if "anthropic" in app.source else "codex"
        return (home / ".local/bin" / command).exists() or shutil.which(command) is not None
    package = app.package or (app.source.rsplit("/", 1)[-1].lower()
                              if app.kind == "github-rpm" else app.source)
    return subprocess.run(["rpm", "-q", package], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False).returncode == 0


def _run(command):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)
        output = "".join(char for char in output if char.isprintable() or char in "\n\t")
        if "EAI_AGAIN" in output:
            raise RuntimeError("Could not resolve the package server. Check your internet connection, then press APPLY to retry.")
        raise RuntimeError(output.strip()[-1000:] or f"Command failed with exit code {result.returncode}.")


def _latest_rpm(app, arch, directory):
    request = urllib.request.Request(f"https://api.github.com/repos/{app.source}/releases/latest",
                                     headers={"User-Agent": "InfinityLauncher"})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    release_arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(arch, arch)
    suffixes = (f"-linux-{arch}.rpm", f".{arch}.rpm", f"-linux-{release_arch}.rpm")
    assets = [asset for asset in release.get("assets", ()) if asset["name"].endswith(suffixes)]
    if len(assets) != 1:
        raise RuntimeError(f"No unique {arch} RPM in the latest {app.name} release.")
    asset = assets[0]
    url = asset["browser_download_url"]
    if not url.startswith(f"https://github.com/{app.source}/releases/download/"):
        raise RuntimeError("Unexpected release download URL.")
    destination = Path(directory) / asset["name"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "InfinityLauncher"}), timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    if destination.stat().st_size != asset["size"]:
        raise RuntimeError("Release download size did not match GitHub metadata.")
    checksums = next((item for item in release["assets"] if item["name"] in ("SHA256SUMS.txt", "SHA256SUMS")), None)
    if checksums:
        with urllib.request.urlopen(checksums["browser_download_url"], timeout=30) as response:
            lines = response.read().decode().splitlines()
        expected = next((line.split()[0] for line in lines if line.split()[-1].lstrip("*") == asset["name"]), None)
        if expected and hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Release checksum verification failed.")
    destination.chmod(0o644)
    return destination


def install(app, home=None):
    """Install one selected app. Calling this is the only installation trigger."""
    home = Path(home or Path.home())
    if app.kind == "local-model":
        _install_local_model(app, home)
    elif app.kind == "epic-appimage":
        _install_epic_appimage(app, home)
    elif app.kind == "flatpak":
        _run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
              "https://dl.flathub.org/repo/flathub.flatpakrepo"])
        _run(["flatpak", "install", "--user", "--noninteractive", "--assumeyes", "flathub", app.source])
    elif app.kind == "github-rpm":
        with tempfile.TemporaryDirectory(prefix="infinity-launcher-") as directory:
            package = _latest_rpm(app, os.uname().machine, directory)
            _run(["pkexec", "dnf", "-y", "install", str(package)])
    elif app.kind == "dnf":
        if app.source == "docker-ce":
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


def _install_epic_appimage(app, home):
    binary = home / ".local/bin/EpicGamesLauncher.AppImage"
    desktop = home / ".local/share/applications/epic-games-launcher.desktop"
    binary.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=binary.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            request = urllib.request.Request(app.source, headers={"User-Agent": "InfinityLauncher"})
            with urllib.request.urlopen(request, timeout=60) as response:
                url = urllib.parse.urlsplit(response.geturl())
                if url.scheme != "https" or not (url.hostname or "").endswith(".epicgames.com"):
                    raise RuntimeError("Unexpected Epic Games download URL.")
                expected_size = response.headers.get("Content-Length")
                shutil.copyfileobj(response, output)
            with temporary.open("rb") as downloaded:
                header = downloaded.read(11)
                if temporary.stat().st_size < 4096 or header[:4] != b"\x7fELF" or header[8:] != b"AI\x02":
                    raise RuntimeError("Epic Games download is not an AppImage.")
            if expected_size and temporary.stat().st_size != int(expected_size):
                raise RuntimeError("Epic Games download size did not match server metadata.")
            temporary.chmod(0o755)
            os.replace(temporary, binary)
        finally:
            temporary.unlink(missing_ok=True)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=Epic Games Launcher\n"
        f'Exec=env APPIMAGE_EXTRACT_AND_RUN=1 "{binary}"\n'
        "Icon=applications-games\nCategories=Game;\n",
        encoding="utf-8",
    )


def _install_local_model(app, home):
    model = LOCAL_MODELS[app.source]

    ollama = ollama_binary()
    needs_model = not ollama or subprocess.run([ollama, "show", app.source],
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL, check=False).returncode != 0
    # Fail before installing runtimes when the selected weights cannot fit.
    if needs_model:
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
              "opencode-ai@1.19.0"])

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
