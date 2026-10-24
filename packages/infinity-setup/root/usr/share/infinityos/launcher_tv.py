"""Optional, one-account TV sessions for InfinitySetup."""

import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from launcher_backend import APPS, _run, install, installed

CONTROL = "/usr/libexec/infinityos-tv-control"
STATE = Path("/etc/infinityos/tv-modes")
ESDE = {
    "x86_64": ("357718352", 124827104,
               "abc2999a12385f85775bd3f986fa891c76b69df3791f7c12e4c783cf3c3630f5"),
    "aarch64": ("357718204", 132372640,
                "b6d34657842db89628d5bc42ed465b605108b45cb1d16b15332d6c9f60136a4b"),
}
THEME_URL = "https://github.com/Siddy212/canvas-es-de.git"
THEME_REVISION = "c615aa94313646199f1b0e6c5478b7fe6839e8c4"
# ES-DE stores system-wide emulator selections in each system's gamelist.xml.
# https://gitlab.com/es-de/emulationstation-de/-/blob/master/es-app/src/GamelistFileParser.cpp
# Labels match the bundled system definitions; Fedora ships these cores.
# https://gitlab.com/es-de/emulationstation-de/-/blob/master/resources/systems/linuxarm/es_systems.xml
FEDORA_EMULATORS = {"nes": "Nestopia UE", "psx": "PCSX ReARMed"}
ESDE_PACKAGES = ("retroarch", "fuse-libs", "git", "libretro-gambatte",
                 "libretro-mgba", "libretro-nestopia", "libretro-pcsx-rearmed")


def _manifest(home, mode):
    return home / f".local/share/infinityos/tv/{mode}-installed.json"


def _missing_packages(packages):
    return [package for package in packages if subprocess.run(
        ["rpm", "-q", "--quiet", package], check=False).returncode != 0]


def _tree_hash(path):
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_symlink():
            return None
        if file.is_dir():
            continue
        if not file.is_file():
            return None
        digest.update(str(file.relative_to(path)).encode())
        digest.update(hashlib.sha256(file.read_bytes()).digest())
    return digest.hexdigest()


def _save_manifest(home, mode, details):
    _replace_text(_manifest(home, mode), json.dumps(details, sort_keys=True) + "\n")


def _managed_packages(home, mode):
    path = _manifest(home, mode)
    if not path.is_file():
        return []
    details = json.loads(path.read_text(encoding="utf-8"))
    allowed = ESDE_PACKAGES if mode == "esde" else ("gamescope", "libva", "libvpx", "ibus-libs")
    return [package for package in details.get("packages", [])
            if package in allowed and
            package not in _missing_packages((package,))]


def _remove_managed(home, mode):
    path = _manifest(home, mode)
    if not path.is_file():
        return
    details = json.loads(path.read_text(encoding="utf-8"))
    if mode == "esde":
        theme = home / "ES-DE/themes/canvas-es-de"
        if details.get("theme_hash") and theme.is_dir() and _tree_hash(theme) == details["theme_hash"]:
            shutil.rmtree(theme)
        for relative, entry in details.get("settings", {}).items():
            setting = home / relative
            if setting.is_file() and hashlib.sha256(setting.read_bytes()).hexdigest() == entry["applied"]:
                if entry["previous"] is None:
                    setting.unlink()
                else:
                    _replace_text(setting, entry["previous"])
    path.unlink()


def enabled(mode, uid=None):
    if mode not in ("esde", "steam"):
        raise ValueError("Unknown TV mode")
    state = STATE / mode
    return state.is_file() and state.read_text(encoding="ascii").strip() == str(uid or os.getuid())


def _install_esde(home):
    arch = os.uname().machine
    if arch not in ESDE:
        raise RuntimeError("ES-DE is available only on x64 and ARM64")
    package_id, size, expected = ESDE[arch]
    binary = home / ".local/share/infinityos/tv/ES-DE.AppImage"
    if binary.is_file() and hashlib.sha256(binary.read_bytes()).hexdigest() == expected:
        return binary
    binary.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://gitlab.com/es-de/emulationstation-de/-/package_files/{package_id}/download"
    with tempfile.NamedTemporaryFile(prefix=".es-de-", dir=binary.parent, delete=False) as file:
        temporary = Path(file.name)
        digest = hashlib.sha256()
        count = 0
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > size:
                        raise RuntimeError("ES-DE download exceeds its published size")
                    file.write(chunk)
                    digest.update(chunk)
            if count != size or digest.hexdigest() != expected:
                raise RuntimeError("ES-DE download failed SHA-256 verification")
            file.flush()
            temporary.chmod(0o755)
            temporary.replace(binary)
        finally:
            temporary.unlink(missing_ok=True)
    return binary


def _install_theme(home):
    target = home / "ES-DE/themes/canvas-es-de"
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".infinity-esde-theme-",
                                     dir=target.parent) as directory:
        source = Path(directory) / "canvas"
        _run(["git", "init", "-q", str(source)])
        _run(["git", "-C", str(source), "fetch", "-q", "--depth", "1",
              THEME_URL, THEME_REVISION])
        _run(["git", "-C", str(source), "checkout", "-q", "FETCH_HEAD"])
        revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.strip()
        if revision != THEME_REVISION:
            raise RuntimeError("ES-DE theme revision changed unexpectedly")
        shutil.rmtree(source / ".git")
        source.replace(target)


