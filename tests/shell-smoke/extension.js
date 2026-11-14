import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {HardwareMonitor} from '../ghostty@infinityos.org/hardware-monitor.js';
import {widgetChoices} from '../ghostty@infinityos.org/monitor-widgets.js';
import NowPlay from '../nowplay@LalaloyXyz/extension.js';
import Raccoon from '../raccoonlauncher@shimafallah.github.io/extension.js';
import Updater from '../infinity-updater@infinityos.org/extension.js';
import {opticalMetrics} from '../dash2dock-animated@infinityos.org/optical-icons.mjs';

function check(ok, message) { if (!ok) throw new Error(message); }

export default class Smoke extends Extension {
    enable() {
        this._objects = [];
        GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 3, () => {
            this.run().catch(error => { console.error(`INFINITY_SMOKE_FAIL ${error.message} ${error.stack}`); });
            return GLib.SOURCE_REMOVE;
        });
    }

    async run() {
        const root = this.dir.get_parent();
        const metadata = uuid => {
            const dir = root.get_child(uuid);
            const [, bytes] = dir.get_child('metadata.json').load_contents(null);
            return {...JSON.parse(new TextDecoder().decode(bytes)), dir, path: dir.get_path()};
        };
        const theme = St.ThemeContext.get_for_stage(global.stage).get_theme();
        for (const uuid of ['ghostty@infinityos.org', 'nowplay@LalaloyXyz', 'raccoonlauncher@shimafallah.github.io', 'infinity-updater@infinityos.org']) {
            const file = root.get_child(uuid).get_child('stylesheet.css');
            if (file.query_exists(null)) theme.load_stylesheet(file);
        }
        const iconTheme = St.IconTheme.new();
        let iconLoaded = false;
        opticalMetrics(iconTheme, null, 'folder', () => { iconLoaded = true; });
        const terminal = metadata('ghostty@infinityos.org');
        const source = Gio.SettingsSchemaSource.new_from_directory(`${terminal.path}/schemas`, Gio.SettingsSchemaSource.get_default(), false);
        const settings = new Gio.Settings({settings_schema: source.lookup('org.infinityos.GhosTTY', true)});
        settings.set_strv('monitor-metrics', ['memory:used', ...widgetChoices.map(choice => choice.id)]);
        const monitor = new HardwareMonitor({path: terminal.path, getSettings: () => settings, openPreferences() {}}, () => {});
        this._objects.push({disable: () => monitor.destroy()});
        monitor.sync({x: 0, y: 150, width: 1280}, true);
        const wait = () => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 750, () => { resolve(); return GLib.SOURCE_REMOVE; }));
        await wait();
        check(iconLoaded, 'native dock icon measurement failed');
        check(monitor._cells.length === 8, 'sensor/widget construction');
        for (const cell of monitor._cells.filter(cell => cell.actor.visible))
            check(cell.label.height > 0, `caption clipped: ${cell.id}`);
        const visibleCells = monitor._cells.filter(cell => cell.actor.visible);
        const [left] = visibleCells[0].actor.get_transformed_position();
        const last = visibleCells.at(-1).actor;
        const [lastX] = last.get_transformed_position();
        const [lastWidth] = last.get_transformed_size();
        check(Math.abs((left + lastX + lastWidth) / 2 - 640) < 2, 'monitor row is not centered');
        monitor._openMenu(-1); check(monitor.menuOpen, 'monitor menu failed'); monitor._menu.close();
        monitor._widgets.stopwatch.toggle(); monitor._widgets.toggleTimer('widget:timer');
        const iface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        iface.set_string('color-scheme', 'prefer-light'); await wait();
        check(monitor.actor.has_style_class_name('light'), 'light mode failed');
        iface.set_string('color-scheme', 'prefer-dark'); await wait();
        check(!monitor.actor.has_style_class_name('light'), 'dark mode failed');
        const target = monitor._cells[0].actor._delegate;
        target.acceptDrop({monitor, id: 'widget:clock'}, null, 0);
        await wait(); check(settings.get_strv('monitor-metrics')[0] === 'widget:clock', 'drag reorder failed');
        monitor.hide(); check(!monitor._widgetTimer && !monitor._timer, 'hidden strip still polling');

        const raccoon = new Raccoon(metadata('raccoonlauncher@shimafallah.github.io'));
        this._objects.push(raccoon); raccoon.enable();
        raccoon._overlay.open(); check(raccoon._overlay._isOpen, 'Raccoon did not open');
        raccoon._overlay._entry.set_text('2+3'); await wait();
        check(raccoon._overlay._results.some(result => result.name === '5'), 'Raccoon calculator failed');
        raccoon._overlay.close(); check(!raccoon._overlay._grab, 'Raccoon kept modal grab');

        const {default: Blur} = await import('gi://Blur');
        check(Blur.BlurEffect.list_properties().some(property => property.name === 'corner-radius'), 'native rounded blur unavailable');
        const nowplay = new NowPlay(metadata('nowplay@LalaloyXyz'));
        this._objects.push(nowplay); nowplay.enable();
        check(!nowplay._ui._createStatusPill.toString().includes('animateUp'), 'loaded obsolete NowPlay equalizer');
        console.log('INFINITY_NOWPLAY_TIMER_SOURCE_CONFIRMED');
        const player = {busName: 'org.mpris.MediaPlayer2.smoke', title: 'InfinityOS test', artist: 'CI',
            status: 'Playing', position: 30, trackLen: 180, canSeek: true, trackId: '/test', artUrl: '', appIconName: 'audio-x-generic'};
        nowplay._ui.showPopup(player, [player]); await wait();
        check(nowplay._ui.popupVisible, 'NowPlay did not open');
        nowplay._ui.destroyPopup();
        const updater = new Updater(metadata('infinity-updater@infinityos.org'));
        this._objects.push(updater); updater.enable();
        check(Main.panel.statusArea['infinity-updater'], 'updater indicator failed');
        const client = Gio.Subprocess.new(['python3', '-c', `
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
app = Gtk.Application(application_id='org.infinityos.Updater')
def activate(app):
    window = Gtk.ApplicationWindow(application=app, title='InfinityUpdater smoke')
    window.set_decorated(False)
    window.set_default_size(160, 100)
    window.set_child(Gtk.Label(label='Updater'))
    window.present()
app.connect('activate', activate)
app.run(None)
`], Gio.SubprocessFlags.NONE);
        this._objects.push({disable: () => client.force_exit()});
        await wait(); await wait(); await wait();
        const drawer = global.get_window_actors().find(actor => updater._isUpdater(actor.meta_window));
        check(drawer, 'updater client did not map');
        const frame = drawer.meta_window.get_frame_rect();
        const area = Main.layoutManager.getWorkAreaForMonitor(drawer.meta_window.get_monitor());
        check(frame.width === Math.min(460, area.width) && frame.height === area.height, 'updater remained at initial size');
        check(drawer.opacity === 255 && Math.abs(drawer.translation_x) < 1, 'updater did not finish its spring slide');
        this.disable();
        console.log('INFINITY_SMOKE_PASS');
    }

    disable() {
        for (const object of this._objects.reverse()) object.disable();
        this._objects = [];
    }
}
