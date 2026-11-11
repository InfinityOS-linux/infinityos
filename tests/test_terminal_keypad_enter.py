"""Keypad Enter must terminate a canonical, echo-disabled password read."""
import os
from pathlib import Path
import pty
import select
import termios
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'packages/infinity-terminal/root/usr/share/infinityos/ghostty/config'


class KeypadEnterTests(unittest.TestCase):
    def test_keypad_enter_submits_without_echo(self):
        bindings = [line.split('=', 1)[1].strip() for line in CONFIG.read_text().splitlines()
                    if line.startswith('keybind =')]
        binding = next((entry for entry in bindings if entry.startswith('kp_enter=')), None)
        self.assertEqual(binding, r'kp_enter=text:\r')
        payload = binding.split('text:', 1)[1].encode().decode('unicode_escape').encode()
        master, slave = pty.openpty()
        try:
            attrs = termios.tcgetattr(slave)
            attrs[0] |= termios.ICRNL
            attrs[3] = (attrs[3] | termios.ICANON) & ~(termios.ECHO | termios.ECHONL)
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            # Application-keypad Enter cannot complete a password-style line read.
            os.write(master, b'test-value\x1bOM')
            self.assertFalse(select.select([slave], [], [], 0.05)[0])
            termios.tcflush(slave, termios.TCIFLUSH)
            os.write(master, b'test-value' + payload)
            self.assertTrue(select.select([slave], [], [], 1)[0])
            self.assertEqual(os.read(slave, 128), b'test-value\n')
            self.assertFalse(select.select([master], [], [], 0.05)[0])
        finally:
            os.close(master)
            os.close(slave)
