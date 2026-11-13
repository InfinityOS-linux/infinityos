# Infinity Terminal hardware strip

The GNOME Shell controller reserves space above the Ghostty window for a dark hardware strip. The strip follows the terminal slide, respects the selected monitor and full-height resizing, and disappears in overview or when the terminal closes. The client keeps its full input region; the strip does not cover terminal text.

Right-click any tile to change its sensor/device, move it left or right, remove it, or add another. Device headings distinguish multiple GPUs, including identical models. The same menu controls refresh intervals (1/2/5/10 seconds), history (30/60/120/300 seconds), graphs and Celsius/Fahrenheit. Left-click and keyboard activation also open the menu. A horizontal scrollbar accommodates many tiles. All selections persist in GSettings. Preferences can disable the strip and set the CPU's nominal TDP manually.

## Readings and limits

- Temperatures, power, frequency and fans: Linux hwmon, with driver labels and stable physical device paths instead of volatile hwmon indexes. GPU device addresses appear on tiles.
- NVIDIA: optional `nvidia-smi` CSV query, identified by GPU UUID. Each GPU exposes its own temperature, graphics clock, power, configured power limit and VRAM. Driver-reported unsupported values become N/A. No NVIDIA dependency is installed on machines that do not need it.
- CPU frequency: mean cpufreq policy frequency, with `/proc/cpuinfo` fallback.
- CPU package power: readable hwmon sensors or a short RAPL energy interval, including counter wrap. RAPL permissions are not elevated. Unsupported or restricted sensors stay unavailable.
- RAM: MemTotal minus MemAvailable, in GiB. Disk tiles show used/total GiB for local mount points, including `/`.
- CPU TDP is **manually supplied from the CPU specification**, not inferred from power consumption. Zero means unknown. Driver power limits have separate labels. AMD APU power can include CPU and GPU; the underlying driver determines the scope.

The standard-library Python reader runs asynchronously outside GNOME Shell. It only runs while the strip is visible, never overlaps a previous sample, bounds NVIDIA queries to two seconds and the reader process to four seconds, and never writes hardware settings. Failed or removed sensors produce N/A and a graph gap. History is bounded and cleared on hiding/configuration changes. This requires `python3-core`, declared by the terminal RPM.

## Research

- [Linux hwmon ABI](https://docs.kernel.org/hwmon/sysfs-interface.html): optional attributes, millidegree temperatures, microwatt power, device discovery and fault indicators. Sensor names are not interchangeable across motherboard drivers.
- [AMDGPU monitoring](https://docs.kernel.org/gpu/amdgpu/thermal.html): temperature channels, clock units, power caps and combined APU power.
- [NVIDIA SMI](https://docs.nvidia.com/deploy/nvidia-smi/index.html): query fields, N/A support and stable UUID identification. NVML has a stronger compatibility guarantee; the existing driver utility avoids adding a Python binding dependency here.
- [GNOME Shell popup menus](https://github.com/GNOME/gnome-shell/blob/main/js/ui/popupMenu.js): modal menu lifecycle and GNOME 51 gesture-based input.

## Validation

Run `node --test tests/terminal-*.test.mjs`, `python3 -m unittest discover -s tests -p test_terminal_hardware.py`, and `glib-compile-schemas --strict --dry-run packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/schemas`.

Tests cover two GPUs, stable identity after enumeration changes, NVIDIA unsupported values, unit conversions, RAM, escaped mount paths, history gaps, TDP semantics, ordering, and reserved strip space while resizing. Existing terminal startup/gesture/lifecycle tests also run.

Before release, smoke-test under GNOME 51: open/close animations, right-click source selection with two GPUs, setting persistence after logout, overview, pinning, full-height resizing, fractional/HiDPI scaling, secondary monitor, sensor removal, and missing NVIDIA driver. This implementation was developed on macOS; live GNOME rendering and physical sensor readings have not been validated here.
