import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as Workspace from 'resource:///org/gnome/shell/ui/workspace.js';

const APP_ID = 'com.infinityos.GhosTTY';
const KEYBINDING = 'infinity-terminal-toggle';
export default class InfinityTerminal extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._settings.set_boolean('pinned', false);
        this._window = null;
        this._pendingShow = false;
        this._sourceId = 0;
        this._pendingWindows = new Map();
        this._indicator = new PanelMenu.Button(0.0, 'Show or hide InfinityTerminal', true);
        this._indicator.accessible_role = Atk.Role.PUSH_BUTTON;
        this._icon = new St.Icon({
            icon_name: 'utilities-terminal-symbolic',
            style_class: 'system-status-icon',
            opacity: 112,
        });
        this._indicator.add_child(this._icon);
        const click = new Clutter.ClickGesture();
        click.set_recognize_on_press(true);
        click.connect('recognize', () => this._toggle());
        this._indicator.add_action(click);
        Main.panel.addToStatusArea('ghostty', this._indicator);
        this._hideRequestId = this._settings.connect('changed::hide-request', () => {
            const window = this._findWindow();
            if (window && !window.minimized)
                this._hide(window);
        });
        const getRunning = Shell.AppSystem.prototype.get_running;
        this._getRunning = getRunning;
        this._filteredRunning = function () {
            return getRunning.call(this).filter(app =>
                !app.get_windows().some(window =>
                    window.get_gtk_application_id?.() === APP_ID ||
                    window.get_wm_class?.() === APP_ID));
        };
        Shell.AppSystem.prototype.get_running = this._filteredRunning;
        const isOverviewWindow = Workspace.Workspace.prototype._isOverviewWindow;
        this._isOverviewWindow = isOverviewWindow;
        this._filteredOverviewWindow = function (window) {
            return isOverviewWindow.call(this, window) &&
                !(window.minimized && (window.get_gtk_application_id?.() === APP_ID ||
                    window.get_wm_class?.() === APP_ID));
        };
        Workspace.Workspace.prototype._isOverviewWindow = this._filteredOverviewWindow;
        Main.wm.addKeybinding(KEYBINDING, this._settings,
            Meta.KeyBindingFlags.NONE, Shell.ActionMode.ALL, () => this._toggle());
        this._outsideClickId = global.stage.connect('captured-event', (_stage, event) => {
            const source = event.get_source();
            if (this._settings.get_boolean('pinned') || event.type() !== Clutter.EventType.BUTTON_PRESS ||
                (source && this._indicator.contains(source)))
                return Clutter.EVENT_PROPAGATE;

            const window = this._findWindow();
            if (!window || window.minimized)
                return Clutter.EVENT_PROPAGATE;

            const [x, y] = event.get_coords();
            const rect = window.get_frame_rect();
            if (x < rect.x || x >= rect.x + rect.width ||
                y < rect.y || y >= rect.y + rect.height)
                this._hide(window);

            return Clutter.EVENT_PROPAGATE;
        });
        this._focusId = global.display.connect('notify::focus-window', () => {
            const window = this._findWindow();
            if (!this._settings.get_boolean('pinned') && window && !window.minimized &&
                global.display.focus_window !== window)
                this._hide(window);
        });
        this._windowCreatedId = global.display.connect('window-created', (_display, window) => {
            const clear = () => {
                for (const id of this._pendingWindows.get(window) ?? [])
                    window.disconnect(id);
                this._pendingWindows.delete(window);
            };
            const check = () => {
                if (!this._isGhosTTY(window))
                    return;
                clear();
                this._track(window, true);
            };
            // Wayland sets the application ID after window-created.
            this._pendingWindows.set(window, [
                window.connect('notify::gtk-application-id', check),
                window.connect('notify::wm-class', check),
                window.connect('unmanaged', clear),
            ]);
            check();
        });

        const existing = this._findWindow();
        if (existing)
            this._track(existing, true);
        else
            this._spawn();
    }

    disable() {
        if (Workspace.Workspace.prototype._isOverviewWindow === this._filteredOverviewWindow)
            Workspace.Workspace.prototype._isOverviewWindow = this._isOverviewWindow;
        if (Shell.AppSystem.prototype.get_running === this._filteredRunning)
            Shell.AppSystem.prototype.get_running = this._getRunning;
        Main.wm.removeKeybinding(KEYBINDING);
        this._settings.disconnect(this._hideRequestId);
        global.stage.disconnect(this._outsideClickId);
        global.display.disconnect(this._focusId);
        global.display.disconnect(this._windowCreatedId);
        for (const [window, ids] of this._pendingWindows) {
            for (const id of ids)
                window.disconnect(id);
        }
        this._pendingWindows.clear();
        if (this._unmanagedId && this._window)
            this._window.disconnect(this._unmanagedId);
        if (this._minimizedId && this._window)
            this._window.disconnect(this._minimizedId);
        if (this._window) {
            const actor = this._window.get_compositor_private();
            if (actor)
                actor.opacity = 255;
        }
        if (this._sourceId)
            GLib.Source.remove(this._sourceId);
        this._indicator.destroy();
        this._indicator = null;
        this._icon = null;
        this._window = null;
        this._settings = null;
    }

    _isGhosTTY(window) {
        return window.get_gtk_application_id?.() === APP_ID ||
            window.get_wm_class?.() === APP_ID;
    }

    _findWindow() {
        if (this._window)
            return this._window;
        return global.get_window_actors()
            .map(actor => actor.meta_window)
            .find(window => this._isGhosTTY(window)) ?? null;
    }

    _spawn() {
        try {
            Gio.Subprocess.new(['systemctl', '--user', 'start', 'ghostty.service'], Gio.SubprocessFlags.NONE);
        } catch (error) {
            console.error(`Could not start InfinityTerminal: ${error}`);
        }
    }

    _track(window, fresh) {
        if (this._unmanagedId && this._window)
            this._window.disconnect(this._unmanagedId);
        if (this._minimizedId && this._window)
            this._window.disconnect(this._minimizedId);
        this._window = window;
        if (fresh && !this._pendingShow) {
            const actor = window.get_compositor_private();
            if (actor) {
                actor.opacity = 0;
                Main.wm.skipNextEffect(actor);
            }
            window.minimize();
        }
        this._icon.opacity = window.minimized ? 112 : 255;
        this._minimizedId = window.connect('notify::minimized', () => {
            this._icon.opacity = window.minimized ? 112 : 255;
            Main.overview._overview.controls._workspacesDisplay._updateWorkspacesViews();
        });
        this._unmanagedId = window.connect('unmanaged', () => {
            this._window = null;
            this._icon.opacity = 112;
            this._unmanagedId = 0;
            this._minimizedId = 0;
        });
        this._sourceId = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._sourceId = 0;
            this._place(window);
            if (this._pendingShow) {
                this._pendingShow = false;
                this._reveal(window);
            } else if (fresh) {
                const actor = window.get_compositor_private();
                if (actor)
                    Main.wm.skipNextEffect(actor);
                window.minimize();
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    _place(window) {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor)
            return;
        const y = monitor.y + Main.panel.height;
        window.move_resize_frame(true, monitor.x, y,
            monitor.width, Math.round(monitor.height / 2));
        window.move_frame(true, monitor.x, y);
    }

    _toggle() {
        const window = this._findWindow();
        if (!window) {
            this._pendingShow = true;
            this._spawn();
        } else if (window.minimized) {
            this._reveal(window);
        } else {
            this._hide(window);
        }
    }

    _reveal(window) {
        const actor = window.get_compositor_private();
        if (actor)
            actor.opacity = 255;
        if (actor) {
            actor.remove_all_transitions();
            actor.translation_y = -window.get_frame_rect().height;
            Main.wm.skipNextEffect(actor);
        }
        window.unminimize();
        this._place(window);
        window.activate(global.get_current_time());
        this._sourceId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 25, () => {
            this._sourceId = 0;
            const actor = window.get_compositor_private();
            if (actor) {
                actor.ease({translation_y: 0, duration: 150,
                    mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    _hide(window) {
        const actor = window.get_compositor_private();
        if (!actor) {
            window.minimize();
            return;
        }
        actor.remove_all_transitions();
        actor.ease({
            translation_y: -window.get_frame_rect().height,
            duration: 120,
            mode: Clutter.AnimationMode.EASE_IN_CUBIC,
            onComplete: () => {
                Main.wm.skipNextEffect(actor);
                window.minimize();
                actor.translation_y = 0;
            },
        });
    }
}
