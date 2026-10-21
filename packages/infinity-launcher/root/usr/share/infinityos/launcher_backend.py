"""Application catalog and deferred installation for InfinityLauncher."""

import hashlib
import io
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tarfile
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


DRIVERS = {
    "xone": ("medusalix/xone", "8311a25f2b4e69b7a3f8133b884cede065b253cc",
             "6ba4ad757e0598a886c9ed50f1b9f0477a6eab3fbca4de7c564d415e3b4aadc8", "xone", "v0.3"),
    "xpadneo": ("atar-axis/xpadneo", "e8f103a77f777c2c54536dd947969cf228699c13",
                "3e37e6d774ad6bd0e0f49d0854e30b715851b845520155cbaa428ca90d4780ac", "hid-xpadneo", "v0.10.5"),
}
XONE_FIRMWARE_SHA256 = "48084d9fa53b9bb04358f3bb127b7495dc8f7bb0b3ca1437bd24ef2b6eabdf66"


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
    App("System", "Safe Disk Cleaner", "github-appimage", "cyb3rl00m/safe-disk-cleaner", "Inspect disk usage and choose safe cleanup actions with clear explanations.", website="https://github.com/cyb3rl00m/safe-disk-cleaner", group="System maintenance", icon="io.github.cyb3rl00m.SafeDiskCleaner"),
    App("System", "OpenLogi", "github-rpm", "AprilNEA/OpenLogi", "Configure Logitech mouse buttons, DPI and SmartShift locally.", website="https://github.com/AprilNEA/OpenLogi", group="Device tools", icon="openlogi"),
    App("System", "OpenRazer", "dnf", "openrazer-meta", "Drivers and daemon for Razer devices; restart after installation.", website="https://github.com/openrazer/openrazer", group="Device tools", icon="input-gaming-symbolic"),
    App("System", "WinBoat", "winboat-rpm", "winboat-org/winboat", "Run Windows apps in a container-backed VM; requires KVM, 4 GB RAM and 32 GB free space.", True, website="https://github.com/winboat-org/winboat", group="Windows apps", icon="winboat", package="winboat"),
    App("Gaming", "Steam", "flatpak", "com.valvesoftware.Steam", "Steam games and store.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Epic Games Launcher", "epic-appimage", "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncher-x86_64.AppImage", "Native Linux Preview from Epic Games.", True, website="https://launcher.epicgames.com/", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Blizzard Battle.net", "lutris-installer", "battlenet-standard", "Windows launcher; install through Lutris and Wine.", True, website="https://download.battle.net/", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Heroic Games Launcher", "flatpak", "com.heroicgameslauncher.hgl", "Epic, GOG and Amazon games.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Lutris", "flatpak", "net.lutris.Lutris", "Games from multiple stores.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Faugus Launcher", "flatpak", "io.github.Faugus.faugus-launcher", "Windows games with Wine.", True, group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "Prism Launcher", "flatpak", "org.prismlauncher.PrismLauncher", "Minecraft instances and modpacks.", group="Game launchers", icon="applications-games-symbolic"),
    App("Gaming", "OpenGamepadUI", "github-rpm", "shadowblip/OpenGamepadUI", "Controller-first game library.", group="Game launchers", icon="opengamepadui"),
    App("Gaming", "ProtonPlus", "flatpak", "com.vysp3r.ProtonPlus", "Manage Proton, Wine, DXVK and VKD3D versions for game launchers.", website="https://protonplus.vysp3r.com/", group="Game launchers", icon="com.vysp3r.ProtonPlus"),
    App("Gaming", "Xbox Controller · USB / Dongle", "driver", "xone", "xone driver for wired Xbox controllers and the Xbox Wireless Adapter; installs dongle firmware.", website="https://github.com/medusalix/xone", group="Xbox Controller", icon="input-gaming-symbolic"),
    App("Gaming", "Xbox Controller · Bluetooth", "driver", "xpadneo", "xpadneo Bluetooth driver for Xbox controllers; pair the controller after installation.", website="https://github.com/atar-axis/xpadneo", group="Xbox Controller", icon="input-gaming-symbolic"),
    App("Gaming", "Discord", "flatpak", "com.discordapp.Discord", "Voice and text chat.", True, group="Communication", icon="mail-message-new-symbolic"),
    App("Gaming", "Vesktop", "flatpak", "dev.vencord.Vesktop", "Alternative Discord client.", group="Communication", icon="mail-message-new-symbolic"),
    App("Gaming", "Bottles", "flatpak", "com.usebottles.bottles", "Wine environments for Windows apps.", True, group="Other", icon="applications-system-symbolic"),
    App("Creative", "PhotoCraft", "github-rpm", "storytold/photocraft", "Open-source photo editor built in Rust.", website="https://github.com/storytold/photocraft", group="Image", icon="ai.storyteller.photocraft"),
    App("Creative", "VectorCraft", "github-rpm", "storytold/vectorcraft", "Create and edit vector art in an open-source Rust app.", website="https://github.com/storytold/vectorcraft", group="Image", icon="ai.storyteller.vectorcraft"),
    App("Creative", "LightCraft", "github-rpm", "storytold/lightcraft", "Edit photos non-destructively in an open-source Rust app.", website="https://github.com/storytold/lightcraft", group="Image", icon="ai.storyteller.lightcraft"),
    App("Creative", "FilmCraft", "github-rpm", "storytold/filmcraft", "Edit video on a nonlinear timeline in an open-source Rust app.", website="https://github.com/storytold/filmcraft", group="Video", icon="ai.storyteller.filmcraft"),
    App("Creative", "EffectCraft", "github-rpm", "storytold/effectcraft", "Create motion graphics and composite visual effects.", website="https://github.com/storytold/effectcraft", group="Video", icon="ai.storyteller.effectcraft"),
    App("Creative", "DesignCraft", "github-rpm", "storytold/designcraft", "Design pages and publication layouts in an open-source Rust app.", website="https://github.com/storytold/designcraft", group="Design", icon="ai.storyteller.designcraft"),
    App("Creative", "CADCraft", "github-rpm", "storytold/cadcraft", "Computer-aided design and drafting in an open-source Rust app.", website="https://github.com/storytold/cadcraft", group="Design", icon="ai.storyteller.cadcraft"),
    App("Creative", "FigCraft", "github-rpm", "storytold/figcraft", "Design and prototype interfaces with frames, components and layouts (early alpha).", website="https://github.com/storytold/figcraft", group="Design", icon="ai.storyteller.figcraft"),
    App("Creative", "SoundCraft", "github-rpm", "storytold/soundcraft", "Record, edit and mix multitrack audio (pre-alpha).", website="https://github.com/storytold/soundcraft", group="Audio", icon="ai.storyteller.soundcraft"),
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
    App("Office", "PDFCraft", "github-rpm", "storytold/pdfcraft", "Read and edit PDF documents in an open-source Rust app.", website="https://github.com/storytold/pdfcraft", group="Documents", icon="ai.storyteller.pdfcraft"),
    App("Office", "WordCraft", "github-rpm", "storytold/wordcraft", "Create and edit word-processing documents in an open-source Rust app.", website="https://github.com/storytold/wordcraft", group="Documents", icon="ai.storyteller.wordcraft"),
    App("Office", "GridCraft", "github-rpm", "storytold/gridcraft", "Create spreadsheets for data and tables in an open-source Rust app.", website="https://github.com/storytold/gridcraft", group="Documents", icon="ai.storyteller.gridcraft"),
    App("Office", "DeckCraft", "github-rpm", "storytold/deckcraft", "Create presentations and slide shows in an open-source Rust app.", website="https://github.com/storytold/deckcraft", group="Documents", icon="ai.storyteller.deckcraft"),
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
    if app.kind == "github-appimage":
        return ((home / ".local/bin/SafeDiskCleaner.AppImage").is_file() and
                (home / ".local/share/applications/io.github.cyb3rl00m.SafeDiskCleaner.desktop").is_file())
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
    if app.kind == "driver":
        return _driver_module_installed(app.source) and (
            app.source != "xone" or _xone_firmware_valid())
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


def _driver_module_installed(driver):
    if not shutil.which("dkms"):
        return False
    module = DRIVERS[driver][3]
    result = subprocess.run(["dkms", "status", module], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, check=False)
    return result.returncode == 0 and "installed" in result.stdout


def _xone_firmware_valid():
    firmware = Path("/lib/firmware/xow_dongle.bin")
    return firmware.is_file() and hashlib.sha256(firmware.read_bytes()).hexdigest() == XONE_FIRMWARE_SHA256


def _verified_driver_source(driver, directory):
    repository, commit, expected, _, _ = DRIVERS[driver]
    url = f"https://codeload.github.com/{repository}/tar.gz/{commit}"
    request = urllib.request.Request(url, headers={"User-Agent": "InfinityLauncher"})
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


def _install_xone_firmware(directory):
    firmware = Path("/lib/firmware/xow_dongle.bin")
    if _xone_firmware_valid():
        return
    # Microsoft's legacy CAB endpoint only offers HTTP; the extracted firmware
    # is authenticated with the SHA256 from xone before it enters /lib/firmware.
    url = ("http://download.windowsupdate.com/c/msdownload/update/driver/drvs/2017/07/"
           "1cd6a87c-623f-4407-a52d-c31be49e925c_e19f60808bdcbfbd3c3df6be3e71ffc52e43261e.cab")
    cab = Path(directory) / "driver.cab"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read(1_000_001)
    if len(payload) > 1_000_000:
        raise RuntimeError("Xbox Wireless Adapter firmware archive is too large.")
    cab.write_bytes(payload)
    _run(["cabextract", "-F", "FW_ACC_00U.bin", "-d", str(directory), str(cab)])
    extracted = Path(directory) / "FW_ACC_00U.bin"
    if not extracted.is_file() or hashlib.sha256(extracted.read_bytes()).hexdigest() != XONE_FIRMWARE_SHA256:
        raise RuntimeError("Xbox Wireless Adapter firmware failed checksum verification.")
    firmware.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(extracted, firmware)
    firmware.chmod(0o644)


def _install_driver_as_root(driver):
    if os.geteuid() != 0 or driver not in DRIVERS:
        raise PermissionError("Controller driver installation requires root and a known driver.")
    kernel = os.uname().release
    build_dir = Path(f"/lib/modules/{kernel}/build")
    prerequisites = ["dkms", "gcc", "make", "kernel-headers"]
    if not build_dir.is_dir():
        prerequisites.append(f"kernel-devel-{kernel}")
    if driver == "xone":
        prerequisites.append("cabextract")
    else:
        prerequisites.extend(("bluez", "bluez-tools"))
    _run(["dnf", "-y", "install", *prerequisites])
    if not build_dir.is_dir():
        raise RuntimeError(f"Kernel headers for {kernel} are missing. Update packages, reboot, then retry.")
    with tempfile.TemporaryDirectory(prefix="infinity-controller-") as directory:
        if not _driver_module_installed(driver):
            source = _verified_driver_source(driver, directory)
            if driver == "xone":
                version = DRIVERS[driver][4]
                destination = Path("/usr/src") / f"xone-{version}"
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
                for path in (*destination.rglob("dkms.conf"), *destination.rglob("*.c")):
                    contents = path.read_bytes()
                    if b"#VERSION#" in contents:
                        path.write_bytes(contents.replace(b"#VERSION#", version.encode()))
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


def _latest_rpm(app, arch, directory):
    request = urllib.request.Request(f"https://api.github.com/repos/{app.source}/releases/latest",
                                     headers={"User-Agent": "InfinityLauncher"})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    release_arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(arch, arch)
    suffixes = (f"-linux-{arch}.rpm", f".{arch}.rpm", f"-linux-{release_arch}.rpm", f"-{arch}.rpm")
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


def _latest_appimage(app, arch, directory):
    request = urllib.request.Request(f"https://api.github.com/repos/{app.source}/releases/latest",
                                     headers={"User-Agent": "InfinityLauncher"})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    assets = [asset for asset in release.get("assets", ())
              if asset["name"].endswith(f"-{arch}.AppImage")]
    if len(assets) != 1:
        raise RuntimeError(f"No unique {arch} AppImage in the latest {app.name} release.")
    asset = assets[0]
    if Path(asset["name"]).name != asset["name"]:
        raise RuntimeError("Unexpected AppImage asset name.")
    url = asset["browser_download_url"]
    if not url.startswith(f"https://github.com/{app.source}/releases/download/"):
        raise RuntimeError("Unexpected release download URL.")
    digest = asset.get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError("Release is missing a SHA256 digest for the AppImage.")
    destination = Path(directory) / asset["name"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "InfinityLauncher"}), timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    if destination.stat().st_size != asset["size"]:
        raise RuntimeError("AppImage download size did not match GitHub metadata.")
    if hashlib.sha256(destination.read_bytes()).hexdigest() != digest.removeprefix("sha256:"):
        raise RuntimeError("AppImage checksum verification failed.")
    with destination.open("rb") as downloaded:
        header = downloaded.read(20)
    machine = {"x86_64": 62, "aarch64": 183}.get(arch)
    if (destination.stat().st_size < 4096 or header[:4] != b"\x7fELF" or
            header[4:6] != b"\x02\x01" or header[8:11] != b"AI\x02" or
            machine is None or int.from_bytes(header[18:20], "little") != machine):
        raise RuntimeError("Release download is not an AppImage.")
    return destination


