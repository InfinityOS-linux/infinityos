# Infinity OS improvement checklist

## 1. Installation proof

- [x] Add installed-system audit for bootloader, Btrfs, defaults and apps.
- [x] Add repeatable fresh-install VM procedure and run it on ARM if possible.
- [x] Record x86_64 installation status separately from ISO static verification.
- [x] Run focused tests, commit and push to GitHub.

## 2. Update recovery

- [x] Create a pre-upgrade Btrfs root snapshot from InfinityUpdater.
- [x] Block RPM upgrade when a required snapshot fails.
- [x] Show recovery information and update progress honestly.
- [x] Test, commit and push to GitHub.

## 3. Extension compatibility

- [x] Check bundled and enabled extension GNOME version metadata.
- [x] Provide a safe way to disable a broken extension.
- [x] Add checks to the RPM publication gate.
- [x] Test, commit and push to GitHub.

## 4. Desktop response

- [x] Capture baseline timings on the installed VM, noting unmeasured paint latency.
- [x] Check for confirmed delays without changing saved user preferences; none justified an optimization.
- [x] Verify interaction manually, commit and push to GitHub.

## 5. Infinity Config diagnostics

- [x] Replace the Tweaks placeholder with useful controls and shortcuts.
- [x] Add an explicit diagnostic report with sensitive-data redaction.
- [x] Verify the report and UI, commit and push to GitHub.

## Final checkpoint

- [x] Run the full test suite.
- [x] Inspect GitHub publication results for the final code push.
- [x] Report ARM and x86_64 fresh-install results separately.
