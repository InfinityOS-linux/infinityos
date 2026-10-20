# Infinity OS improvement checklist

## 1. Installation proof

- [x] Add installed-system audit for bootloader, Btrfs, defaults and apps.
- [ ] Add repeatable fresh-install VM procedure and run it on ARM if possible.
- [ ] Record x86_64 installation status separately from ISO static verification.
- [ ] Run focused tests, commit and push to GitHub.

## 2. Update recovery

- [x] Create a pre-upgrade Btrfs root snapshot from InfinityUpdater.
- [x] Block RPM upgrade when a required snapshot fails.
- [x] Show recovery information and update progress honestly.
- [x] Test, commit and push to GitHub.

## 3. Extension compatibility

- [ ] Check bundled and enabled extension GNOME version metadata.
- [ ] Provide a safe way to disable a broken extension.
- [ ] Add checks to the RPM publication gate.
- [ ] Test, commit and push to GitHub.

## 4. Desktop response

- [ ] Capture baseline timings on the installed VM.
- [ ] Fix delays with evidence, without changing saved user preferences.
- [ ] Verify interaction manually, commit and push to GitHub.

## 5. Infinity Config diagnostics

- [ ] Replace the Tweaks placeholder with useful controls and shortcuts.
- [ ] Add an explicit diagnostic report with sensitive-data redaction.
- [ ] Verify the report and UI, commit and push to GitHub.

## Final checkpoint

- [ ] Run the full test suite and inspect GitHub publication results.
- [ ] Report ARM and x86_64 fresh-install results separately.