def _install_safe_disk_cleaner(app, home):
    binary = home / ".local/bin/SafeDiskCleaner.AppImage"
    desktop = home / ".local/share/applications/io.github.cyb3rl00m.SafeDiskCleaner.desktop"
    binary.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="infinity-cleaner-") as directory:
        package = _latest_appimage(app, os.uname().machine, directory)
        temporary = binary.with_suffix(".tmp")
        shutil.copyfile(package, temporary)
        temporary.chmod(0o755)
        temporary.replace(binary)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=Safe Disk Cleaner\n"
        f'Exec=env APPIMAGE_EXTRACT_AND_RUN=1 "{binary}"\n'
        "Icon=/usr/share/infinityos/launcher-icons/io.github.cyb3rl00m.SafeDiskCleaner.svg\n"
        "Terminal=false\nCategories=GTK;System;Utility;\n",
        encoding="utf-8",
    )


def install(app, home=None):
    """Install one selected app. Calling this is the only installation trigger."""
    home = Path(home or Path.home())
    if app.kind == "local-model":
        _install_local_model(app, home)
    elif app.kind == "epic-appimage":
        _install_epic_appimage(app, home)
    elif app.kind == "github-appimage":
        if app.source != "cyb3rl00m/safe-disk-cleaner":
            raise ValueError(f"No AppImage installation source for {app.name}.")
        _install_safe_disk_cleaner(app, home)
    elif app.kind == "flatpak":
        _run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
              "https://dl.flathub.org/repo/flathub.flatpakrepo"])
        _run(["flatpak", "install", "--user", "--noninteractive", "--assumeyes", "flathub", app.source])
    elif app.kind == "github-rpm":
        with tempfile.TemporaryDirectory(prefix="infinity-launcher-") as directory:
            package = _latest_rpm(app, os.uname().machine, directory)
            _run(["pkexec", "dnf", "-y", "install", str(package)])
    elif app.kind == "winboat-rpm":
        with tempfile.TemporaryDirectory(prefix="infinity-launcher-") as directory:
            package = _latest_rpm(app, os.uname().machine, directory)
            _run(["pkexec", "dnf", "-y", "install", "podman", "podman-compose",
                  "freerdp", str(package)])
    elif app.kind == "driver":
        if app.source not in DRIVERS:
            raise ValueError(f"Unknown controller driver: {app.source}")
        _run(["pkexec", "/usr/bin/python3", str(Path(__file__).resolve()),
              "--install-driver", app.source])
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


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--install-driver":
        raise SystemExit("Usage: launcher_backend.py --install-driver xone|xpadneo")
    _install_driver_as_root(sys.argv[2])
