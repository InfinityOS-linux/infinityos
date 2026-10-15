# Infinity OS RPM packages

`infinity-launcher`, `infinity-updater`, `infinityos-repos`, `infinityos-wallpapers`, and `infinityos-ramdrive` are `noarch` RPMs. `infinity-terminal` includes the patched Ghostty binary and is built separately for `aarch64` and `x86_64`. The existing GNOME extension UUID, terminal application ID, desktop file ID, and launcher first-run marker remain stable so an RPM can adopt files from older images without losing shortcuts or first-run state. The visible names and launch commands are **InfinityLauncher** and **InfinityTerminal**.

Each RPM contains the source commit in `/usr/share/infinityos/build-revisions/`.
Commit changes before packaging and publish all six RPMs from the same commit.
The image build refuses an RPM from a different commit, including an older
published package with the same version number. Build a new image from the
repository's `kiwi-build` wrapper, which uses a fresh source archive.

Edit the app files under `packages/infinity-launcher/root/`, `packages/infinity-terminal/root/`, or `packages/infinity-updater/root/`. Terminal engine changes belong in `ghostty/ghostty-1.3.1-infinity.patch`. `packages/build-rpm.sh` builds one package locally with Docker. For example:

```sh
packages/build-rpm.sh infinity-launcher
packages/build-rpm.sh infinity-updater
packages/build-rpm.sh infinityos-repos
packages/build-rpm.sh infinityos-wallpapers
packages/build-rpm.sh infinityos-ramdrive
INFINITY_GHOSTTY_INSTALL_DIR=/path/to/prebuilt/ghostty/install packages/build-rpm.sh infinity-terminal
```

Without `INFINITY_GHOSTTY_INSTALL_DIR`, the terminal script builds Ghostty from its pinned upstream source. Set `INFINITY_TARGET_PLATFORM=linux/arm64` or `linux/amd64` to target the other architecture. The RPMs are written to `.build/rpm-output/`. Building these packages does not build an OS image.

To publish another Infinity OS application, add its RPM spec and source, add CI jobs for each supported architecture, and include those jobs in the `pages` job's `needs`. The publisher automatically places all `noarch` RPMs in both repositories and architecture-specific RPMs in the matching repository. The launcher, updater, terminal, wallpapers, RAMDrive, and repository configuration RPMs remain required so a partial pipeline cannot replace the published repository. Wallpaper sources and the GNOME catalog live in `root/usr/share/backgrounds/infinityos/` and `root/usr/share/infinityos/background-catalog.xml`.

Push changes to protected `main` to run the GitLab pipeline. It builds the launcher, updater, wallpapers, repository configuration package and both terminal architectures, signs the RPMs and `repomd.xml` with the protected `RPM_SIGNING_KEY_B64` CI variable, and publishes each architecture to [Infinity OS Pages](https://infinityos-ca177d.gitlab.io/rpm/44/). The CI pipeline IID is the RPM release number, so a successful new build produces an upgrade. The public key fingerprint is `0CEB C668 0F0E F50B D376 CBB0 3471 5734 8035 14AC`. The public key is bundled with the image in `root/etc/pki/rpm-gpg/`.

Infinity OS installs `infinityos-repos`, which owns the DNF configuration and public key. A one-time service imports trust for signed repository metadata at first boot; it retries on the next boot if the network is unavailable. InfinityUpdater checks RPM and Flatpak updates daily and offers installation from its GNOME panel icon. Bazaar replaces GNOME Software and is installed system-wide from Flathub when networking is available. Existing installations can add the same repo file and key from this source tree, then run:

```sh
sudo dnf -y --refresh makecache --repo infinityos
sudo dnf install infinityos-repos infinity-launcher infinity-terminal infinityos-ramdrive infinity-updater
sudo dnf upgrade
```

InfinityLauncher downloads the latest GitHub release RPMs for Storytold apps and OpenGamepadUI when selected. These third-party RPMs are installed directly, so their future upgrades do not come from the Infinity OS repository. Docker CE is installed from Docker's official Fedora repository, which stays disabled until Docker is selected.
