import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Mtk from 'gi://Mtk';
import Cairo from 'cairo';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const WIDTH = 180;
const HEIGHT = 18;
const SHOULDER = 2;
const BOTTOM = 17;
const PANEL_LAYERS = new Set(['wackPanelBackdrop', 'wackPanelBackdropOverlay', 'wackPanelProximityOverlay']);

function handleInset(y) {
    // Invert the vertical coordinate of the same cubic drawn in paint().
    let low = 0, high = 1;
    for (let i = 0; i < 12; i++) {
        const t = (low + high) / 2;
        if (t * t * (3 - 2 * t) < (y - SHOULDER) / (BOTTOM - SHOULDER)) low = t;
        else high = t;
    }
    const t = (low + high) / 2;
    const s = 1 - t;
    return 96 * s * s * t + 144 * s * t * t + 78 * t * t * t;
}

const PanelBackdropClip = GObject.registerClass(
class InfinityTerminalPanelBackdropClip extends Clutter.Effect {
    vfunc_paint(_node, context, _flags) {
        const actor = this.get_actor();
        const framebuffer = context.get_framebuffer();
        // PaintContext.get_stage_view() is not exposed to GJS. Resolve the
        // compositor view through the panel's public Actor API instead.
        const views = Main.panel.peek_stage_views();
        const view = views.find(candidate => candidate.get_framebuffer() === framebuffer) ?? views[0];
        const region = this.handle.backdropRegion(view, framebuffer);
        if (!region) {
            actor.continue_paint(context);
            return;
        }
        // Clip the output of the panel's blur in the stage framebuffer. The
        // blur still reads one rectangular input containing the full backdrop.
        framebuffer.push_region_clip(region);
        try { actor.continue_paint(context); }
        finally { framebuffer.pop_clip(); }
    }
});

