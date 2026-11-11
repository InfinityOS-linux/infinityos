# InfinitySetup audit — 2026-11-11

## Changes

- CraftSuite description: “Install the complete CraftSuite office suite.” / “Zainstaluj cały pakiet biurowy CraftSuite.”
- Opening: backdrop fades in over 250 ms, then the card over 320 ms. Timing starts at the first GTK frame, not before the window maps. Closing cancels an unfinished opening and starts from current opacity. Disabled animations remain immediate.
- Nexus uses the publisher’s renamed `domsvoboda/nexus-launcher` repository. Existing executable and desktop paths remain unchanged. URL and SHA-256 checks remain enabled.
- New Thunderbird installations use the active `org.mozilla.thunderbird` Flatpak. Existing legacy/ESR installations are recognized without touching profiles or installing a second copy. Bundled icon follows the new ID.
- Spotify is offered only on x64, matching the published Flathub architecture.
- The local-model OpenCode dependency is updated from 1.19.0 to 1.19.5, the current npm release at audit time.

## Checks performed

The catalog contains 69 applications. Checks are not a claim that all 69 were installed and launched.

- Queried latest-release metadata for all 24 GitHub RPM/AppImage entries and exercised the actual asset selector for every offered architecture. All pass after the Nexus correction.
- Queried all 32 Flatpak app metadata records and compared offered ARM/x64 combinations against live Flathub refs. All offered combinations exist after corrections. The old Thunderbird ID is marked end-of-life; the replacement is active.
- Queried Fedora 45 / Docker / OpenRazer repositories for mpv, OpenRazer, Docker CE and its dependencies on ARM and x64.
- Parsed Valve’s live ARM Steam manifest with the production parser. Verified availability of Epic’s official installer, the Lutris Battle.net recipe, Ollama installer, and all three Hugging Face model repositories.
- Xbox driver pinned versions match current releases: xone 0.5.8 and xpadneo 0.10.5. ES-DE’s pinned downloads match current release 3.5.0 on ARM and x64.
- Checked npm versions: Codex 0.167.1, Claude Code 2.1.322 and OpenCode 1.19.5. Codex and Claude installation already requests the current npm version.
- Downloaded and SHA-256-verified the four current CraftSuite ARM RPMs using the production downloader, then installed them together in an isolated Fedora 45 container: PDFCraft 0.21.0, WordCraft 0.18.0, GridCraft 0.19.0, DeckCraft 0.18.0. Removed PDFCraft and verified the other three remained installed.
- Ran Setup/backend/Updater/TV unit tests, CraftSuite GTK tests under Xvfb, and a real GTK frame-clock opening test (72 observed frames, backdrop before card).

## Limits

No complete installation/launch of every catalog application; no physical GPU/controller tests, account login, game launch or large model inference. x64 asset/repository checks are not x64 runtime tests. No ISO rebuilt for this change. No lint run.

## Sources

- https://flathub.org/api/v2/appstream/org.mozilla.thunderbird
- https://support.mozilla.org/en-US/kb/installing-thunderbird-linux
- https://github.com/domsvoboda/nexus-launcher/releases/latest
- https://docs.gtk.org/gtk4/method.Widget.add_tick_callback.html
- https://gitlab.com/es-de/emulationstation-de/-/releases