def _replace_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{path.name}.",
                                     dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(content)
            output.flush()
            temporary.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o644)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _configure_esde(home):
    settings = home / "ES-DE/settings/es_settings.xml"
    if not settings.exists():
        settings.parent.mkdir(parents=True, exist_ok=True)
        _replace_text(settings,
            '<?xml version="1.0"?>\n'
            '<string name="ROMDirectory" value="/emulation/roms" />\n'
            '<string name="Theme" value="canvas-es-de" />\n'
            '<string name="ThemeColorScheme" value="neon-controller" />\n'
            '<string name="MenuColorScheme" value="dark" />\n')
    else:
        content = settings.read_text(encoding="utf-8")
        setting = '<string name="ROMDirectory" value="/emulation/roms" />'
        updated, count = re.subn(r'<string name="ROMDirectory" value="[^"]*"\s*/>',
                                 setting, content, count=1)
        if not count:
            updated = content.rstrip() + "\n" + setting + "\n"
        if updated != content:
            _replace_text(settings, updated)
    retroarch = home / ".config/retroarch/retroarch.cfg"
    retroarch.parent.mkdir(parents=True, exist_ok=True)
    if not retroarch.exists():
        _replace_text(retroarch, 'system_directory = "/emulation/bios"\n')
    else:
        content = retroarch.read_text(encoding="utf-8")
        setting = 'system_directory = "/emulation/bios"'
        updated, count = re.subn(r'^system_directory\s*=.*$', setting, content,
                                 count=1, flags=re.MULTILINE)
        if not count:
            updated = content.rstrip() + "\n" + setting + "\n"
        if updated != content:
            _replace_text(retroarch, updated)
    for system, emulator in FEDORA_EMULATORS.items():
        gamelist = home / f"ES-DE/gamelists/{system}/gamelist.xml"
        if not gamelist.exists():
            # ES-DE 3.4.x reads this node at document level, beside gameList.
            _replace_text(gamelist,
                '<?xml version="1.0"?>\n'
                f'<alternativeEmulator><label>{emulator}</label></alternativeEmulator>\n'
                '<gameList />\n')


def _hide_esde_from_home(home):
    hidden = home / ".hidden"
    content = hidden.read_text(encoding="utf-8") if hidden.is_file() else ""
    if "ES-DE" not in content.splitlines():
        _replace_text(hidden, content + ("\n" if content and not content.endswith("\n") else "")
                      + "ES-DE\n")


def _finish_esde(home):
    _install_theme(home)
    _configure_esde(home)
    binary = home / ".local/share/infinityos/tv/ES-DE.AppImage"
    _run([str(binary), "--create-system-dirs"])
    _hide_esde_from_home(home)


def set_enabled(mode, active, home=None):
    if mode not in ("esde", "steam"):
        raise ValueError("Unknown TV mode")
    home = Path(home or Path.home())
    if not active:
        packages = _managed_packages(home, mode)
        _run(["pkexec", CONTROL, "deactivate", mode, *packages])
        if mode == "esde":
            (home / ".local/share/infinityos/tv/ES-DE.AppImage").unlink(missing_ok=True)
        _remove_managed(home, mode)
        return
    if mode == "esde":
        settings_paths = ("ES-DE/settings/es_settings.xml", ".config/retroarch/retroarch.cfg",
                          "ES-DE/gamelists/nes/gamelist.xml",
                          "ES-DE/gamelists/psx/gamelist.xml")
        previous_settings = {relative: (home / relative).read_text(encoding="utf-8")
                             if (home / relative).is_file() else None
                             for relative in settings_paths}
        theme = home / "ES-DE/themes/canvas-es-de"
        existing = (_manifest(home, mode).read_text(encoding="utf-8")
                    if _manifest(home, mode).is_file() else None)
        details = json.loads(existing) if existing else {"packages": [], "settings": {}}
        previous_settings = details.get("previous_settings", previous_settings)
        theme_created = details.get("theme_created",
                                    not theme.exists() and not details.get("theme_hash"))
        _install_esde(home)
        details["packages"] = list(dict.fromkeys(
            details.get("packages", []) + _missing_packages(ESDE_PACKAGES)))
        details["previous_settings"] = previous_settings
        details["theme_created"] = theme_created
        _save_manifest(home, mode, details)
        _run(["pkexec", CONTROL, "activate", "esde", str(os.getuid())])
        details["theme_hash"] = (_tree_hash(theme) if theme_created
                                 else details.get("theme_hash"))
        details["settings"] = {
            relative: {"previous": previous_settings[relative],
                       "applied": hashlib.sha256((home / relative).read_bytes()).hexdigest()}
            for relative in settings_paths if (home / relative).is_file()
        }
        details.pop("previous_settings")
        details.pop("theme_created")
        _save_manifest(home, mode, details)
        shortcut = home / "Emulation"
        if not shortcut.exists() and not shortcut.is_symlink():
            shortcut.symlink_to("/emulation", target_is_directory=True)
    else:
        steam = next(app for app in APPS if app.name == "Steam")
        existing = (_manifest(home, mode).read_text(encoding="utf-8")
                    if _manifest(home, mode).is_file() else None)
        details = json.loads(existing) if existing else {"packages": []}
        if not installed(steam, home):
            install(steam, home, defer_system_dependencies=True)
        dependencies = ["gamescope"]
        if os.uname().machine == "aarch64":
            dependencies.extend(("libva", "libvpx", "ibus-libs"))
        details["packages"] = list(dict.fromkeys(
            details.get("packages", []) + _missing_packages(dependencies)))
        _save_manifest(home, mode, details)
        _run(["pkexec", CONTROL, "activate", "steam", str(os.getuid())])


if __name__ == "__main__":
    if sys.argv[1:] != ["--finish-esde"]:
        raise SystemExit("Usage: launcher_tv.py --finish-esde")
    _finish_esde(Path(pwd.getpwuid(os.getuid()).pw_dir))