// A separate chrome actor avoids enlarging the panel's reserved work area.
export class TerminalPullHandle {
    constructor(terminal) {
        this.terminal = terminal;
        this.signals = [];
        this.drag = null;
        this.windowSignals = new Map();
        this.closedWindows = new WeakSet();
        this.panelLine = new St.Widget({reactive: false});
        this.panelLineRight = new St.Widget({reactive: false});
        for (const line of [this.panelLine, this.panelLineRight])
            Main.layoutManager.addTopChrome(line, {affectsStruts: false, trackFullscreen: true});
        this.actor = new St.DrawingArea({reactive: true, can_focus: true, track_hover: true,
            accessible_name: 'Show, hide or drag InfinityTerminal',
            accessible_role: Atk.Role.PUSH_BUTTON});
        this.actor.connect('repaint', () => this.paint());
        this.actor.connect('notify::hover', () => this.actor.queue_repaint());
        this.actor.set_cursor_type(Clutter.CursorType.GRAB);
        Main.layoutManager.addTopChrome(this.actor, {affectsStruts: false, trackFullscreen: true});
        const connect = (object, signal, callback) => {
            this.signals.push([object, object.connect(signal, callback)]);
        };
        const sync = () => this.sync();
        this.panelLayers = [];
        Main.panel._infinityTerminalPullHandle = this;
        connect(this.actor, 'notify::scale-x', () => {
            this.syncPanelLine();
            this.actor.queue_repaint();
            this.repaintBackdrop();
        });
        connect(this.actor, 'notify::scale-y', () => {
            this.actor.queue_repaint();
            this.repaintBackdrop();
        });
        connect(Main.panel, 'child-added', sync);
        connect(Main.panel, 'child-removed', sync);
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
            return GLib.SOURCE_CONTINUE;
        });
        this.sync();
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

    createBackdropClip() {
        const clip = new PanelBackdropClip();
        clip.handle = this;
        return clip;
    }

    backdropRegion(view, framebuffer) {
        const region = Mtk.Region.create();
        const [px, py] = Main.panel.get_transformed_position();
        const [pw, ph] = Main.panel.get_transformed_size();
        // The boxed property is directly readable in GJS; get_layout() takes
        // a caller-allocated rectangle rather than returning one.
        const layout = view?.layout;
        const scale = view?.get_scale() ?? 1;
        const x = value => Math.round((value - (layout?.x ?? 0)) * scale);
        const y = value => Math.round((value - (layout?.y ?? 0)) * scale);
        const panelBottom = y(py + ph);
        const add = (left, top, right, bottom) => {
            if (right > left && bottom > top)
                region.union_rectangle(new Mtk.Rectangle({x: left, y: top, width: right - left, height: bottom - top}));
        };
        add(x(px), y(py), x(px + pw), panelBottom);
        if (!this.backdropExtension || !this.actor.mapped || !view ||
            framebuffer !== view.get_framebuffer()) return region;

        const [hx, hy] = this.actor.get_transformed_position();
        const [hw, hh] = this.actor.get_transformed_size();
        if (hh <= 0) return region;
        const top = (hy - layout.y) * scale;
        const height = hh * scale;
        // Use the displayed geometry, including the compaction animation.
        for (let row = panelBottom; row < y(hy + hh * BOTTOM / HEIGHT); row++) {
            const localY = (row + .5 - top) * HEIGHT / height;
            const inset = localY <= SHOULDER ? 0 : handleInset(localY) * hw / WIDTH;
            add(x(hx + inset), row, x(hx + hw - inset), row + 1);
        }
        return region;
    }

    syncBackdrop(extension) {
        const blur = global.blur_my_shell?._panel_blur;
        const native = blur?.actors_list?.find(actors =>
            actors.widgets.panel === Main.panel && !actors.is_dtp_panel);
        // BMS may initialize or rebuild its background after the handle. The
        // handle's height alone is not a sufficient cache key for that source.
        const changed = extension !== this.backdropExtension || blur !== this.panelBlur ||
            native !== this.nativeBackdrop;
        this.backdropExtension = extension;
        this.panelBlur = blur;
        this.nativeBackdrop = native;
        if (changed || (extension && native && native.terminalClip?.handle !== this))
            blur?.refreshTerminalHandle?.();
        this.repaintBackdrop();
        const layers = (Main.panel.get_children?.() ?? []).filter(layer => PANEL_LAYERS.has(layer.name));
        if (layers.length === this.panelLayers.length &&
            layers.every((layer, i) => layer === this.panelLayers[i])) return;
        for (const layer of this.panelLayers)
            layer.disconnectObject(this.actor);
        this.panelLayers = layers;
        const repaint = () => this.actor.queue_repaint();
        for (const layer of layers)
            layer.connectObject('style-changed', repaint, 'notify::opacity', repaint, 'notify::visible', repaint, this.actor);
    }

    repaintBackdrop() {
        // The contour is painted by the panel's blur actor, independently of
        // this DrawingArea. Invalidate that actor during every animation frame.
        this.nativeBackdrop?.widgets.background_group?.queue_redraw();
    }

    paintBackdrop(cr, height) {
        const [panelX, panelY] = Main.panel.get_transformed_position();
        const [, panelHeight] = Main.panel.get_transformed_size();
        const [handleX, handleY] = this.actor.get_transformed_position();
        const [handleWidth, handleHeight] = this.actor.get_transformed_size();
        if (handleWidth <= 0 || handleHeight <= 0) return;
        cr.save();
        // The first two pixels overlap the panel for the grip. Leave the
        // panel's own background visible there so its tint is applied once.
        const seam = (panelY + panelHeight - handleY) * HEIGHT / handleHeight;
        cr.rectangle(0, seam, WIDTH, height - seam);
        cr.clip();
        const paintTint = (actor, opacity = 1) => {
            const color = actor.get_theme_node().get_background_color();
            const rgba = typeof color.get_red === 'function'
                ? [color.get_red(), color.get_green(), color.get_blue(), color.get_alpha()]
                : [color.red, color.green, color.blue, color.alpha].map(channel => channel / 255);
            cr.setSourceRGBA(...rgba.slice(0, 3), rgba[3] * opacity);
            cr.paint();
        };
        paintTint(Main.panel);
        // Iterate in paint order because WACK can reorder the proximity tint.
        for (const layer of (Main.panel.get_children?.() ?? [])) {
            if (!PANEL_LAYERS.has(layer.name) || !layer.visible || !layer.opacity) continue;
            const strip = layer._infinityPanelStrip;
            if (!strip) {
                paintTint(layer, layer.opacity / 255);
                continue;
            }
            if (strip.path !== this.stripPath) {
                this.stripPath = strip.path;
                try { this.stripImage = Cairo.ImageSurface.createFromPNG(strip.path); }
                catch { this.stripImage = null; }
            }
            const image = this.stripImage;
            if (!image) continue;
            const imageScale = strip.width / image.getWidth();
            cr.save();
            cr.translate((panelX - handleX) * WIDTH / handleWidth,
                (panelY - handleY) * HEIGHT / handleHeight);
            cr.scale(imageScale * WIDTH / handleWidth, imageScale * HEIGHT / handleHeight);
            cr.setSourceSurface(image, 0, 0);
            cr.paintWithAlpha(layer.opacity / 255);
            cr.restore();
        }
        cr.restore();
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
        if (!monitor) {
            this.actor.hide();
            this.panelLine.hide();
            this.panelLineRight.hide();
            this.syncBackdrop(0);
            return;
        }
        this.centerClock(monitor);
        const visible = !global.display.get_monitor_in_fullscreen(monitor.index) &&
            !Main.overview.visible && !Main.sessionMode.isLocked;
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
            if (candidate.maximized_vertically)
                return true;
            const frame = candidate.get_frame_rect();
            const center = monitor.x + monitor.width / 2;
            return frame.x <= center + 90 && frame.x + frame.width >= center - 90 &&
                frame.y <= monitor.y + panelHeight + 1 && frame.y + frame.height > monitor.y;
        });
        this.actor.visible = visible;
        const compact = open || crowded;
        if (compact !== this.compact) {
            const initial = this.compact === undefined;
            this.compact = compact;
            this.actor.set_pivot_point(.5, 0);
            this.actor.ease({scale_x: compact ? .5 : 1, scale_y: compact ? .5 : 1,
                duration: initial || !St.Settings.get().enable_animations ? 0 : 180,
                mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
        }
        this.panelLine.visible = this.panelLineRight.visible = visible;
        const scheme = this.interfaceSettings.get_string('color-scheme');
        this.light = scheme === 'prefer-light' || (scheme === 'default' &&
            !Main.panel.has_style_pseudo_class?.('dark'));
        const lineStyle = `background-color: ${this.light
            ? 'rgba(70, 40, 100, 0.20)' : 'rgba(184, 166, 217, 0.20)'};`;
        this.panelLine.style = this.panelLineRight.style = lineStyle;
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this.actor.set_size(WIDTH * scale, HEIGHT * scale);
        this.actor.set_position(Math.round(monitor.x + monitor.width / 2 - WIDTH * scale / 2),
            Math.round(monitor.y + panelHeight - SHOULDER * scale));
        this.syncPanelLine();
        this.syncBackdrop(visible ? HEIGHT * scale : 0);
        this.actor.queue_repaint();
    }

    syncPanelLine() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor || !this.panelLine.visible) return;
        const [, panelHeight] = Main.panel.get_transformed_size();
        const themeScale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        const width = WIDTH * themeScale * this.actor.scale_x;
        const left = monitor.x + (monitor.width - width) / 2;
        const right = left + width;
        const height = .75 * themeScale;
        const y = monitor.y + panelHeight - height;
        this.panelLine.set_size(left - monitor.x, height);
        this.panelLine.set_position(monitor.x, y);
        this.panelLineRight.set_size(monitor.x + monitor.width - right, height);
        this.panelLineRight.set_position(right, y);
    }

    paint() {
        const cr = this.actor.get_context();
        const [width, height] = this.actor.get_surface_size();
        try {
            cr.scale(width / WIDTH, height / HEIGHT);
            // Mirrored control points, horizontal tangents at both shoulders.
            const outline = () => {
                cr.moveTo(0, 2);
                cr.curveTo(32, 2, 48, 17, 78, 17);
                cr.lineTo(102, 17);
                cr.curveTo(132, 17, 148, 2, 180, 2);
            };
            outline();
            cr.closePath();
            cr.save();
            cr.clip();
            this.paintBackdrop(cr, HEIGHT);
            cr.restore();
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
            this.showGrabCursor();
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
                this.terminal._showTerminal({bounce: false});
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

    showGrabCursor() {
        // A temporary transparent hit surface keeps the grab cursor over native
        // Wayland clients while the handle owns this pointer gesture.
        this.actor.set_cursor_type(Clutter.CursorType.GRABBING);
        const [width, height] = global.stage.get_size();
        this.cursorSurface = new St.Widget({reactive: true, width, height});
        this.cursorSurface.set_cursor_type(Clutter.CursorType.GRABBING);
        Main.layoutManager.addTopChrome(this.cursorSurface, {affectsStruts: false});
    }

    clearGrabCursor() {
        this.actor.set_cursor_type(Clutter.CursorType.GRAB);
        if (!this.cursorSurface) return;
        Main.layoutManager.removeChrome(this.cursorSurface);
        this.cursorSurface.destroy();
        this.cursorSurface = null;
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
        this.clearGrabCursor();
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
        delete Main.panel._infinityTerminalPullHandle;
        global.blur_my_shell?._panel_blur?.refreshTerminalHandle?.();
        for (const layer of this.panelLayers)
            layer.disconnectObject(this.actor);
        this.panelLayers = [];
        this.stripImage = null;
        if (this.verifyTimer) { GLib.Source.remove(this.verifyTimer); this.verifyTimer = 0; }
        this.finish(true);
        for (const [object, id] of this.signals) object.disconnect(id);
        this.signals = [];
        if (this.clockActor) this.clockActor.translation_x = this.clockTranslation;
        for (const [window, ids] of this.windowSignals)
            for (const id of ids) window.disconnect(id);
        this.windowSignals.clear();
        for (const line of [this.panelLine, this.panelLineRight]) {
            Main.layoutManager.removeChrome(line);
            line.destroy();
        }
        Main.layoutManager.removeChrome(this.actor);
        this.actor.destroy();
    }
}
