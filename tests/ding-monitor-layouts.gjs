// Real GJS/GIO/GVfs metadata persistence; run inside dbus-run-session and Xvfb.
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk?version=4.0';

Gtk.init();
const appPath = ARGV[0];
const {FileItem} = await import(GLib.filename_to_uri(`${appPath}/fileItem.js`, null));
const Layouts = await import(GLib.filename_to_uri(`${appPath}/monitorLayouts.js`, null));
const laptop = {x: 0, y: 0, width: 800, height: 600, scaleFactor: 1};
const external = {...laptop, x: 800};
const manager = {_iconLayoutKey: Layouts.layoutKey([laptop, external])};
const directory = GLib.dir_make_tmp('infinity-ding-metadata-XXXXXX');
const file = Gio.File.new_for_path(`${directory}/icon.txt`);
GLib.file_set_contents(file.get_path(), 'desktop contents remain unchanged\n');

function check(condition, message) {
    if (!condition)
        throw new Error(message);
}

function reload() {
    const info = file.query_info('metadata::*', Gio.FileQueryInfoFlags.NONE, null);
    const item = Object.create(FileItem.prototype);
    item._desktopManager = manager;
    item._file = file;
    item._readSavedPositions(info);
    return item;
}

try {
    file.set_attribute_string('metadata::nautilus-icon-position', '1102,202', Gio.FileQueryInfoFlags.NONE, null);
    manager._iconLayoutKey = Layouts.layoutKey([laptop]);
    let item = reload();
    item._grid = {};
    item.getCoordinates = () => [702, 202];
    item.rememberMonitorPosition();
    item = reload();
    check(JSON.stringify(item.savedCoordinates) === '[702,202]', 'fallback metadata did not persist');
    item.savedCoordinates = [102, 402];
    manager._iconLayoutKey = Layouts.layoutKey([external, laptop]);
    item = reload();
    check(JSON.stringify(item.savedCoordinates) === '[1102,202]', 'GVfs lost the external-monitor layout');
    manager._iconLayoutKey = Layouts.layoutKey([laptop]);
    item = reload();
    check(JSON.stringify(item.savedCoordinates) === '[102,402]', 'GVfs lost the laptop-only layout');
    const [, bytes] = file.load_contents(null);
    check(new TextDecoder().decode(bytes) === 'desktop contents remain unchanged\n', 'icon contents changed');
    print('DING native monitor layout persistence: PASS');
} finally {
    file.delete(null);
    Gio.File.new_for_path(directory).delete(null);
}
