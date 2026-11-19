import configparser
import ctypes
import ctypes.util
import json
from pathlib import Path
import runpy
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'root/usr/share/icons/InfinityOS-Modern-Ice'


class CursorAssetsTests(unittest.TestCase):
    def test_gnome_scalable_wait_and_progress_have_the_approved_animation(self):
        scalable = THEME / 'cursors_scalable'
        self.assertEqual((scalable / 'progress').readlink().as_posix(), 'wait')
        metadata = json.loads((scalable / 'wait/metadata.json').read_text())
        builder = runpy.run_path(str(ROOT / 'scripts/build-infinity-cursors'))
        poses = list(builder['waiting_poses']())
        self.assertEqual(len(metadata), 40)
        self.assertEqual(sum(frame['delay'] for frame in metadata), 800)
        for frame, (pressure, delay) in zip(metadata, poses):
            self.assertEqual((frame['nominal_size'], frame['hotspot_x'], frame['hotspot_y']),
                             (256, 128, 160))
            self.assertEqual(frame['delay'], delay)
            filename = scalable / 'wait' / frame['filename']
            self.assertEqual(filename.read_bytes(), builder['waiting_svg'](pressure))
            svg = ET.fromstring(filename.read_bytes())
            self.assertEqual((svg.get('width'), svg.get('height')), ('256', '256'))

    def test_wait_animation_keeps_palm_hotspot_and_transparency_fixed(self):
        data = (THEME / 'cursors/wait').read_bytes()
        magic, header, version, count = struct.unpack_from('<4s3I', data)
        self.assertEqual((magic, header, version, count), (b'Xcur', 16, 0x10000, 280))
        groups = {}
        previous_end = header + count * 12
        for index in range(count):
            kind, size, offset = struct.unpack_from('<3I', data, header + index * 12)
            self.assertEqual(offset, previous_end)
            chunk = struct.unpack_from('<9I', data, offset)
            self.assertEqual(chunk[:8], (36, 0xFFFD0002, size, 1, size, size,
                                         size // 2, round(size * .625)))
            pixels = data[offset + 36:offset + 36 + size * size * 4]
            self.assertEqual(len(pixels), size * size * 4)
            self.assertIn(0, pixels[3::4])
            self.assertIn(255, pixels[3::4])
            for b, g, r, alpha in struct.iter_unpack('4B', pixels):
                self.assertLessEqual(max(r, g, b), alpha)
            groups.setdefault(size, []).append((chunk[8], pixels))
            previous_end = offset + 36 + len(pixels)
        self.assertEqual(previous_end, len(data))
        self.assertEqual(set(groups), {16, 24, 32, 48, 64, 96, 128})
        for size, frames in groups.items():
            self.assertEqual([delay for delay, _ in frames], [20] * 40)
            # Below the finger roots, every pixel stays identical for the whole loop.
            palm_start = round(size * .56) * size * 4
            self.assertEqual(len({pixels[palm_start:] for _, pixels in frames}), 1)
            self.assertGreaterEqual(len({pixels for _, pixels in frames}), 12)
            self.assertNotEqual(frames[0][1], frames[-1][1], 'the loop must start with a tap, not the resting pose')
            self.assertEqual(sum(delay for delay, _ in frames), 800)
            self.assertGreaterEqual(len({pixels for _, pixels in frames[:4]}), 3, 'fingers must visibly change within 80 ms')
            if size >= 32:
                def fingertip(pixels, x):
                    column = round(x * size / 256)
                    return next(row for row in range(round(size * .56))
                                if pixels[(row * size + column) * 4 + 3] >= 128)
                # Each finger visibly shortens in the native asset, not just
                # the enlarged preview. The small finger moves by at least 2px
                # at 32px, and the longer fingers move farther.
                for x, peak, minimum in ((80, 4, 4), (121, 10, 5),
                                          (163, 16, 4), (198, 22, 2)):
                    movement = fingertip(frames[peak][1], x) - fingertip(frames[-1][1], x)
                    self.assertGreaterEqual(movement, minimum * size // 32)
                thumb = lambda pixels: b''.join(
                    pixels[row * size * 4:(row * size + round(size * .2)) * 4]
                    for row in range(round(size * .43), round(size * .56)))
                self.assertEqual(len({thumb(pixels) for _, pixels in frames}), 1)

    def test_busy_names_resolve_to_the_wait_animation(self):
        for name in ('watch', 'progress', 'left_ptr_watch', 'default_wait', 'half-busy',
                     'busy', '0426c94ea35c87780ff01dc239897213',
                     '08e8e1c95fe2fc01f976f1e063a24ccd',
                     '3ecb610c1bf2410f44200f48c40d3599'):
            with self.subTest(name=name):
                path = THEME / 'cursors' / name
                self.assertEqual(path.readlink().as_posix(), 'wait')
                self.assertEqual(path.resolve(), (THEME / 'cursors/wait').resolve())

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

    def test_native_xcursor_loader_reads_all_wait_frames(self):
        library = ctypes.util.find_library('Xcursor')
        if not library:
            self.skipTest('Native libXcursor is unavailable on this host')
        class Image(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint) for name in
                        ('version', 'size', 'width', 'height', 'xhot', 'yhot', 'delay')] + [('pixels', ctypes.c_void_p)]
        class Images(ctypes.Structure):
            _fields_ = [('nimage', ctypes.c_int),
                        ('images', ctypes.POINTER(ctypes.POINTER(Image))),
                        ('name', ctypes.c_char_p)]
        lib = ctypes.CDLL(library)
        lib.XcursorFilenameLoadImages.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.XcursorFilenameLoadImages.restype = ctypes.POINTER(Images)
        lib.XcursorImagesDestroy.argtypes = [ctypes.POINTER(Images)]
        for size in (16, 24, 32, 48, 64, 96, 128):
            loaded = lib.XcursorFilenameLoadImages(bytes(THEME / 'cursors/wait'), size)
            self.assertTrue(loaded)
            try:
                self.assertEqual(loaded.contents.nimage, 40)
                for index in range(loaded.contents.nimage):
                    image = loaded.contents.images[index].contents
                    self.assertEqual((image.width, image.height), (size, size))
                    self.assertEqual((image.xhot, image.yhot), (size // 2, round(size * .625)))
                    self.assertEqual(image.delay, 20)
            finally:
                lib.XcursorImagesDestroy(loaded)
