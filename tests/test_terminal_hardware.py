import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/hardware-snapshot.py'
spec = importlib.util.spec_from_file_location('hardware', SCRIPT)
hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hardware)


class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, text):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def gpu(self, index, bus, value):
        device = self.root / f'sys/devices/pci0000:00/{bus}'
        hw = device / f'hwmon/hwmon{index}'
        hw.mkdir(parents=True)
        (hw / 'name').write_text('amdgpu')
        (hw / 'temp1_input').write_text(str(value))
        (hw / 'freq1_input').write_text('2200000000')
        (hw / 'power1_average').write_text('65000000')
        (hw / 'device').symlink_to(device)
        link = self.root / f'sys/class/hwmon/hwmon{index}'
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(hw)
        return hw, link

    def test_two_gpus_have_distinct_stable_ids_and_correct_units(self):
        first, link = self.gpu(0, '0000:03:00.0', 54000)
        self.gpu(1, '0000:04:00.0', 48000)
        before = hardware.snapshot(self.root, nvidia=False)
        temps = [m for m in before if m['unit'] == '°C']
        self.assertEqual([m['value'] for m in temps], [54, 48])
        self.assertNotEqual(temps[0]['id'], temps[1]['id'])
        self.assertTrue(any(m['value'] == 2.2 and m['unit'] == 'GHz' for m in before))
        self.assertTrue(any(m['value'] == 65 and m['unit'] == 'W' for m in before))
        link.unlink()
        link.with_name('hwmon9').symlink_to(first)
        after = hardware.snapshot(self.root, nvidia=False)
        self.assertEqual({m['id'] for m in before}, {m['id'] for m in after})

    def test_missing_faulty_and_invalid_readings_are_not_zero(self):
        hw, _ = self.gpu(0, '0000:03:00.0', 54000)
        (hw / 'temp1_fault').write_text('1')
        (hw / 'power1_average').write_text('NaN')
        metrics = hardware.snapshot(self.root, nvidia=False)
        self.assertIsNone(next(m['value'] for m in metrics if m['unit'] == '°C'))
        self.assertIsNone(next(m['value'] for m in metrics if m['unit'] == 'W'))
        self.assertIsNone(next(m['value'] for m in metrics if m['id'] == 'memory:used'))
        self.assertIsNone(hardware.number('N/A'))
        self.assertIsNone(hardware.number('inf'))

    def test_memory_clocks_and_mount_names(self):
        self.write('proc/meminfo', 'MemTotal: 33554432 kB\nMemAvailable: 20971520 kB\n')
        self.write('sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq', '4000000')
        self.write('sys/devices/system/cpu/cpufreq/policy1/scaling_cur_freq', '5000000')
        self.write('proc/self/mountinfo', '31 20 8:1 / /media/My\\040Disk rw - ext4 /dev/sda1 rw\n')
        data = {m['id']: m for m in hardware.snapshot(self.root, nvidia=False)}
        self.assertEqual(data['memory:used']['value'], 12)
        self.assertEqual(data['memory:used']['maximum'], 32)
        self.assertEqual(data['cpu:clock']['value'], 4.5)
        self.assertIn('disk:/media/My Disk', data)

    def test_nvidia_uuid_survives_reordering_and_na(self):
        text = 'GPU-aaa, RTX 4090, 00000000:01:00.0, 54, 2400, 65, 450, 1024, 24576\nGPU-bbb, RTX 4090, 00000000:02:00.0, N/A, 2200, [Not Supported], N/A, 512, 24576\n'
        rows = hardware.nvidia_rows(text)
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[1][3][0])
        self.assertIsNone(rows[1][3][2])
        self.assertEqual({r[0] for r in rows}, {r[0] for r in hardware.nvidia_rows('\n'.join(reversed(text.splitlines())))})
        with patch.object(hardware.shutil, 'which', return_value='/usr/bin/nvidia-smi'), patch.object(hardware.subprocess, 'run') as run:
            run.return_value.stdout = text
            data = {m['id']: m for m in hardware.snapshot(self.root)}
        self.assertEqual(data['nvidia:GPU-aaa:clock']['value'], 2.4)
        self.assertEqual(data['nvidia:GPU-bbb:memory']['value'], 0.5)
        self.assertNotEqual(data['nvidia:GPU-aaa:temp']['label'], data['nvidia:GPU-bbb:temp']['label'])


if __name__ == '__main__':
    unittest.main()
