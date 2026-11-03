These vector masters generate the seven Infinity OS boot icons and the two menu
arrows. Run `scripts/generate-refind-icons.sh` after editing them. Steam is a
trademark of Valve Corporation. The Steam mark is based on the Simple Icons
Steam symbol.

Manual menu labels are rendered verbatim by the packaged
`infinityos-refind-short-labels` helper. Stock rEFInd wraps those labels in
`Boot %s from %s` inside `AddStanzaEntries`; shortening `menuentry` alone does
not remove the volume description. The helper replaces only that exact UTF-16
format resource in unsigned x64/ARM64 PE images, preserves all section offsets
and image length, and updates the PE checksum. It rejects signed or unknown
images before writing. Installation, live ISO finalization and Setup RPM
post-transaction updates use the same helper. Existing loaders are updated too.
The resulting x64 image was booted under QEMU/OVMF to check the visible caption.
