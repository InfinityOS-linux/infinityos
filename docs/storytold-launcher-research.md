# Storytold apps for InfinitySetup

Research snapshot: 2026-10-21. GridCraft, SoundCraft and FigCraft were added to InfinitySetup after checking current x86_64 and aarch64 RPM releases.

The current InfinitySetup already includes PhotoCraft, VectorCraft, LightCraft, FilmCraft, EffectCraft, DesignCraft and CADCraft under Creative, plus PDFCraft, WordCraft and DeckCraft under Office (`packages/infinity-setup/root/usr/share/infinityos/launcher_backend.py`). The [Storytold organization repository list](https://github.com/orgs/storytold/repositories) contains these and the additional projects below.

| App | Owner's description, suitable for launcher copy | Proposed category / group | Linux release status |
| --- | --- | --- | --- |
| [GridCraft](https://github.com/storytold/gridcraft) | Spreadsheet for data and tables, built in Rust. | Office / Documents, immediately below WordCraft as requested. | [v0.10.0](https://github.com/storytold/gridcraft/releases/tag/v0.10.0) includes both `gridcraft-0.10.0-linux-x86_64.rpm` and `gridcraft-0.10.0-linux-aarch64.rpm`. [README](https://github.com/storytold/gridcraft#readme) calls it a modern spreadsheet application. |
| [SoundCraft](https://github.com/storytold/soundcraft) | Record, edit and mix multitrack audio. | Creative / Audio; a dedicated group is clearer than Image, Video or Design. | [v0.11.0](https://github.com/storytold/soundcraft/releases/tag/v0.11.0) includes x86_64 and aarch64 RPMs. [README](https://github.com/storytold/soundcraft#readme) calls it a digital audio workstation and explicitly labels it **pre-alpha**. |
| [FigCraft](https://github.com/storytold/figcraft) | Design and prototype interfaces with frames, components and layouts. | Creative / Design. | [v0.9.0](https://github.com/storytold/figcraft/releases/tag/v0.9.0) includes x86_64 and aarch64 RPMs. [README](https://github.com/storytold/figcraft#readme) labels it **early alpha**. |
| [ArtCraft Launcher](https://github.com/storytold/craft-launcher) | Install, update and open the Craft App Suite. | **Excluded at the user's request.** Its installation role overlaps InfinitySetup. | [v0.6.1](https://github.com/storytold/craft-launcher/releases/tag/v0.6.1) includes x86_64 and aarch64 RPMs. |

Other apparent desktop candidates are not currently ready for InfinitySetup's GitHub RPM installation path:

- [AniCraft](https://github.com/storytold/AniCraft) is described by its repository metadata as a Rust 2D animation editor, but the repository has no content or releases yet. Future fit: Creative / Animation.
- [ArtCraft](https://github.com/storytold/artcraft#readme) is an AI image/video creation desktop app. Its [latest GitHub release](https://github.com/storytold/artcraft/releases/tag/artcraft-v0.41.0) only contains macOS and Windows installers, so there is no Linux RPM for either target architecture.
- [ArtCraft-X](https://github.com/storytold/artcraftx#readme) describes itself as an experimental AI creation desktop app and says builds are forthcoming. No GitHub release is published. Future fit: Creative / AI tools.
- [Craft Repo Status App](https://github.com/storytold/craft-repo-status-app) tracks PR/build status and has no GitHub release. It is a development utility, not an end-user creative app.

The remaining organization repositories are libraries, assets, demos, services, plugins or data rather than installable desktop apps. Check current releases again at implementation time, since the organization publishes frequently.
