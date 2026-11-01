# shortcut: Ghostty 1.3.1 needs Zig 0.15.2; move this builder to Fedora 45 when a compatible Zig package is available.
FROM fedora:44
RUN dnf -y install zig-0.15.2-3.fc44 gcc gcc-c++ pkgconf-pkg-config gtk4-devel libadwaita-devel gtk4-layer-shell-devel blueprint-compiler libX11-devel libXrandr-devel libXi-devel wayland-devel fontconfig-devel freetype-devel harfbuzz-devel libpng-devel zlib-devel bzip2-devel oniguruma-devel glslang-devel spirv-tools-devel git patch && dnf clean all
