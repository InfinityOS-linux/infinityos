# Publishing the next Infinity OS release

Infinity OS has its own version (`/etc/infinityos-release`). Fedora's
`VERSION_ID=44` remains unchanged for DNF repositories and the installer.
The updater announces a newer signed `releases/stable.json` and installs it
only after ordinary RPM updates. Flatpaks and firmware are independent.

The current upgrade path is for releases based on **Fedora 44** on x86_64 and
aarch64. A Fedora base change requires a separate offline system-upgrade path;
the updater displays that a release exists but disables installation rather
than attempting an unsafe in-session transaction.

## Prepare 1.1

1. Wait for the current `main` RPM publication to succeed. Its draft GitHub
   Release `repo-1.0` stores the signed 1.0 repository, which remains available
   for existing installations when 1.1 is published.
2. In the source tree, run `scripts/set-infinityos-release 1.1`. Review the
   changed manifest, image version and both repository URLs.
3. Build and test the new aarch64 and x86_64 images from that source commit.
   Confirm live boot, installation, rEFInd recovery, updater detection and
   the upgrade on a disposable installed 1.0 VM. Do not promote the release
   until those tests pass.
4. Push the reviewed commit to `main`. The RPM workflow builds both arches,
   signs packages and repository metadata, restores the frozen 1.0 repository,
   signs the release manifest, and deploys the complete Pages site. If any
   step fails, Pages is not updated.
5. Confirm that `releases/stable.json` and its detached signature, both 1.1
   RPM repositories, and both legacy 1.0 repositories are reachable. Verify
   package and repository signatures with the shipped Infinity OS key.

The updater never trusts a version or repository URL supplied by a local
user. It verifies the remote manifest signature and constructs a URL on the
fixed Infinity OS Pages host. The privileged helper checks the signature
again, checks that ordinary RPM updates are complete, creates a Btrfs root
snapshot, downloads packages, runs DNF distro-sync with RPM and repository
signature verification, and only then writes the installed version marker.
It leaves the snapshot available in the rEFInd recovery menu. Reboot to use
the updated system.

For 1.2, use the same script with `1.2`. The workflow keeps signed archives
for every version in `previous` and freezes each old channel automatically.
Never delete those draft repository archives while installed systems still
use the corresponding version.
