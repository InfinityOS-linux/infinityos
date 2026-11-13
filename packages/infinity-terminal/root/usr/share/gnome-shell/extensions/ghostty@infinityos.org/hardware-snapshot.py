#!/usr/bin/python3
"""Read-only hardware snapshot; isolated from the Shell main loop, no extra modules."""
import csv
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return ""


def number(value, divisor=1):
    try:
        value = float(value) / divisor
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def nvidia_rows(text):
    result = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 9:
            continue
        uuid, name, bus, temp, clock, power, limit, used, total = [v.strip() for v in row]
        if not uuid.startswith('GPU-'):
            continue
        result.append((uuid, name, bus, [number(v) for v in (temp, clock, power, limit, used, total)]))
    return result


def snapshot(root=Path('/'), nvidia=True):
    metrics = []
    def add(key, label, group, value, unit, maximum=None):
        metrics.append(dict(id=key, label=label, group=group, value=value, unit=unit, maximum=maximum))
    sys = root / 'sys'
    proc = root / 'proc'
    # Stable device paths (not hwmonN or cardN) survive enumeration changes.
    for hw in sorted((sys / 'class/hwmon').glob('hwmon*')):
        name = read(hw / 'name') or 'Sensor'
        device = (hw / 'device').resolve() if (hw / 'device').exists() else hw.resolve().parent.parent
        identity = str(device).removeprefix(str(root))
        group = f'{name} ({device.name})'
        cpu = name in ('coretemp', 'k10temp', 'zenpower', 'cpu_thermal')
        gpu = name in ('amdgpu', 'nouveau', 'i915', 'xe')
        try:
            paths = sorted(hw.iterdir())
        except OSError:
            continue
        for path in paths:
            match = re.fullmatch(r'(temp|power|freq|fan)([0-9]+)_(input|average|cap)', path.name)
            if not match:
                continue
            kind, channel, field = match.groups()
            if field == 'cap' and kind != 'power':
                continue
            if field == 'average' and kind != 'power':
                continue
            if kind == 'power' and field == 'input' and (hw / f'power{channel}_average').exists():
                continue
            suffix = read(hw / f'{kind}{channel}_label') or channel
            title = {'temp': 'Temp', 'power': 'Power', 'freq': 'Clock', 'fan': 'Fan'}[kind]
            if field == 'cap':
                title = 'Power Limit'
            prefix = 'CPU' if cpu else 'GPU' if gpu else name
            scale, unit = {'temp': (1000, '°C'), 'power': (1000000, 'W'), 'freq': (1000000000, 'GHz'), 'fan': (1, 'RPM')}[kind]
            value = number(read(path), scale)
            if read(hw / f'{kind}{channel}_fault') == '1':
                value = None
            add(f'hwmon:{identity}:{name}:{kind}{channel}:{"cap" if field == "cap" else "value"}',
                f'{prefix} {title} · {suffix}' + (f' ({device.name})' if gpu else ''), group, value, unit)
    # RAPL is often root-only. Never elevate permissions for monitoring.
    packages = []
    for path in sorted((sys / 'class/powercap').glob('intel-rapl:*')):
        name = read(path / 'name')
        if not name.startswith('package-'):
            continue
        identity = f'rapl:{name}'
        energy = number(read(path / 'energy_uj'))
        maximum = number(read(path / 'max_energy_range_uj'))
        packages.append((path, name, identity, energy, maximum))
        for constraint in path.glob('constraint_*_name'):
            if read(constraint) == 'long_term':
                cap = constraint.with_name(constraint.name.replace('_name', '_power_limit_uw'))
                add(f'{identity}:limit', f'CPU Power Limit · {name}', name, number(read(cap), 1000000), 'W')
    if packages:
        started = time.monotonic()
        time.sleep(0.05)
        elapsed = time.monotonic() - started
        for path, name, identity, previous, maximum in packages:
            current = number(read(path / 'energy_uj'))
            power = None
            if previous is not None and current is not None:
                delta = current - previous
                if delta < 0 and maximum:
                    delta += maximum
                if delta >= 0:
                    power = delta / 1000000 / elapsed
            add(f'{identity}:power', f'CPU Power · {name}', name, power, 'W')
    clocks = [number(read(p), 1000000) for p in (sys / 'devices/system/cpu/cpufreq').glob('policy*/scaling_cur_freq')]
    clocks = [v for v in clocks if v is not None]
    if not clocks:
        clocks = [number(line.split(':', 1)[1], 1000) for line in read(proc / 'cpuinfo').splitlines() if line.startswith('cpu MHz')]
        clocks = [v for v in clocks if v is not None]
    add('cpu:clock', 'CPU Clock', 'System', sum(clocks) / len(clocks) if clocks else None, 'GHz')
    memory = {}
    for line in read(proc / 'meminfo').splitlines():
        parts = line.replace(':', '').split()
        if len(parts) >= 2:
            memory[parts[0]] = number(parts[1])
    total, available = memory.get('MemTotal'), memory.get('MemAvailable')
    add('memory:used', 'RAM', 'System', (total - available) / 1048576 if total and available is not None else None,
        'GiB', total / 1048576 if total else None)
    mounts = {'/'}
    for line in read(proc / 'self/mountinfo').splitlines():
        before, sep, after = line.partition(' - ')
        fields = before.split()
        if sep and len(fields) > 4 and after.split()[0] in ('ext4', 'ext3', 'btrfs', 'xfs', 'f2fs', 'vfat', 'exfat', 'ntfs3', 'zfs'):
            mounts.add(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), fields[4]))
    for mount in sorted(mounts):
        try:
            usage = shutil.disk_usage(root / mount.lstrip('/'))
            value, maximum = usage.used / 1073741824, usage.total / 1073741824
        except OSError:
            value, maximum = None, None
        add(f'disk:{mount}', f'Disk Used · {mount}', 'Disks', value, 'GiB', maximum)
    if nvidia and shutil.which('nvidia-smi'):
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=uuid,name,pci.bus_id,temperature.gpu,clocks.gr,power.draw,power.limit,memory.used,memory.total',
                                     '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=2, check=True)
            for uuid, name, bus, values in nvidia_rows(result.stdout):
                temp, clock, power, limit, used, total = values
                group = f'{name} ({bus})'
                for key, label, value, unit, maximum in (
                    ('temp', 'GPU Temp', temp, '°C', None),
                    ('clock', 'GPU Clock', clock / 1000 if clock is not None else None, 'GHz', None),
                    ('power', 'GPU Power', power, 'W', None),
                    ('limit', 'GPU Power Limit', limit, 'W', None),
                    ('memory', 'VRAM', used / 1024 if used is not None else None, 'GiB', total / 1024 if total else None)):
                    add(f'nvidia:{uuid}:{key}', f'{label} · {name} ({bus})', group, value, unit, maximum)
        except (OSError, subprocess.SubprocessError):
            pass
    return metrics


if __name__ == '__main__':
    print(json.dumps(snapshot(), allow_nan=False))
