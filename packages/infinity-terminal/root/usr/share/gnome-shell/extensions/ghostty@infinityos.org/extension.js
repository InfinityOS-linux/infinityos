import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as Workspace from 'resource:///org/gnome/shell/ui/workspace.js';
import {clampTerminalHeight, isFullHeight} from './resize.mjs';

const APP_ID = 'com.infinityos.GhosTTY';
const KEYBINDING = 'infinity-terminal-toggle';
const SWIPE_DISTANCE = 8;
const RESIZE_EDGE = 10;
export default class InfinityTerminal extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._settings.set_boolean('pinned', false);
        this._window = null;
        this._pendingShow = false;
        this._sourceId = 0;
        this._placementId = 0;
        this._geometryIds = [];
        this._pendingWindows = new Map();
        this._resize = null;
        this._resizeCursor = false;
        this._fullHeight = false;
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
        Main.panel.addToStatusArea('ghostty', this._indicator, 2, 'left');
        this._hideRequestId = this._settings.connect('changed::hide-request', () => {
            const window = this._findWindow();
            if (window && !window.minimized)
                this._hide(window);
        });
        this._toggleRequestId = this._settings.connect('changed::toggle-request', () => this._toggle());
        this._showRequestId = this._settings.connect('changed::show-request', () => this._showTerminal());
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
        this._touchpadSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.peripherals.touchpad'});
        this._gesture = null;
        this._overviewHiddenId = 0;
        this._gestureEventId = global.stage.connect('captured-event',
            (_stage, event) => this._handleGesture(event));
        this._resizeEventId = global.stage.connect('captured-event',
            (_stage, event) => this._handleResize(event));
        this._workspaceSwipe = Main.wm._workspaceAnimation?._swipeTracker;
        this._workspaceTouchpad = this._workspaceSwipe?._touchpadGesture;
        this._workspaceUpdateId = this._workspaceTouchpad
            ? GObject.signal_handler_find(this._workspaceTouchpad, {signalId: 'update'})
            : 0;
        if (this._workspaceUpdateId) {
            this._workspaceTouchpad.block_signal_handler(this._workspaceUpdateId);
            this._reversedWorkspaceUpdateId = this._workspaceTouchpad.connect('update',
                (gesture, time, delta, distance) => {
                    // Keep natural scrolling in apps, but map a physical right swipe
                    // to the next workspace independently of that preference.
                    const direction = this._touchpadSettings.get_boolean('natural-scroll') ? -1 : 1;
                    this._workspaceSwipe._updateTouchpadGesture(gesture, time,
                        delta * direction, distance);
                });
        }
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
        else if (GLib.get_user_name() !== 'liveuser')
            this._spawn();
    }

    disable() {
        if (Workspace.Workspace.prototype._isOverviewWindow === this._filteredOverviewWindow)
            Workspace.Workspace.prototype._isOverviewWindow = this._isOverviewWindow;
        if (Shell.AppSystem.prototype.get_running === this._filteredRunning)
            Shell.AppSystem.prototype.get_running = this._getRunning;
        Main.wm.removeKeybinding(KEYBINDING);
        if (this._overviewHiddenId)
            Main.overview.disconnect(this._overviewHiddenId);
        this._overviewHiddenId = 0;
        global.stage.disconnect(this._gestureEventId);
        global.stage.disconnect(this._resizeEventId);
        this._resize = null;
        this._setResizeCursor(false);
        if (this._reversedWorkspaceUpdateId)
            this._workspaceTouchpad.disconnect(this._reversedWorkspaceUpdateId);
        if (this._workspaceUpdateId)
            this._workspaceTouchpad.unblock_signal_handler(this._workspaceUpdateId);
        this._workspaceSwipe = null;
        this._workspaceTouchpad = null;
        this._touchpadSettings = null;
        this._gesture = null;
        this._settings.disconnect(this._hideRequestId);
        this._settings.disconnect(this._toggleRequestId);
        this._settings.disconnect(this._showRequestId);
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
        for (const id of this._geometryIds)
            this._window?.disconnect(id);
        this._geometryIds = [];
        if (this._window) {
            const actor = this._window.get_compositor_private();
            if (actor)
                actor.opacity = 255;
        }
        if (this._sourceId)
            GLib.Source.remove(this._sourceId);
        if (this._placementId)
            GLib.Source.remove(this._placementId);
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

    _setResizeCursor(active) {
        if (this._resizeCursor === active)
            return;
        this._resizeCursor = active;
        global.display.set_cursor(active
            ? (Meta.Cursor.SOUTH_RESIZE ?? Meta.Cursor.S_RESIZE)
            : Meta.Cursor.DEFAULT);
    }

    _handleResize(event) {
        const type = event.type();
        if (this._resize) {
            if (type === Clutter.EventType.MOTION) {
                this._resizeTo(event.get_coords()[1]);
                return Clutter.EVENT_STOP;
            }
            if (type === Clutter.EventType.BUTTON_RELEASE && event.get_button() === 1) {
                const monitor = Main.layoutManager.primaryMonitor;
                if (monitor) {
                    const height = this._fullHeight
                        ? monitor.height - Main.panel.height
                        : this._resize.window.get_frame_rect().height;
                    this._settings.set_double('height-ratio', height / monitor.height);
                }
                this._resize = null;
                this._setResizeCursor(false);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        }

        if (type !== Clutter.EventType.MOTION && type !== Clutter.EventType.BUTTON_PRESS)
            return Clutter.EVENT_PROPAGATE;
        const window = this._findWindow();
        const [x, y] = event.get_coords();
        const rect = window && !window.minimized ? window.get_frame_rect() : null;
        const edge = rect && x >= rect.x && x < rect.x + rect.width &&
            y >= rect.y + rect.height - RESIZE_EDGE && y < rect.y + rect.height;
        this._setResizeCursor(!!edge);
        if (!edge || type !== Clutter.EventType.BUTTON_PRESS || event.get_button() !== 1)
            return Clutter.EVENT_PROPAGATE;
        this._resize = {window, offset: rect.y + rect.height - y};
        return Clutter.EVENT_STOP;
    }

    _resizeTo(pointerY) {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor || !this._resize)
            return;
        const top = monitor.y + Main.panel.height;
        const height = clampTerminalHeight(monitor.height, Main.panel.height,
            pointerY + this._resize.offset - top);
        const full = isFullHeight(monitor.height, Main.panel.height, height);
        if (full) {
            if (!this._fullHeight)
                this._resize.window.maximize(Meta.MaximizeFlags.BOTH);
        } else {
            if (this._fullHeight)
                this._resize.window.unmaximize(Meta.MaximizeFlags.BOTH);
            this._resize.window.move_resize_frame(true, monitor.x, top, monitor.width, height);
            this._resize.window.move_frame(true, monitor.x, top);
        }
        this._fullHeight = full;
    }

    _handleGesture(event) {
        if (event.type() !== Clutter.EventType.TOUCHPAD_SWIPE ||
            event.get_touchpad_gesture_finger_count() !== 3 ||
            !(Main.actionMode & (Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW)))
            return Clutter.EVENT_PROPAGATE;

        const phase = event.get_gesture_phase();
        if (phase === Clutter.TouchpadGesturePhase.BEGIN) {
            this._gesture = {dx: 0, dy: 0, direction: null};
            return Clutter.EVENT_PROPAGATE;
        }
        if (!this._gesture)
            return Clutter.EVENT_PROPAGATE;

        if (phase === Clutter.TouchpadGesturePhase.UPDATE &&
            this._gesture.direction === null) {
            const [dx, dy] = event.get_gesture_motion_delta_unaccelerated();
            this._gesture.dx += dx;
            this._gesture.dy += dy;
            const {dx: totalX, dy: totalY} = this._gesture;
            if (Math.hypot(totalX, totalY) >= SWIPE_DISTANCE)
                this._gesture.direction = totalY > 0 &&
                    Math.abs(totalY) > Math.abs(totalX) * 1.25 ? 'down' : 'other';
        }

        const handled = this._gesture.direction === 'down';
        if (phase === Clutter.TouchpadGesturePhase.END ||
            phase === Clutter.TouchpadGesturePhase.CANCEL) {
            this._gesture = null;
            if (handled && phase === Clutter.TouchpadGesturePhase.END)
                this._finishDownGesture();
        }
        return handled ? Clutter.EVENT_STOP : Clutter.EVENT_PROPAGATE;
    }

    _finishDownGesture() {
        const controls = Main.overview._overview.controls;
        const appGridOpen = Main.overview.visible &&
            (controls.dash?.showAppsButton?.checked ?? controls._stateAdjustment.value > 1.5);
        if (appGridOpen) {
            controls.dash.showAppsButton.checked = false;
        } else if (Main.overview.visible) {
            if (!this._overviewHiddenId)
                this._overviewHiddenId = Main.overview.connect('hidden', () => {
                    Main.overview.disconnect(this._overviewHiddenId);
                    this._overviewHiddenId = 0;
                    this._showTerminal();
                });
            Main.overview.hide();
        } else {
            this._showTerminal();
        }
    }

    _showTerminal() {
        const window = this._findWindow();
        if (!window || window.minimized)
            this._toggle();
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
        for (const id of this._geometryIds)
            this._window?.disconnect(id);
        this._window = window;
        this._geometryIds = [
            window.connect('position-changed', () => this._enforcePlacement(window)),
            window.connect('size-changed', () => this._enforcePlacement(window)),
        ];
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
            this._resize = null;
            this._setResizeCursor(false);
            this._icon.opacity = 112;
            this._unmanagedId = 0;
            this._minimizedId = 0;
            this._geometryIds = [];
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

    _enforcePlacement(window) {
        if (window !== this._window || window.minimized || this._resize || this._placementId)
            return;
        this._placementId = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._placementId = 0;
            if (window !== this._window || window.minimized || this._resize)
                return GLib.SOURCE_REMOVE;
            const monitor = Main.layoutManager.primaryMonitor;
            if (!monitor)
                return GLib.SOURCE_REMOVE;
            const rect = window.get_frame_rect();
            const height = clampTerminalHeight(monitor.height, Main.panel.height,
                monitor.height * this._settings.get_double('height-ratio'));
            const full = isFullHeight(monitor.height, Main.panel.height, height);
            if ((!full || window.get_maximized() !== Meta.MaximizeFlags.BOTH) &&
                (rect.x !== monitor.x || rect.y !== monitor.y + Main.panel.height ||
                 rect.width !== monitor.width || rect.height !== height))
                this._place(window);
            return GLib.SOURCE_REMOVE;
        });
    }

    _place(window) {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor)
            return;
        const y = monitor.y + Main.panel.height;
        const height = clampTerminalHeight(monitor.height, Main.panel.height,
            monitor.height * this._settings.get_double('height-ratio'));
        window.unmaximize(Meta.MaximizeFlags.BOTH);
        window.move_resize_frame(true, monitor.x, y, monitor.width, height);
        window.move_frame(true, monitor.x, y);
        this._fullHeight = isFullHeight(monitor.height, Main.panel.height, height);
        if (this._fullHeight)
            window.maximize(Meta.MaximizeFlags.BOTH);
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
