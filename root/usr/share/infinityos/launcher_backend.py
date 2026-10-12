"""Package choices and installation for Infinity Launcher."""

import os
import shutil
import subprocess
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


APPS = (
    App("Gaming", "Steam", "flatpak", "com.valvesoftware.Steam", "Gry i biblioteka Steam", True),
    App("Gaming", "Discord", "flatpak", "com.discordapp.Discord", "Komunikator dla graczy", True),
    App("Gaming", "Vesktop", "flatpak", "dev.vencord.Vesktop", "Alternatywny klient Discord", True),
    App("Gaming", "Heroic Games Launcher", "flatpak", "com.heroicgameslauncher.hgl", "Epic, GOG i Amazon Games", True),
    App("Gaming", "Lutris", "flatpak", "net.lutris.Lutris", "Biblioteka gier z wielu źródeł", True),
    App("Gaming", "Bottles", "flatpak", "com.usebottles.bottles", "Aplikacje i gry Windows przez Wine", True),
    App("Creative", "PhotoCraft", "pending", "", "Oczekuje na źródło pakietu"),
    App("Creative", "VectorCraft", "pending", "", "Oczekuje na źródło pakietu"),
    App("Creative", "PDFCraft", "pending", "", "Oczekuje na źródło pakietu"),
    App("Creative", "GIMP", "flatpak", "org.gimp.GIMP", "Edycja zdjęć i grafiki"),
    App("Creative", "Krita", "flatpak", "org.kde.krita", "Malarstwo cyfrowe"),
    App("Creative", "Inkscape", "flatpak", "org.inkscape.Inkscape", "Grafika wektorowa"),
    App("Creative", "Blender", "flatpak", "org.blender.Blender", "Modelowanie i animacja 3D"),
    App("Creative", "Kdenlive", "flatpak", "org.kde.kdenlive", "Montaż wideo"),
    App("Creative", "OBS Studio", "flatpak", "com.obsproject.Studio", "Nagrywanie i streaming"),
    App("Creative", "Audacity", "flatpak", "org.audacityteam.Audacity", "Edycja dźwięku"),
    App("Programming", "Visual Studio Code", "flatpak", "com.visualstudio.code", "Edytor Microsoft VS Code"),
    App("AI", "Claude + Claude Code CLI", "npm", "@anthropic-ai/claude-code", "CLI oraz skrót do Claude w Firefox", website="https://claude.ai/"),
    App("AI", "Codex + Codex CLI", "npm", "@openai/codex", "CLI oraz skrót do Codex w Firefox", website="https://chatgpt.com/codex"),
)


def available(app, arch=None):
    return app.kind != "pending" and (not app.x86_only or (arch or os.uname().machine) == "x86_64")


def installed(app, home=None):
    home = Path(home or Path.home())
    if app.kind == "flatpak":
        return any(
            subprocess.run(["flatpak", "info", scope, app.source], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False).returncode == 0
            for scope in ("--user", "--system")
        )
    if app.kind == "npm":
        command = "claude" if "anthropic" in app.source else "codex"
        return (home / ".local/bin" / command).exists() or shutil.which(command) is not None
    return False


def _run(command):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(result.stdout.strip()[-1000:] or f"Polecenie zakończyło się kodem {result.returncode}.")


def install(app, home=None):
    """Install one selected app. Calling this is the only installation trigger."""
    home = Path(home or Path.home())
    if app.kind == "flatpak":
        _run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
              "https://dl.flathub.org/repo/flathub.flatpakrepo"])
        _run(["flatpak", "install", "--user", "--noninteractive", "--assumeyes", "flathub", app.source])
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
    else:
        raise ValueError(f"Brak źródła instalacji dla {app.name}.")
