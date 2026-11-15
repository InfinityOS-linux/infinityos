import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// A separate chrome actor avoids enlarging the panel's reserved work area.
export class TerminalPullHandle {
    constructor(terminal) {
        this.terminal = terminal;
        this.signals = [];
        this.drag = null;
        this.actor = new St.DrawingArea({reactive: true, can_focus: true, track_hover: true,
            accessible_name: 'Show or drag down InfinityTerminal',
            accessible_role: Atk.Role.PUSH_BUTTON});
        this.actor.connect('repaint', () => this.paint());
        this.actor.connect('notify::hover', () => this.actor.queue_repaint());
        Main.layoutManager.addTopChrome(this.actor, {affectsStruts: false, trackFullscreen: true});
        const connect = (object, signal, callback) => {
            this.signals.push([object, object.connect(signal, callback)]);
        };
        const sync = () => this.sync();
        connect(Main.panel, 'notify::allocation', sync);
        connect(Main.panel, 'style-changed', () => { this.actor.queue_repaint(); this.sync(); });
        connect(Main.panel.statusArea.dateMenu, 'notify::allocation', sync);
        connect(Main.layoutManager, 'startup-complete', sync);
        connect(Main.layoutManager, 'monitors-changed', () => { this.finish(true); this.sync(); });
        connect(global.display, 'in-fullscreen-changed', () => { this.finish(true); this.sync(); });
        connect(Main.overview, 'showing', () => { this.finish(true); this.sync(); });
        connect(Main.overview, 'hidden', sync);
        connect(Main.sessionMode, 'updated', () => { this.finish(true); this.sync(); });
        connect(global.stage, 'captured-event', (_stage, event) => this.event(event));
        this.sync();
    }

    contains(actor) { return !!actor && (actor === this.actor || this.actor.contains(actor)); }
    get active() { return !!this.drag?.moved; }

    sync() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor) { this.actor.hide(); return; }
        const fullscreen = global.display.get_monitor_in_fullscreen(monitor.index);
        const normal = !Main.overview.visible && !Main.sessionMode.isLocked;
        this.terminal._indicator.visible = fullscreen && normal;
        this.actor.visible = !fullscreen && normal;
        const clock = Main.panel.statusArea.dateMenu;
        const [x] = clock.get_transformed_position();
        const [width] = clock.get_transformed_size();
        const [, panelHeight] = Main.panel.get_transformed_size();
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this.actor.set_size(180 * scale, 18 * scale);
        this.actor.set_position(Math.round(x + width / 2 - 90 * scale),
            Math.round(monitor.y + panelHeight - 1));
        this.actor.queue_repaint();
    }

    paint() {
        const cr = this.actor.get_context();
        const [width, height] = this.actor.get_surface_size();
        try {
            cr.scale(width / 180, height / 18);
            // The desktop panel may be translucent; the handle needs an opaque silhouette.
            cr.setSourceRGBA(11 / 255, 9 / 255, 18 / 255, 1);
            // Mirrored control points, horizontal tangents at both shoulders.
            cr.moveTo(0, 0);
            cr.curveTo(32, 0, 48, 17, 78, 17);
            cr.lineTo(102, 17);
            cr.curveTo(132, 17, 148, 0, 180, 0);
            cr.closePath(); cr.fillPreserve();
            cr.setSourceRGBA(.72, .65, .85, .20); cr.setLineWidth(.75); cr.stroke();
            cr.setSourceRGBA(1, 1, 1, this.actor.hover ? 1 : .85);
            cr.setLineWidth(1.25);
            for (const y of [6, 9, 12]) {
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
        const open = height > 60;
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
        this.terminal._sliding = false;
        this.terminal._syncResizeHandle();
    }

    destroy() {
        this.finish(true);
        for (const [object, id] of this.signals) object.disconnect(id);
        this.signals = [];
        Main.layoutManager.removeChrome(this.actor);
        this.actor.destroy();
    }
}
