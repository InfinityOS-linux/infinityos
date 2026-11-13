"""Run the theme in Plymouth's interpreter with a simulated changing display."""
import ctypes
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Result(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('object', ctypes.c_void_p)]


class State(ctypes.Structure):
    _fields_ = [(name, ctypes.c_void_p) for name in ('user_data', 'global_', 'local', 'this')]


class PlymouthAnimationTests(unittest.TestCase):
    def test_frames_are_preloaded_and_finished_animation_follows_display(self):
        libraries = list(Path('/usr/lib').glob('*/plymouth/script.so'))
        libraries += list(Path('/usr/lib64/plymouth').glob('script.so'))
        if not libraries:
            self.skipTest('Plymouth script plugin is required')
        lib = ctypes.CDLL(str(libraries[0]))
        pointer = ctypes.c_void_p
        for name, args, result in (
            ('script_state_new', [pointer], ctypes.POINTER(State)),
            ('script_lib_math_setup', [pointer], pointer),
            ('script_lib_string_setup', [pointer], pointer),
            ('script_lib_string_destroy', [pointer], None),
            ('script_parse_string', [ctypes.c_char_p, ctypes.c_char_p], pointer),
            ('script_execute', [pointer, pointer], Result),
            ('script_obj_hash_get_number', [pointer, ctypes.c_char_p], ctypes.c_double),
            ('script_parse_op_free', [pointer], None),
            ('script_lib_math_destroy', [pointer], None),
            ('script_state_destroy', [pointer], None),
        ):
            function = getattr(lib, name)
            function.argtypes, function.restype = args, result
        state = lib.script_state_new(None)
        math = lib.script_lib_math_setup(state)
        strings = lib.script_lib_string_setup(state)
        source = (ROOT / 'tests/fixtures/plymouth-renderer.script').read_text()
        source += (ROOT / 'root/usr/share/plymouth/themes/infinityos/infinityos.script').read_text()
        source += '''
message("Running %posttrans scriptlet: infinity-updater-1.1.0...");
post_ok=(message_sprite.image.text == "Finalizing updates...");
message("Running post-transaction scriptlet: package...");
legacy_post_ok=(message_sprite.image.text == "Finalizing updates...");
message("Running %pretrans scriptlet: package...");
pre_ok=(message_sprite.image.text == "Preparing updates...");
message("Running pre-transaction scriptlet: package...");
legacy_pre_ok=(message_sprite.image.text == "Preparing updates...");
message("Error in %posttrans scriptlet: package");
error_ok=(message_sprite.image.text == "Error in %posttrans scriptlet: package");
message("[1/3] Upgrading package...");
progress_ok=(message_sprite.image.text == "[1/3] Upgrading package...");
loaded_before_refresh=loads;
for(tick=0;tick<100;tick++) refresh();
screen_width=1920; screen_height=1080; refresh();
result_x=logo.x; result_y=logo.y;
screen_width=320; screen_height=240; refresh();
small_x=logo.x; small_y=logo.y; small_width=logo.image.width;
'''
        operation = lib.script_parse_string(source.encode(), b'infinityos-test')
        self.assertTrue(operation)
        try:
            self.assertEqual(lib.script_execute(state, operation).type, 0)
            for key, expected in dict(post_ok=1, legacy_post_ok=1, pre_ok=1, legacy_pre_ok=1,
                                      error_ok=1, progress_ok=1, loaded_before_refresh=90, loads=90, frame=89,
                                      result_x=816, result_y=459, small_x=64,
                                      small_y=66, small_width=192).items():
                with self.subTest(key=key):
                    self.assertAlmostEqual(lib.script_obj_hash_get_number(state.contents.global_, key.encode()), expected)
        finally:
            lib.script_parse_op_free(operation)
            lib.script_lib_string_destroy(strings)
            lib.script_lib_math_destroy(math)
            lib.script_state_destroy(state)
