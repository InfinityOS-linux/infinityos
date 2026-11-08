# Proton in InfinityConfig

The Proton tab lists downloaded custom tools and Steam-managed Proton versions.
It offers the recent stable Proton-Cachy (Steam Linux Runtime builds) and GE-Proton
releases published on their official GitHub repositories. Archive selection follows
the machine architecture: aarch64/arm64 or baseline x86_64, not x86_64_v3.

Install and Update verify the GitHub SHA-256 digest and file size, validate archive
paths and links, and stage extraction before publishing. Updates install alongside
older versions, preserving games' existing compatibility-tool selections. The
Remove button confirms the affected version and removes its listed copies without
touching games, saves or `steamapps/compatdata`. Steam-managed tools are opened in
the Steam client for management rather than edited behind Steam's package manager.

Managed versions are installed for the current account in:

- `~/.local/share/Steam/compatibilitytools.d` (also discoverable by UMU/other launchers)
- `~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d`
- existing alternative Steam roots under `~/.steam` and the Flatpak home

These directories are prepared even if Steam is installed later. Resolved aliases
are deduplicated. Files are hard-linked on the same filesystem, and copied across
filesystems, so Flatpak can read its own installation without extra sandbox grants.
Matching managed copies appear as one row and are removed together. Existing custom
tools without Infinity metadata remain separately identifiable by their locations;
removing a symlink never removes its external target.

Steam must be restarted after changes to refresh its compatibility-tool list. The
manager does not restart Steam or interrupt games. It does not select a different
Proton for games automatically, install a game launcher, or provide a system-wide
Wine replacement. Other launchers can use the displayed Proton path.

The UI has English and Polish translations. Release lookups and downloads run off
the GTK thread. Installed versions remain manageable if GitHub is unavailable.

Verification: `tests/test_config_proton.py` covers architecture selection, integrity,
archive escape attempts, publication rollback, sharing and removal; GTK tests cover
lazy loading, updates, installed states and translations. Live release downloads
still require a working GitHub connection.

Official integration references:
- https://github.com/CachyOS/proton-cachyos/releases
- https://github.com/GloriousEggroll/proton-ge-custom/releases
- https://github.com/ValveSoftware/Proton#installing-a-local-build
- https://github.com/Open-Wine-Components/umu-launcher/wiki/Frequently-asked-questions-(FAQ)
