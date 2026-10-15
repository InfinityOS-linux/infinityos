# Contributing to Infinity OS

Infinity OS welcomes focused fixes, documentation, translations, and improvements to its desktop applications. Open an issue before starting a large change so the approach can be discussed.

1. Fork the project and create a branch for one change.
2. Keep image configuration, RPM packaging, and documentation in sync. A change to an application that ships as an RPM needs a matching package build before an image can be verified.
3. Run relevant focused tests from `tests/` and check shell syntax for changed scripts. If the change affects boot, installation, or hardware support, describe the hardware or VM used for verification.
4. Open a merge request to `main` with the problem, solution, and test results. Include screenshots for visible desktop changes.

The image wrapper accepts only a clean commit and checks that the six Infinity OS RPMs match that commit. The repository contains material from Fedora and other upstream projects; preserve their copyright, license, and attribution notices when changing or importing files. See [THIRD_PARTY.md](THIRD_PARTY.md) and [docs/REDISTRIBUTION.md](docs/REDISTRIBUTION.md).

Report security issues through the private route described in [SECURITY.md](SECURITY.md).
