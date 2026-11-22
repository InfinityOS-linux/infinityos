import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


HELPER = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-automount"


class MountError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

    def matches(self, domain, code):
        return domain == "gio" and code == self.code


class Volume:
    def __init__(self, uuid, device="/dev/sdb1", mounted=False, mountable=True):
        self.uuid = uuid
        self.device = device
        self.mounted = mounted
        self.mountable = mountable
        self.mount = Mock()

    def get_identifier(self, kind):
        return self.uuid if kind == "uuid" else self.device

    def get_mount(self):
        return object() if self.mounted else None

    def can_mount(self):
        return self.mountable

    def mount_finish(self, result):
        if result:
            raise result
        self.mounted = True

    def finish(self, result=None):
        callback = self.mount.call_args.args[3]
        callback(self, result, None)


class AutomountTests(unittest.TestCase):
    def setUp(self):
        self.selected = ["chosen"]
        self.volumes = []
        self.glib = SimpleNamespace(
            Error=MountError,
            SOURCE_REMOVE=False,
            idle_add=Mock(return_value=1),
            timeout_add_seconds=Mock(return_value=2),
            source_remove=Mock(),
        )
        gio = SimpleNamespace(
            VOLUME_IDENTIFIER_KIND_UUID="uuid",
            VOLUME_IDENTIFIER_KIND_UNIX_DEVICE="unix-device",
            Cancellable=Mock(side_effect=Mock),
            MountMountFlags=SimpleNamespace(NONE=0),
            IOErrorEnum=SimpleNamespace(CANCELLED="cancelled", ALREADY_MOUNTED="already-mounted"),
            io_error_quark=lambda: "gio",
        )
        repository = SimpleNamespace(Gio=gio, GLib=self.glib)
        loader = importlib.machinery.SourceFileLoader("automount", str(HELPER))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"gi": SimpleNamespace(repository=repository), "gi.repository": repository}):
            loader.exec_module(module)
        self.settings = SimpleNamespace(connect=Mock(), get_strv=lambda _key: self.selected)
        self.monitor = SimpleNamespace(connect=Mock(), get_volumes=lambda: self.volumes)
        self.service = module.Automount(self.settings, self.monitor)

    def test_only_selected_local_volumes_are_mounted_without_a_prompt(self):
        chosen = Volume("chosen")
        missing_id = Volume(None)
        other = Volume("another")
        network = Volume("chosen", device=None)
        self.volumes = [chosen, missing_id, other, network]
        self.service.scan()
        chosen.mount.assert_called_once()
        self.assertEqual(chosen.mount.call_args.args[:2], (0, None))
        self.glib.timeout_add_seconds.assert_called_once()
        for volume in (missing_id, other, network):
            volume.mount.assert_not_called()
        chosen.finish()
        self.glib.source_remove.assert_called_once_with(2)

    def test_missing_volume_is_ignored_and_can_mount_after_connection(self):
        self.assertFalse(self.service.scan())
        self.assertFalse(self.service.pending)
        chosen = Volume("chosen")
        self.volumes = [chosen]
        added = dict(call.args for call in self.monitor.connect.call_args_list)["volume-added"]
        added(self.monitor, chosen)
        self.glib.idle_add.call_args.args[0]()
        chosen.mount.assert_called_once()

    def test_duplicate_uuids_are_skipped(self):
        self.volumes = [Volume("chosen"), Volume("chosen", device="/dev/sdc1")]
        with self.assertLogs(level="WARNING"):
            self.service.scan()
        for volume in self.volumes:
            volume.mount.assert_not_called()

    def test_manual_unmount_does_not_remount_a_connected_volume(self):
        chosen = Volume("chosen", mounted=True)
        self.volumes = [chosen]
        self.service.scan()
        chosen.mounted = False
        self.service.scan()
        chosen.mount.assert_not_called()

    def test_removal_or_deselection_cancels_pending_mount(self):
        for removed in (True, False):
            with self.subTest(removed=removed):
                chosen = Volume("chosen")
                self.volumes = [chosen]
                self.service.scan()
                cancellable = chosen.mount.call_args.args[2]
                if removed:
                    self.volumes = []
                    self.service.volume_removed(self.monitor, chosen)
                else:
                    self.selected = []
                    self.service.settings_changed()
                cancellable.cancel.assert_called_once()
                chosen.finish(MountError("cancelled", "Cancelled"))
                self.assertFalse(self.service.pending)
                self.selected = ["chosen"]

    def test_slow_and_failed_mounts_do_not_retry_or_stop_other_volumes(self):
        self.selected.append("second")
        chosen = Volume("chosen")
        second = Volume("second", device="/dev/sdc1")
        self.volumes = [chosen, second]
        self.service.scan()
        timeout = self.glib.timeout_add_seconds.call_args_list[0].args[1]
        with self.assertLogs(level="WARNING"):
            self.assertFalse(timeout())
            second.finish(MountError("permission-denied", "Authorization required"))
        chosen.mount.call_args.args[2].cancel.assert_called_once()
        chosen.finish(MountError("cancelled", "Cancelled"))
        self.service.scan()
        chosen.mount.assert_called_once()
        second.mount.assert_called_once()

    def test_startup_ready_waits_for_the_initial_mounts_only(self):
        chosen = Volume("chosen")
        self.volumes = [chosen]
        ready = self.service.ready_file = Mock()
        self.service.scan()
        ready.touch.assert_not_called()
        chosen.finish()
        ready.touch.assert_called_once()
        self.service.scan()
        ready.touch.assert_called_once()

    def test_unavailable_drive_does_not_delay_steam(self):
        ready = self.service.ready_file = Mock()
        self.service.scan()
        ready.touch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
