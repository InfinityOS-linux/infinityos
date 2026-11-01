"""The lock-screen-only extension must not fail the user-session smoke test."""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-audit-desktop"
SPEC = importlib.util.spec_from_loader("infinityos_audit_desktop", importlib.machinery.SourceFileLoader("infinityos_audit_desktop", str(SCRIPT)))
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class DesktopAuditTests(unittest.TestCase):
    def test_unlock_dialog_extension_is_enabled_but_not_expected_active(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            defaults = root / "gnome-defaults"
            defaults.write_text("enabled-extensions=['desktop@test', 'lock@test']\n")
            extensions = root / "extensions"
            for uuid, modes in (("desktop@test", None),
                                ("lock@test", ["unlock-dialog"])):
                folder = extensions / uuid
                folder.mkdir(parents=True)
                metadata = {} if modes is None else {"session-modes": modes}
                (folder / "metadata.json").write_text(json.dumps(metadata))
            self.assertEqual(audit.expected_extensions(defaults, extensions),
                             (["desktop@test", "lock@test"], ["desktop@test"]))


if __name__ == "__main__":
    unittest.main()
