import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// A separate chrome actor avoids enlarging the panel's reserved work area.
export class TerminalPullHandle {
    constructor(terminal) {
        this.terminal = terminal;
        this.signals = [];
        this.drag = null;
        this.windowSignals = new Map();
        this.closedWindows = new WeakSet();
        this.panelLine = new St.Widget({reactive: false, style: 'background-color: rgba(184, 166, 217, 0.20);'});
        Main.layoutManager.addTopChrome(this.panelLine, {affectsStruts: false, trackFullscreen: true});
        this.actor = new St.DrawingArea({reactive: true, can_focus: true, track_hover: true,
            accessible_name: 'Show, hide or drag InfinityTerminal',
            accessible_role: Atk.Role.PUSH_BUTTON});
        this.actor.connect('repaint', () => this.paint());
        this.actor.connect('notify::hover', () => this.actor.queue_repaint());
        Main.layoutManager.addTopChrome(this.actor, {affectsStruts: false, trackFullscreen: true});
        const connect = (object, signal, callback) => {
            this.signals.push([object, object.connect(signal, callback)]);
        };
        const sync = () => this.sync();
        this.interfaceSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        connect(this.interfaceSettings, 'changed::color-scheme', sync);
        connect(Main.panel, 'notify::allocation', sync);
        connect(Main.panel, 'style-changed', () => { this.actor.queue_repaint(); this.sync(); });
        connect(Main.panel.statusArea.dateMenu, 'notify::allocation', sync);
        connect(Main.layoutManager, 'startup-complete', sync);
        connect(Main.layoutManager, 'monitors-changed', () => { this.finish(true); this.sync(); });
        connect(global.display, 'restacked', sync);
        connect(global.display, 'window-created', (_display, window) => { this.trackWindow(window); this.sync(); });
        if (global.workspace_manager) connect(global.workspace_manager, 'active-workspace-changed', sync);
        connect(global.display, 'in-fullscreen-changed', () => { this.finish(true); this.sync(); });
        connect(Main.overview, 'showing', () => { this.finish(true); this.sync(); });
        connect(Main.overview, 'hidden', sync);
        connect(Main.sessionMode, 'updated', () => { this.finish(true); this.sync(); });
        connect(global.stage, 'captured-event', (_stage, event) => this.event(event));
        this.clockActor = Main.panel.statusArea.dateMenu;
        this.clockTranslation = this.clockActor.translation_x ?? 0;
        const label = this.clockActor._clockDisplay;
        if (label) connect(label, 'notify::allocation', sync);
        this.verifyTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
            this.sync();
            this.samplePanelColor();
            return GLib.SOURCE_CONTINUE;
        });
        this.sync();
        this.samplePanelColor();
    }

    centerClock(monitor) {
        if (this.centering || Main.sessionMode.isLocked) return;
        const clock = Main.panel.statusArea.dateMenu;
        const label = clock._clockDisplay ?? clock;
        const [x] = label.get_transformed_position();
        const [width] = label.get_transformed_size();
        if (width <= 0) return;
        // An odd text width cannot be exactly centered on an even-width monitor
        // without a half-pixel origin. Snap the rendered origin to avoid filtering
        // the glyph texture and leave at most half a pixel of centering error.
        const targetX = Math.round(monitor.x + (monitor.width - width) / 2);
        const error = targetX - x;
        const parent = clock.get_parent?.();
        const parentScale = parent?.width > 0 ? parent.get_transformed_size()[0] / parent.width : 1;
        if (Math.abs(error) < .01 || parentScale <= 0) return;
        this.centering = true;
        try { clock.translation_x = (clock.translation_x ?? 0) + error / parentScale; }
        finally { this.centering = false; }
    }

    samplePanelColor() {
        if (this.destroyed || this.sampling || !this.actor.visible ||
            Main.panel.menuManager?.activeMenu || !Main.panel.visible) return;
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor) return;
        const [panelX, panelY] = Main.panel.get_transformed_position();
        const [panelWidth, panelHeight] = Main.panel.get_transformed_size();
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        // Sample directly below the centered clock, above the handle overlap.
        // A side sample can have a different composited color on translucent panels.
        const x = Math.round(Math.max(panelX, Math.min(panelX + panelWidth - 1,
            monitor.x + monitor.width / 2)));
        const y = Math.round(panelY + panelHeight - 4 * scale);
        if (x < 0 || y < 0) return;
        this.sampling = true;
        const shot = new Shell.Screenshot();
        shot.pick_color(x, y, (source, result) => {
            try {
                const resultColor = source.pick_color_finish(result);
                const color = Array.isArray(resultColor) ? resultColor.find(value => value && typeof value === 'object') : resultColor;
                if (!this.destroyed && color) {
                    this.panelColor = typeof color.get_red === 'function'
                        ? [color.get_red(), color.get_green(), color.get_blue()].map(value => value * 255)
                        : [color.red, color.green, color.blue];
                    this.actor.queue_repaint();
                }
            } catch (error) {
                // Retain the last valid sample if the compositor is unavailable.
            } finally { this.sampling = false; }
        });
    }

    contains(actor) { return !!actor && (actor === this.actor || this.actor.contains(actor)); }
    get active() { return !!this.drag?.moved; }

    trackWindow(window) {
        if (this.closedWindows.has(window) || this.windowSignals.has(window) || !window.connect) return;
        const ids = ['position-changed', 'size-changed', 'notify::minimized',
            'notify::maximized-vertically', 'notify::maximized-horizontally'].map(signal =>
            window.connect(signal, () => this.sync()));
        ids.push(window.connect('unmanaged', () => {
            this.closedWindows.add(window);
            for (const id of ids) window.disconnect(id);
            this.windowSignals.delete(window);
            this.sync();
        }));
        this.windowSignals.set(window, ids);
    }

    sync() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor) { this.actor.hide(); this.panelLine.hide(); return; }
        this.centerClock(monitor);
        const fullscreen = global.display.get_monitor_in_fullscreen(monitor.index);
        const normal = !Main.overview.visible && !Main.sessionMode.isLocked;
        const window = this.terminal._findWindow();
        const open = !!window && !window.minimized && !this.terminal._firstFrame;
        const [, panelHeight] = Main.panel.get_transformed_size();
        const windows = (global.get_window_actors?.() ?? []).map(actor => actor.meta_window).filter(candidate => candidate && !this.closedWindows.has(candidate));
        for (const candidate of windows) this.trackWindow(candidate);
        const crowded = windows.some(candidate => {
            if (candidate === window || candidate.minimized ||
                !candidate.showing_on_its_workspace() || candidate.get_monitor() !== monitor.index ||
                !candidate.can_close()) return false;
            // Maximization is authoritative even when theme gaps or work-area
            // insets leave the window frame a few pixels below the panel.
            if ((candidate.get_maximized?.() ?? 0) & Meta.MaximizeFlags.VERTICAL)
                return true;
            const frame = candidate.get_frame_rect();
            const center = monitor.x + monitor.width / 2;
            return frame.x <= center + 90 && frame.x + frame.width >= center - 90 &&
                frame.y <= monitor.y + panelHeight + 1 && frame.y + frame.height > monitor.y;
        });
        this.terminal._indicator.visible = fullscreen && normal;
        const clock = Main.panel.statusArea.dateMenu;
        const [clockX] = clock.get_transformed_position();
        const [clockWidth] = clock.get_transformed_size();
        const [, iconWidth] = this.terminal._indicator.get_preferred_width(panelHeight);
        this.terminal._indicator.set_size(iconWidth, panelHeight);
        this.terminal._indicator.set_position(Math.round(clockX + clockWidth), monitor.y);
        this.actor.visible = normal;
        const compact = fullscreen || open || crowded;
        if (compact !== this.compact) {
            const initial = this.compact === undefined;
            this.compact = compact;
            this.actor.set_pivot_point(.5, 0);
            this.actor.ease({scale_x: compact ? .5 : 1, scale_y: compact ? .5 : 1,
                duration: initial || !St.Settings.get().enable_animations ? 0 : 180,
                mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
        }
        this.panelLine.visible = !fullscreen && normal;
        const scheme = this.interfaceSettings.get_string('color-scheme');
        this.light = scheme === 'prefer-light' || (scheme === 'default' &&
            !Main.panel.has_style_pseudo_class?.('dark'));
        this.panelLine.style = `background-color: ${this.light
            ? 'rgba(70, 40, 100, 0.20)' : 'rgba(184, 166, 217, 0.20)'};`;
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this.panelLine.set_size(monitor.width, .75 * scale);
        this.panelLine.set_position(monitor.x, monitor.y + panelHeight - .75 * scale);
        this.actor.set_size(180 * scale, 18 * scale);
        this.actor.set_position(Math.round(monitor.x + monitor.width / 2 - 90 * scale),
            Math.round(monitor.y + panelHeight - 2 * scale));
        this.actor.queue_repaint();
    }

    paint() {
        const cr = this.actor.get_context();
        const [width, height] = this.actor.get_surface_size();
        try {
            cr.scale(width / 180, height / 18);
            // The desktop panel may be translucent; the handle needs an opaque silhouette.
            const panel = Main.panel.get_theme_node().get_background_color();
            const fill = this.panelColor ?? [panel.red, panel.green, panel.blue];
            cr.setSourceRGBA(...fill.map(c => c / 255), 1);
            // Mirrored control points, horizontal tangents at both shoulders.
            const outline = () => {
                cr.moveTo(0, 2);
                cr.curveTo(32, 2, 48, 17, 78, 17);
                cr.lineTo(102, 17);
                cr.curveTo(132, 17, 148, 2, 180, 2);
            };
            cr.moveTo(0, 0); cr.lineTo(0, 2);
            cr.curveTo(32, 2, 48, 17, 78, 17);
            cr.lineTo(102, 17); cr.curveTo(132, 17, 148, 2, 180, 2);
            cr.lineTo(180, 0); cr.closePath(); cr.fill();
            outline();
            const stroke = this.light ? [70, 40, 100] : [184, 166, 217];
            cr.setSourceRGBA(...stroke.map(c => c / 255), .20);
            cr.setLineWidth(.75); cr.stroke();
            const ink = this.light ? [33 / 255, 27 / 255, 43 / 255] : [1, 1, 1];
            cr.setSourceRGBA(...ink, this.actor.hover ? 1 : .85);
            cr.setLineWidth(1.25);
            for (const y of [3, 6, 9]) {
                cr.moveTo(85, y); cr.lineTo(95, y); cr.stroke();
            }
        } finally { cr.$dispose(); }
    }

    event(event) {
        const type = event.type();
        const source = this.drag ? null : global.stage.get_event_actor(event);
        if (!this.drag) {
            if (!this.actor.visible || !this.contains(source)) return Clutter.EVENT_PROPAGATE;
            if (type === Clutter.EventType.KEY_PRESS &&
                [Clutter.KEY_Return, Clutter.KEY_space].includes(event.get_key_symbol())) {
                this.terminal._toggle(); return Clutter.EVENT_STOP;
            }
            if (type !== Clutter.EventType.BUTTON_PRESS || event.get_button() !== 1)
                return Clutter.EVENT_PROPAGATE;
            const window = this.terminal._findWindow();
            this.drag = {startY: event.get_coords()[1], y: event.get_coords()[1],
                moved: false, initialHeight: window && !window.minimized ? window.get_frame_rect().height : 0,
                wasOpen: !!window && !window.minimized};
            // Keep tracking across native Wayland surfaces without a modal grab.
            this.poll = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 16, () => {
                const [x, y, state] = global.get_pointer();
                this.event({type: () => Clutter.EventType.MOTION,
                    get_coords: () => [x, y], get_state: () => state});
                return this.drag ? GLib.SOURCE_CONTINUE : GLib.SOURCE_REMOVE;
            });
            return Clutter.EVENT_STOP;
        }
        if (type === Clutter.EventType.KEY_PRESS && event.get_key_symbol() === Clutter.KEY_Escape) {
            this.finish(true); return Clutter.EVENT_STOP;
        }
        if (type === Clutter.EventType.MOTION || type === Clutter.EventType.BUTTON_RELEASE) {
            this.drag.y = event.get_coords()[1];
            if (!this.drag.moved && Math.abs(this.drag.y - this.drag.startY) > 6) {
                this.drag.moved = true;
                this.terminal._showTerminal();
            }
            if (this.drag.moved) {
                try { this.apply(); }
                catch (error) { this.finish(true); console.error('InfinityTerminal pull failed', error); return Clutter.EVENT_STOP; }
            }
            if (type === Clutter.EventType.MOTION && !(event.get_state() & Clutter.ModifierType.BUTTON1_MASK)) {
                this.finish(); return Clutter.EVENT_STOP;
            }
            if (type === Clutter.EventType.BUTTON_RELEASE && event.get_button() === 1) this.finish();
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    apply() {
        const window = this.terminal._findWindow();
        if (!this.active || !window || window.minimized || this.terminal._firstFrame) return;
        const actor = window.get_compositor_private();
        if (!actor) return;
        actor.remove_all_transitions();
        const monitor = this.terminal._monitor();
        const available = monitor.height - this.terminal._topInset();
        const distance = this.drag.y - this.drag.startY;
        this.drag.height = Math.min(available, Math.max(0, this.drag.initialHeight + distance));
        if (this.drag.height > window.get_frame_rect().height) {
            this.terminal._settings.set_double('height-ratio', this.drag.height / monitor.height);
            this.terminal._place(window);
        }
        actor.translation_y = this.drag.height - window.get_frame_rect().height;
        this.terminal._sliding = true;
        this.terminal._syncResizeHandle();
    }

    finish(cancel = false) {
        const drag = this.drag;
        this.drag = null;
        if (this.poll) { GLib.Source.remove(this.poll); this.poll = 0; }
        this.grab?.dismiss(); this.grab = null;
        if (!drag) return;
        if (!drag.moved) { if (!cancel) this.terminal._toggle(); return; }
        const height = cancel ? drag.initialHeight : drag.height ?? Math.max(0, drag.initialHeight + drag.y - drag.startY);
        const monitor = this.terminal._monitor();
        const [, panelHeight] = Main.panel.get_transformed_size();
        const tucked = !cancel && drag.y <= monitor.y + panelHeight + 2;
        const open = height > 60 && !tucked;
        const window = this.terminal._findWindow();
        if (!window || this.terminal._firstFrame) {
            if (open) this.terminal._settings.set_double('height-ratio', Math.max(96, height) / this.terminal._monitor().height);
            this.terminal._pendingShow = open;
            return;
        }
        if (!open) { this.terminal._hide(window); return; }
        const actor = window.get_compositor_private();
        if (!actor) return;
        actor.remove_all_transitions();
        this.terminal._settings.set_double('height-ratio', Math.max(96, height) / this.terminal._monitor().height);
        this.terminal._place(window);
        actor.translation_y = 0;
        global.stage.set_key_focus(null);
        window.activate(global.get_current_time());
        this.terminal._sliding = false;
        this.terminal._syncResizeHandle();
    }

    destroy() {
        this.destroyed = true;
        if (this.verifyTimer) { GLib.Source.remove(this.verifyTimer); this.verifyTimer = 0; }
        this.finish(true);
        for (const [object, id] of this.signals) object.disconnect(id);
        this.signals = [];
        if (this.clockActor) this.clockActor.translation_x = this.clockTranslation;
        for (const [window, ids] of this.windowSignals)
            for (const id of ids) window.disconnect(id);
        this.windowSignals.clear();
        Main.layoutManager.removeChrome(this.panelLine);
        this.panelLine.destroy();
        Main.layoutManager.removeChrome(this.actor);
        this.actor.destroy();
    }
}
