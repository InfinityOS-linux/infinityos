# Contributing to Infinity OS

Infinity OS welcomes focused fixes, documentation, translations, and improvements to its desktop applications. Open an issue before starting a large change so the approach can be discussed.

Have a question or an early idea? Join the [InfinityOS Discord community](https://discord.gg/QA8N3XKsH8). Keep actionable bug reports and proposed code changes in GitHub issues and pull requests so they remain easy to track.

1. Fork the project and create a branch for one change.
2. Keep image configuration, RPM packaging, and documentation in sync. A change to an application that ships as an RPM needs a matching package build before an image can be verified.
3. Run relevant focused tests from `tests/` and check shell syntax for changed scripts. If the change affects boot, installation, or hardware support, describe the hardware or VM used for verification.
4. Open a pull request to `main` with the problem, solution, and test results. Include screenshots for visible desktop changes.

The image wrapper accepts only a clean commit and checks that all Infinity OS RPMs listed in its generated manifest match that commit. The repository contains material from Fedora and other upstream projects; preserve their copyright, license, and attribution notices when changing or importing files. See [THIRD_PARTY.md](THIRD_PARTY.md) and [docs/REDISTRIBUTION.md](docs/REDISTRIBUTION.md).

Report security issues through the private route described in [SECURITY.md](SECURITY.md).

# Preserving desktop behavior across updates

Infinity OS changes to a bundled GNOME extension need an Infinity OS UUID when
upstream updates could replace those changes. Keep the directory name,
`metadata.json` UUID, enabled extension list, and all integration references in
sync. Add a focused behavior test under `tests/*.test.mjs` for each user-visible
change, and extend `scripts/verify-gnome-extension-contracts` when a required
extension or setting is added. `kiwi-build` runs these checks from the exact
source commit used for the image; `verify-infinity-iso` checks the installed
extension layout after the image is built.

Infinity OS RPM applications must keep their build-revision marker. The image
builder derives its required RPM manifest from `packages/*/*.spec` and verifies
that every package in the image matches the image's source commit. This
prevents an image from silently mixing new desktop defaults with stale
application packages. Upstream Fedora and Flatpak applications still follow
their own update channels; test their integration when changing supported
versions.
