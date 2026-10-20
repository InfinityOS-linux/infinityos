"""Keep the user recovery command limited to the selected GNOME extension."""

import contextlib
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "root/usr/bin/infinityos-shell-recover"
namespace = {"__name__": "infinityos_shell_recover"}
exec(compile(SOURCE.read_text(), str(SOURCE), "exec"), namespace)


class FakeSettings:
    def __init__(self):
        self.enabled = ["bad@example.org", "good@example.org"]

    def get_strv(self, _key):
        return list(self.enabled)

    def set_strv(self, _key, value):
        self.enabled = list(value)


class ShellRecoveryTests(unittest.TestCase):
    def test_disabling_one_extension_keeps_the_other(self):
        settings = FakeSettings()
        gi = types.ModuleType("gi")
        repository = types.ModuleType("gi.repository")
        repository.Gio = types.SimpleNamespace(Settings=types.SimpleNamespace(
            new=lambda _schema: settings))
        gi.repository = repository
        with patch.dict(sys.modules, {"gi": gi, "gi.repository": repository}), \
             patch.object(sys, "argv", ["infinityos-shell-recover", "--disable", "bad@example.org"]), \
             patch.object(namespace["os"], "geteuid", return_value=1000), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(namespace["main"](), 0)
        self.assertEqual(settings.enabled, ["good@example.org"])


if __name__ == "__main__":
    unittest.main()
