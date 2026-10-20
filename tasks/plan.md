# Infinity OS reliability and desktop improvements

## Goal

Make installation, updates and the desktop predictable on the supported ARM
and x86_64 images. Deliver each independently verifiable change to GitHub in
small commits. The user explicitly forbids running lint.

## Existing foundations

- The image verifier checks boot files, RPM provenance and extension contents.
- Installed Btrfs systems already have Snapper and a systemd-boot Backups menu.
- InfinityUpdater handles RPM, Flatpak and firmware updates with progress.
- Bundled GNOME extensions have fixed UUIDs and an image contract checker.
- Infinity Config provides Dock and Cursor size controls; Tweaks is a placeholder.

## Delivery order

1. **Installation proof:** add a reproducible, non-destructive fresh-install
   smoke test and a post-install audit for systemd-boot, Btrfs, desktop RPMs
   and enabled extensions. Run it on ARM if local VM capacity permits. Keep
   x86_64 verification separate until it has actually been booted and installed.
2. **Update recovery:** make the updater create a root snapshot immediately
   before an RPM upgrade on Btrfs. A failed snapshot must prevent that upgrade.
   Explain the snapshot number and recovery path in the UI. Keep firmware and
   Flatpak progress and errors visible.
3. **Extension compatibility:** make extension contracts verify GNOME version
   support and add a safe recovery path for disabling a faulty extension.
   Run these checks before publishing updated extension RPMs.
4. **Desktop response:** add reproducible measurements for first session,
   launcher, dock and desktop context menu, then optimize confirmed delays.
   Preserve the current visual behavior and existing user settings.
5. **Infinity Config diagnostics:** replace the Tweaks placeholder with useful
   shortcuts and a user-invoked diagnostic report that redacts secrets and
   does not require root.

## Verification checkpoints

Each phase gets focused tests, syntax checks where applicable, a reviewed diff,
an atomic commit and a push to the GitHub remote only. The final checkpoint
includes the full test suite and an installed-system check. Building new ISO
images is not part of this request unless needed for a fresh-install test.

## Risks

- An image can pass static checks while the interactive installer skips a post
  script. The fresh-install test must inspect the installed disk after reboot.
- A snapshot of `/` does not include separate `/home`, `/var` or firmware.
  The interface must state this accurately.
- GNOME extensions can break after a Shell upgrade despite metadata support.
  Bundling, runtime recovery and release checks reduce, but do not eliminate,
  that risk.
- A local ARM VM cannot prove x86_64 hardware behavior. Report the two
  architectures separately.
