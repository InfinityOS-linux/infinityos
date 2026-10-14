import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export default class InfinityUpdater extends Extension {
    enable() {
        this._directory = GLib.build_filenamev([GLib.get_user_cache_dir(), 'infinityos']);
        this._stateFile = GLib.build_filenamev([this._directory, 'updates.json']);
        GLib.mkdir_with_parents(this._directory, 0o700);

        this._indicator = new PanelMenu.Button(0.0, 'Infinity OS Updates', true);
        this._indicator.add_child(new St.Icon({
            icon_name: 'infinity-update-available-symbolic',
            style_class: 'system-status-icon',
        }));
        const click = new Clutter.ClickGesture();
        click.set_recognize_on_press(true);
        click.connect('recognize', () => {
            Gio.Subprocess.new(['/usr/bin/infinity-updater'], Gio.SubprocessFlags.NONE);
        });
        this._indicator.add_action(click);
        Main.panel.addToStatusArea('infinity-updater', this._indicator);

        const directory = Gio.File.new_for_path(this._directory);
        this._monitor = directory.monitor_directory(Gio.FileMonitorFlags.NONE, null);
        this._monitorId = this._monitor.connect('changed', () => this._refresh());
        this._refresh();
        this._fallbackId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 900, () => {
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
        try {
            Gio.Subprocess.new(['systemctl', '--user', 'start', 'infinity-updater.timer'],
                Gio.SubprocessFlags.NONE);
        } catch (error) {
            console.warn(`Could not start Infinity OS updater timer: ${error}`);
        }
    }

    _refresh() {
        let count = 0;
        try {
            const [ok, contents] = GLib.file_get_contents(this._stateFile);
            if (ok)
                count = JSON.parse(new TextDecoder().decode(contents)).updates.length;
        } catch (_error) {
            // No completed update check yet.
        }
        this._indicator.visible = count > 0;
        this._indicator.accessible_name = `${count} Infinity OS updates available`;
    }

    disable() {
        if (this._fallbackId)
            GLib.Source.remove(this._fallbackId);
        this._monitor.disconnect(this._monitorId);
        this._monitor.cancel();
        this._indicator.destroy();
        this._indicator = null;
        this._monitor = null;
    }
}
