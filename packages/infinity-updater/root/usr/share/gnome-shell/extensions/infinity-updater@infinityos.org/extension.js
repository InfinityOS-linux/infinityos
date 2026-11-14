import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';

import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import * as NotificationDaemon from 'resource:///org/gnome/shell/ui/notificationDaemon.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export default class InfinityUpdater extends Extension {
    enable() {
        this._configureUpdateNotifications();
        // Cover only the panel backdrop while the drawer is open. The same
        // opaque surface in GTK avoids a seam against the wallpaper tint.
        this._panelSurface = new St.Widget({reactive: false, visible: false});
        this._panelSurface.add_constraint(new Clutter.BindConstraint({
            source: Main.panel, coordinate: Clutter.BindCoordinate.ALL}));
        Main.panel.add_child(this._panelSurface);
        Main.panel.set_child_below_sibling(this._panelSurface, Main.panel._leftBox);
        this._colorSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        const syncSurface = () => this._panelSurface.set_style(
            `background-color: ${this._colorSettings.get_string('color-scheme') === 'prefer-dark' ? '#0d0b14' : '#faf7ff'};`);
        this._colorId = this._colorSettings.connect('changed::color-scheme', syncSurface);
        syncSurface();
        this._destroyId = global.window_manager.connect('destroy', (_wm, actor) => {
            if (this._isUpdater(actor.meta_window)) this._panelSurface.hide();
        });
        this._focusId = global.display.connect('notify::focus-window',
            () => this._onFocusChanged());
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

        this._indicator = new PanelMenu.Button(0.0, 'InfinityUpdater', true);
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
                console.warn(`Could not open InfinityUpdater: ${error}`);
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

    _simplifyInstalledNotification(notification) {
        if (notification.source?._appId !== 'org.gnome.Software')
            return false;
        const data = notification.serialize().deepUnpack();
        const completed = notification.id === 'updates-installed' ||
            (notification.id === 'offline-updates' &&
             data['default-action']?.unpack() === 'app.set-mode' &&
             data['default-action-target']?.unpack() === 'updated');
        if (!completed)
            return false;
        const polish = GLib.get_language_names()[0].split(/[_.@-]/)[0] === 'pl';
        notification.set({
            title: polish ? 'Aktualizacje zostały zainstalowane.' : 'Updates installed.',
            body: '',
        });
        notification.clearActions();
        if (!this._simplifiedNotifications.has(notification)) {
            this._simplifiedNotifications.add(notification);
            this._notificationOverrides.overrideMethod(notification, 'activate', () => function () {
                return MessageTray.Notification.prototype.activate.call(this);
            });
        }
        return true;
    }

    _configureUpdateNotifications() {
        this._notificationOverrides = new InjectionManager();
        this._simplifiedNotifications = new WeakSet();
        const extension = this;
        this._notificationOverrides.overrideMethod(
            NotificationDaemon.GtkNotificationDaemonAppSource.prototype, 'addNotification',
            original => function (notification) {
                extension._simplifyInstalledNotification(notification);
                return original.call(this, notification);
            });
        for (const source of Main.messageTray.getSources()) {
            if (source._appId === 'org.gnome.Software') {
                for (const notification of source.notifications)
                    this._simplifyInstalledNotification(notification);
            }
        }
    }

    _onCapturedEvent(event) {
        if (event.type() !== Clutter.EventType.BUTTON_PRESS &&
            event.type() !== Clutter.EventType.TOUCH_BEGIN)
            return Clutter.EVENT_PROPAGATE;
        const source = global.stage.get_event_actor(event);
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

    _onFocusChanged() {
        const focused = global.display.focus_window;
        // Wayland client clicks can bypass stage events; shell clicks use the handler above.
        if (!focused)
            return;
        for (const actor of global.get_window_actors()) {
            const window = actor.meta_window;
            if (!this._isUpdater(window) || window.minimized)
                continue;
            let owner = focused;
            while (owner && owner !== window)
                owner = owner.get_transient_for();
            if (!owner)
                this._hideDrawer(window);
        }
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
            this._cancelClose(window);
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

    _cancelOpening(window) {
        const opening = this._openingWindows?.get(window);
        if (!opening) return;
        this._openingWindows.delete(window);
        global.compositor.get_laters().remove(opening.id);
    }

    _showDrawer(window) {
        this._cancelClose(window);
        this._cancelOpening(window);
        const actor = window.get_compositor_private();
        if (!actor) return;
        this._panelSurface?.show();
        const reversing = this._closingWindows?.delete(window);
        Main.wm.skipNextEffect(actor);
        actor.remove_all_transitions();
        if (!reversing) actor.opacity = 0;
        this._placeDrawer(window);
        this._openingWindows ??= new Map();
        const opening = {};
        this._openingWindows.set(window, opening);
        // Let placement and GNOME's map/restore handlers finish before our slide.
        opening.id = global.compositor.get_laters().add(Meta.LaterType.BEFORE_REDRAW, () => {
            if (this._openingWindows?.get(window) !== opening) return false;
            this._openingWindows.delete(window);
            if (window.get_compositor_private() !== actor) return false;
            actor.remove_all_transitions();
            const rect = window.get_buffer_rect();
            actor.x = rect.x;
            actor.y = rect.y;
            actor.scale_x = actor.scale_y = 1;
            if (!reversing) actor.translation_x = window.get_frame_rect().width + 16;
            actor.opacity = 255;
            actor.ease({translation_x: 0, duration: St.Settings.get().enable_animations ? 420 : 0,
                mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
            return false;
        });
        window.activate(global.get_current_time());
    }

    _hideDrawer(window) {
        this._cancelOpening(window);
        if (window.minimized || this._closingWindows?.has(window))
            return;
        const actor = window.get_compositor_private();
        if (!actor)
            return;
        this._closingWindows ??= new WeakMap();
        const closing = {};
        this._closingWindows.set(window, closing);
        actor.remove_all_transitions();
        actor.ease({translation_x: window.get_frame_rect().width + 16, duration: St.Settings.get().enable_animations ? 280 : 0,
            mode: Clutter.AnimationMode.EASE_IN_CUBIC,
            onComplete: () => {
                if (this._closingWindows?.get(window) !== closing)
                    return;
                this._closingWindows.delete(window);
                Main.wm.skipNextEffect(actor);
                window.minimize();
                this._panelSurface?.hide();
                actor.translation_x = 0;
                this._scheduleClose(window);
            }});
    }

    _cancelClose(window) {
        const pending = this._closeTimers?.get(window);
        if (!pending)
            return;
        this._closeTimers.delete(window);
        GLib.Source.remove(pending.timer);
        window.disconnect(pending.unmanaged);
    }

    _scheduleClose(window) {
        this._cancelClose(window);
        this._closeTimers ??= new Map();
        const unmanaged = window.connect('unmanaged', () => this._cancelClose(window));
        const timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => {
            this._closeTimers.delete(window);
            window.disconnect(unmanaged);
            if (window.minimized)
                window.delete(global.get_current_time());
            return GLib.SOURCE_REMOVE;
        });
        this._closeTimers.set(window, {timer, unmanaged});
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
                : 'InfinityUpdater, no updates available';
        if (release && this._notifiedVersion !== release) {
            this._notifiedVersion = release;
            Main.notify(`Infinity OS ${release} is available`,
                'Open InfinityUpdater to install current packages, then upgrade the release.');
        }
    }

    disable() {
        global.window_manager.disconnect(this._destroyId);
        this._colorSettings.disconnect(this._colorId);
        this._colorSettings = null;
        this._panelSurface.destroy();
        this._panelSurface = null;
        for (const window of this._openingWindows?.keys() ?? []) {
            this._cancelOpening(window);
            const actor = window.get_compositor_private();
            if (actor) actor.opacity = 255;
        }
        this._notificationOverrides?.clear();
        this._notificationOverrides = null;
        for (const window of this._closeTimers?.keys() ?? [])
            this._cancelClose(window);
        this._closingWindows = null;
        global.display.disconnect(this._focusId);
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
