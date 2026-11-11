import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export default class InfinityUpdater extends Extension {
    enable() {
        this._outsideClickId = global.stage.connect('captured-event',
            (_stage, event) => this._onCapturedEvent(event));
        this._mapId = global.window_manager.connect('map', (_wm, actor) => {
            if (this._isUpdater(actor.meta_window))
                this._showDrawer(actor.meta_window);
        });
        this._unminimizeId = global.window_manager.connect('unminimize', (_wm, actor) => {
            if (this._isUpdater(actor.meta_window))
                this._showDrawer(actor.meta_window);
        });
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => {
            for (const actor of global.get_window_actors()) {
                if (this._isUpdater(actor.meta_window))
                    this._placeDrawer(actor.meta_window);
            }
        });
        this._directory = GLib.build_filenamev([GLib.get_user_cache_dir(), 'infinityos']);
        this._stateFile = GLib.build_filenamev([this._directory, 'updates.json']);
        GLib.mkdir_with_parents(this._directory, 0o700);

        this._indicator = new PanelMenu.Button(0.0, 'Infinity OS Updates', true);
        this._indicator.accessible_role = Atk.Role.PUSH_BUTTON;
        const content = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        this._icon = new St.Icon({
            icon_name: 'infinity-update-available-symbolic',
            style_class: 'system-status-icon',
        });
        content.add_child(this._icon);
        this._badge = new St.Label({
            style_class: 'infinity-updater-badge',
            y_align: Clutter.ActorAlign.CENTER,
            visible: false,
        });
        content.add_child(this._badge);
        this._indicator.add_child(content);
        const open = () => {
            const window = global.get_window_actors().map(actor => actor.meta_window)
                .find(window => this._isUpdater(window));
            if (window) {
                this._toggleDrawer(window);
                return;
            }
            try {
                Gio.Subprocess.new(['/usr/bin/infinity-updater'], Gio.SubprocessFlags.NONE);
            } catch (error) {
                console.warn(`Could not open Infinity OS Updates: ${error}`);
            }
        };
        const click = new Clutter.ClickGesture();
        click.set_recognize_on_press(true);
        click.connect('recognize', open);
        this._indicator.add_action(click);
        this._indicator.connect('key-press-event', (_actor, event) => {
            const key = event.get_key_symbol();
            if (key === Clutter.KEY_Return || key === Clutter.KEY_space) {
                open();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
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
            Gio.Subprocess.new(['systemctl', '--user', 'start', 'infinity-updater.service'],
                Gio.SubprocessFlags.NONE);
        } catch (error) {
            console.warn(`Could not start Infinity OS update checks: ${error}`);
        }
    }

    _onCapturedEvent(event) {
        if (event.type() !== Clutter.EventType.BUTTON_PRESS &&
            event.type() !== Clutter.EventType.TOUCH_BEGIN)
            return Clutter.EVENT_PROPAGATE;
        const source = event.get_source();
        if (source && this._indicator?.contains(source))
            return Clutter.EVENT_PROPAGATE;
        const [x, y] = event.get_coords();
        for (const actor of global.get_window_actors()) {
            const window = actor.meta_window;
            if (!this._isUpdater(window) || window.minimized)
                continue;
            const rect = window.get_frame_rect();
            if (x < rect.x || x >= rect.x + rect.width ||
                y < rect.y || y >= rect.y + rect.height)
                this._hideDrawer(window);
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _isUpdater(window) {
        return window && !window.get_transient_for() &&
            (window.get_gtk_application_id() === 'org.infinityos.Updater' ||
             window.get_wm_class() === 'org.infinityos.Updater');
    }

    _placeDrawer(window) {
        const area = Main.layoutManager.getWorkAreaForMonitor(window.get_monitor());
        const width = Math.min(460, area.width);
        window.unmaximize(Meta.MaximizeFlags.BOTH);
        window.move_resize_frame(false, area.x + area.width - width, area.y,
            width, area.height);
    }

    _toggleDrawer(window) {
        if (window.minimized) {
            const actor = window.get_compositor_private();
            if (actor)
                Main.wm.skipNextEffect(actor);
            window.activate(global.get_current_time());
        } else if (this._closingWindows?.has(window)) {
            this._showDrawer(window);
        } else {
            this._hideDrawer(window);
        }
    }

    _showDrawer(window) {
        this._placeDrawer(window);
        const actor = window.get_compositor_private();
        if (!actor)
            return;
        const reversing = this._closingWindows?.delete(window);
        actor.remove_all_transitions();
        // Cancelling GNOME's restore effect leaves its intermediate actor position.
        const rect = window.get_buffer_rect();
        actor.x = rect.x;
        actor.y = rect.y;
        actor.scale_x = actor.scale_y = 1;
        actor.opacity = 255;
        if (!reversing)
            actor.translation_x = window.get_frame_rect().width;
        actor.ease({translation_x: 0, duration: St.Settings.get().enable_animations ? 280 : 0,
            mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
        window.activate(global.get_current_time());
    }

    _hideDrawer(window) {
        if (window.minimized || this._closingWindows?.has(window))
            return;
        const actor = window.get_compositor_private();
        if (!actor)
            return;
        this._closingWindows ??= new WeakMap();
        const closing = {};
        this._closingWindows.set(window, closing);
        actor.remove_all_transitions();
        actor.ease({translation_x: window.get_frame_rect().width, duration: St.Settings.get().enable_animations ? 220 : 0,
            mode: Clutter.AnimationMode.EASE_IN_CUBIC,
            onComplete: () => {
                if (this._closingWindows?.get(window) !== closing)
                    return;
                this._closingWindows.delete(window);
                Main.wm.skipNextEffect(actor);
                window.minimize();
                actor.translation_x = 0;
            }});
    }

    _refresh() {
        let count = 0;
        let release = null;
        try {
            const [ok, contents] = GLib.file_get_contents(this._stateFile);
            if (ok) {
                const state = JSON.parse(new TextDecoder().decode(contents));
                count = Array.isArray(state.updates) ? state.updates.length : 0;
                release = state.release?.version ?? null;
                // Offline RPM installation cannot update each user's cached results.
                try {
                    const resultPath = '/var/lib/infinityos/offline-update-result.json';
                    const [resultOk, resultBytes] = GLib.file_get_contents(resultPath);
                    const result = resultOk ? JSON.parse(new TextDecoder().decode(resultBytes)) : {};
                    const info = Gio.File.new_for_path(resultPath).query_info(
                        'time::modified', Gio.FileQueryInfoFlags.NONE, null);
                    if (result.status === 'success' &&
                        Date.parse(state.checked_at) < info.get_attribute_uint64('time::modified') * 1000) {
                        count = Array.isArray(state.updates)
                            ? state.updates.filter(update => update.kind !== 'RPM').length : 0;
                        release = null;
                    }
                } catch (_error) {
                    // Without a successful result, keep pending updates visible.
                }
            }
        } catch (_error) {
            // No completed update check yet.
        }
        const total = count + (release ? 1 : 0);
        this._badge.text = total > 99 ? '99+' : String(total);
        this._badge.visible = total > 0;
        this._indicator.visible = total > 0;
        this._indicator.accessible_name = release
            ? `Infinity OS ${release} is available`
            : count > 0 ? `${count} Infinity OS updates available`
                : 'Infinity OS Updates, no updates available';
        if (release && this._notifiedVersion !== release) {
            this._notifiedVersion = release;
            Main.notify(`Infinity OS ${release} is available`,
                'Open Infinity OS Updates to install current packages, then upgrade the release.');
        }
    }

    disable() {
        this._closingWindows = null;
        global.stage.disconnect(this._outsideClickId);
        global.window_manager.disconnect(this._mapId);
        global.window_manager.disconnect(this._unminimizeId);
        Main.layoutManager.disconnect(this._monitorsId);
        for (const actor of global.get_window_actors()) {
            if (this._isUpdater(actor.meta_window)) {
                actor.remove_all_transitions();
                actor.translation_x = 0;
            }
        }
        if (this._fallbackId)
            GLib.Source.remove(this._fallbackId);
        this._monitor.disconnect(this._monitorId);
        this._monitor.cancel();
        this._indicator.destroy();
        this._indicator = null;
        this._icon = null;
        this._badge = null;
        this._monitor = null;
    }
}
