Infinity OS loads UsbXbox360Dxe v1.8.0 in rEFInd on x86_64 and aarch64 systems.

Source: https://github.com/jlobue10/UsbXbox360Dxe/releases/tag/v1.8.0
X64 binary: upstream standard release UsbXbox360Dxe.efi
SHA-256 (X64): 9651e547d2842369e69776ce5fd51e5a2562268af91ca3ccfb80bf3f492d14a2
AARCH64 binary: built from source commit 79fca28a97f46b38bd2705c6a0bab241c4d280f4
with EDK2 edk2-stable202411 (0f3867fa6ef0553e26c42f7d71ff6bdb98429742),
Ubuntu 22.04 aarch64 GCC5 toolchain and RELEASE configuration.
SHA-256 (AARCH64): 1f8b022b610889160e2b6f475c22d95e50e71a836e228fc1f7c132720377c93d
License: BSD-2-Clause-Patent (see root/usr/share/licenses/infinity-setup/UsbXbox360Dxe-LICENSE)

The driver accepts supported USB gamepads and receivers. It does not handle
Bluetooth controllers. Infinity OS maps the D-pad and left stick to arrow keys
and A to Enter. Keyboard control remains available.
