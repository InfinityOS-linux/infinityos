"""Small, private diagnostic report without logs or machine identifiers."""

import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile


PACKAGES = ("infinity-config", "infinity-setup", "infinity-terminal",
            "infinity-updater", "infinityos-shell-extensions")


def _output(args, run=subprocess.run):
    try:
        result = run(args, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def collect(run=subprocess.run, root=Path("/")):
    """Collect only product state; never include hostnames, logs or network data."""
    release = {}
    try:
        for line in (root / "etc/os-release").read_text().splitlines():
            key, _, value = line.partition("=")
            if key in ("ID", "VERSION_ID"):
                release[key] = value.strip('"')
    except OSError:
        pass

    package_versions = {}
    for package in PACKAGES:
        package_versions[package] = _output(
            ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package], run)

    enabled = _output(["gsettings", "get", "org.gnome.shell", "enabled-extensions"], run)
    try:
        enabled = ast.literal_eval(enabled) if enabled else []
        enabled = [uuid for uuid in enabled if isinstance(uuid, str)]
    except (ValueError, SyntaxError, TypeError):
        enabled = []
    try:
        defaults = (root / "usr/share/infinityos/gnome-defaults").read_text().splitlines()
        packaged_line = next(line.partition("=")[2] for line in defaults
                             if line.startswith("enabled-extensions="))
        packaged = set(ast.literal_eval(packaged_line))
    except (OSError, StopIteration, ValueError, SyntaxError, TypeError):
        packaged = set()
    packaged_enabled = [uuid for uuid in enabled if uuid in packaged]

    return {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "os": release,
        "architecture": platform.machine(),
        "gnome_shell": _output(["gnome-shell", "--version"], run),
        "root_filesystem": _output(["findmnt", "-n", "-o", "FSTYPE", "/"], run),
        # The ESP is root-only on Infinity OS. A user report can show the
        # installer's marker, while the full boot audit must run with sudo.
        "refind_installation_recorded":
            (root / "etc/infinityos/refind-installed").is_file(),
        "backups_ready": (root / "var/lib/infinityos/backups-ready").is_file(),
        "infinity_packages": package_versions,
        "enabled_packaged_extensions": packaged_enabled,
        "other_enabled_extension_count": len(enabled) - len(packaged_enabled),
    }


def write_report(path=None, run=subprocess.run, root=Path("/")):
    if path is None:
        state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        directory = state / "infinityos/diagnostics"
        filename = "report-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json"
        path = directory / filename
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as output:
        json.dump(collect(run, root), output, indent=2, sort_keys=True)
        output.write("\n")
        temporary = output.name
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return path
