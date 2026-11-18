import configparser
import ctypes
import ctypes.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'root/usr/share/icons/InfinityOS-Modern-Ice'


class CursorAssetsTests(unittest.TestCase):
    def test_theme_inherits_existing_pointer_shapes(self):
        config = configparser.ConfigParser()
        config.read(THEME / 'index.theme')
        self.assertEqual(config['Icon Theme']['Inherits'], 'Bibata-Modern-Ice')

    def test_both_gloves_have_matching_hotspots_and_valid_premultiplied_pixels(self):
        states = []
        for name in ('grab', 'grabbing'):
            data = (THEME / 'cursors' / name).read_bytes()
            magic, header, version, count = struct.unpack_from('<4s3I', data)
            self.assertEqual((magic, header, version, count), (b'Xcur', 16, 0x10000, 7))
            geometry = []
            for i in range(count):
                kind, size, offset = struct.unpack_from('<3I', data, header + i * 12)
                chunk = struct.unpack_from('<9I', data, offset)
                self.assertEqual(chunk[:6], (36, kind, size, 1, size, size))
                self.assertEqual(kind, 0xFFFD0002)
                self.assertEqual(chunk[6:8], (size // 2, round(size * .625)))
                geometry.append(chunk[4:8])
                pixels = data[offset + 36:offset + 36 + size * size * 4]
                self.assertEqual(len(pixels), size * size * 4)
                self.assertIn(0, pixels[3::4])
                self.assertIn(255, pixels[3::4])
                for r, g, b, alpha in struct.iter_unpack('4B', pixels):
                    self.assertLessEqual(max(r, g, b), alpha)
            states.append(geometry)
        self.assertEqual(states[0], states[1])

    def test_native_xcursor_loader_accepts_every_size(self):
        library = ctypes.util.find_library('Xcursor')
        if not library:
            self.skipTest('Native libXcursor is unavailable on this host')
        class Image(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint) for name in
                        ('version', 'size', 'width', 'height', 'xhot', 'yhot', 'delay')] + [('pixels', ctypes.c_void_p)]
        lib = ctypes.CDLL(library)
        lib.XcursorFilenameLoadImage.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.XcursorFilenameLoadImage.restype = ctypes.POINTER(Image)
        lib.XcursorImageDestroy.argtypes = [ctypes.POINTER(Image)]
        for name in ('grab', 'grabbing'):
            for size in (16, 24, 32, 48, 64, 96, 128):
                image = lib.XcursorFilenameLoadImage(bytes(THEME / 'cursors' / name), size)
                self.assertTrue(image)
                try:
                    self.assertEqual((image.contents.width, image.contents.height), (size, size))
                    self.assertEqual((image.contents.xhot, image.contents.yhot), (size // 2, round(size * .625)))
                finally:
                    lib.XcursorImageDestroy(image)
