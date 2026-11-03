import runpy
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
module = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-refind-short-labels'))


def image(machine=0x8664):
    data = bytearray(512)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<H', data, 132, machine)
    struct.pack_into('<H', data, 152, 0x20b)
    data.extend(module['OLD'])
    return bytes(data)


class RefindLabelTests(unittest.TestCase):
    def test_only_label_and_checksum_change_on_both_architectures(self):
        for machine in (0x8664, 0xaa64):
            original = image(machine)
            result = module['shorten'](original)
            self.assertEqual(len(result), len(original))
            self.assertEqual(result[:216], original[:216])
            self.assertEqual(result[220:512], original[220:512])
            self.assertTrue(result.endswith(module['NEW']))
            self.assertEqual(module['shorten'](result), result)

    def test_signed_or_unknown_images_are_rejected(self):
        signed = bytearray(image())
        struct.pack_into('<II', signed, 296, 400, 20)
        for data in (signed, b'not an EFI image', image().replace(module['OLD'], b'\0' * len(module['OLD']))):
            with self.assertRaises(ValueError):
                module['shorten'](data)
