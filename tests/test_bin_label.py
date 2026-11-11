import gettext
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'root/usr/libexec/infinityos-bin-label'


@unittest.skipUnless(all(shutil.which(tool) for tool in ('msgfmt', 'msgunfmt', 'msgfilter')), 'gettext tools required')
class BinLabelTests(unittest.TestCase):
    def test_translations_change_without_renaming_message_ids_or_other_languages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            po = root / 'catalog.po'
            po.write_text('''msgid ""
msgstr "Content-Type: text/plain; charset=UTF-8\\nLanguage: en_GB\\n"

msgid "Trash"
msgstr "Wastebasket"

msgid "Trash is Empty"
msgstr "Wastebasket is Empty"

msgid "Open the trash"
msgstr "Open the wastebasket"

msgid "Files"
msgstr "Files"
''')
            target = root / 'en_GB/LC_MESSAGES/nautilus.mo'
            target.parent.mkdir(parents=True)
            subprocess.run(['msgfmt', '-o', str(target), str(po)], check=True)
            polish = root / 'pl/LC_MESSAGES/nautilus.mo'
            polish.parent.mkdir(parents=True)
            polish.write_bytes(target.read_bytes())
            original = polish.read_bytes()
            subprocess.run([str(SCRIPT), str(root)], check=True)
            with target.open('rb') as stream:
                catalog = gettext.GNUTranslations(stream)
            self.assertEqual(catalog.gettext('Trash'), 'Bin')
            self.assertEqual(catalog.gettext('Trash is Empty'), 'Bin is Empty')
            self.assertEqual(catalog.gettext('Open the trash'), 'Open the bin')
            self.assertEqual(catalog.gettext('Files'), 'Files')
            self.assertEqual(polish.read_bytes(), original)
            first = target.read_bytes()
            subprocess.run([str(SCRIPT), str(root)], check=True)
            self.assertEqual(target.read_bytes(), first)
