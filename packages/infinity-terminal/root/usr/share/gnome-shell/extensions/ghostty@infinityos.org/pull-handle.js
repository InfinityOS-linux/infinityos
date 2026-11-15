import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
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
        Main.layoutManager.addChrome(this.actor, {affectsStruts: false, trackFullscreen: true});
        const connect = (object, signal, callback) => {
            this.signals.push([object, object.connect(signal, callback)]);
        };
        const sync = () => this.sync();
        connect(Main.panel, 'notify::allocation', sync);
        connect(Main.panel, 'style-changed', () => { this.actor.queue_repaint(); this.sync(); });
        connect(Main.panel.statusArea.dateMenu, 'notify::allocation', sync);
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
        const [, panelY] = Main.panel.get_transformed_position();
        const [, panelHeight] = Main.panel.get_transformed_size();
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this.actor.set_size(180 * scale, 18 * scale);
        this.actor.set_position(Math.round(x + width / 2 - 90 * scale),
            Math.round(panelY + panelHeight - 1));
        this.actor.queue_repaint();
    }

    paint() {
        const cr = this.actor.get_context();
        const [width, height] = this.actor.get_surface_size();
        try {
            cr.scale(width / 180, height / 18);
            const color = Main.panel.get_theme_node().get_background_color();
            if (color.alpha) cr.setSourceRGBA(color.red / 255, color.green / 255,
                color.blue / 255, color.alpha / 255);
            else cr.setSourceRGBA(11 / 255, 9 / 255, 18 / 255, 1);
            // Mirrored control points, horizontal tangents at both shoulders.
            cr.moveTo(0, 0);
            cr.curveTo(32, 0, 48, 17, 78, 17);
            cr.lineTo(102, 17);
            cr.curveTo(132, 17, 148, 0, 180, 0);
            cr.closePath(); cr.fill();
            cr.setSourceRGBA(1, 1, 1, this.actor.hover ? 1 : .85);
            cr.setLineWidth(1.25);
            for (const y of [6, 9, 12]) {
                cr.moveTo(85, y); cr.lineTo(95, y); cr.stroke();
            }
        } finally { cr.$dispose(); }
    }

    event(event) {
        const type = event.type();
        const source = global.stage.get_event_actor(event);
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
                moved: false, wasOpen: !!window && !window.minimized};
            try { this.grab = global.stage.grab(this.actor); }
            catch (error) { this.drag = null; console.error(error); }
            return Clutter.EVENT_STOP;
        }
        if (type === Clutter.EventType.KEY_PRESS && event.get_key_symbol() === Clutter.KEY_Escape) {
            this.finish(true); return Clutter.EVENT_STOP;
        }
        if (type === Clutter.EventType.MOTION || type === Clutter.EventType.BUTTON_RELEASE) {
            this.drag.y = event.get_coords()[1];
            if (type === Clutter.EventType.MOTION && !(event.get_state() & Clutter.ModifierType.BUTTON1_MASK)) {
                this.finish(); return Clutter.EVENT_STOP;
            }
            if (!this.drag.moved && Math.abs(this.drag.y - this.drag.startY) > 6) {
                this.drag.moved = true;
                this.terminal._showTerminal();
            }
            if (this.drag.moved) {
                try { this.apply(); }
                catch (error) { this.finish(true); console.error('InfinityTerminal pull failed', error); return Clutter.EVENT_STOP; }
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
        const offset = this.terminal._offscreenOffset(window);
        const distance = this.drag.y - this.drag.startY;
        actor.translation_y = Math.min(0, Math.max(offset, (this.drag.wasOpen ? 0 : offset) + distance));
        this.terminal._sliding = true;
        this.terminal._syncResizeHandle();
    }

    finish(cancel = false) {
        const drag = this.drag;
        this.drag = null;
        this.grab?.dismiss(); this.grab = null;
        if (!drag) return;
        if (!drag.moved) { if (!cancel) this.terminal._toggle(); return; }
        const open = cancel ? drag.wasOpen : drag.wasOpen
            ? drag.y - drag.startY > -60 : drag.y - drag.startY > 60;
        const window = this.terminal._findWindow();
        if (!window || this.terminal._firstFrame) {
            this.terminal._pendingShow = open;
            return;
        }
        if (!open) { this.terminal._hide(window); return; }
        const actor = window.get_compositor_private();
        if (!actor) return;
        actor.ease({translation_y: 0, duration: St.Settings.get().enable_animations ? 220 : 0,
            mode: Clutter.AnimationMode.EASE_OUT_CUBIC,
            onComplete: () => { this.terminal._sliding = false; this.terminal._syncResizeHandle(); }});
    }

    destroy() {
        this.finish(true);
        for (const [object, id] of this.signals) object.disconnect(id);
        this.signals = [];
        Main.layoutManager.removeChrome(this.actor);
        this.actor.destroy();
    }
}
