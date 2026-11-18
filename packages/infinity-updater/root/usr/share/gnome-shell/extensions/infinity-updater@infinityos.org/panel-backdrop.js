import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const LAYERS = new Set(['wackPanelBackdrop', 'wackPanelBackdropOverlay', 'wackPanelProximityOverlay']);

function backgroundStyle(actor) {
    const color = actor.get_theme_node().get_background_color();
    const rgba = typeof color.get_red === 'function'
        ? [color.get_red() * 255, color.get_green() * 255, color.get_blue() * 255, color.get_alpha()]
        : [color.red, color.green, color.blue, color.alpha / 255];
    return `background-color: rgba(${rgba.join(',')});`;
}

// Only the backdrop is blurred. GTK's labels, icons and buttons stay sharp.
export class PanelBackdrop {
    constructor() {
        this._entries = new Map();
        this._settings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this._colorId = this._settings.connect('changed::color-scheme', () => this.syncAll());
        this._extensionId = Main.extensionManager.connect('extension-state-changed', () => this.syncAll());
    }

    attach(window) {
        const actor = window.get_compositor_private();
        if (!actor) return;
        const old = this._entries.get(window);
        if (old?.actor === actor) { this.sync(window); return; }
        this.detach(window);
        const container = new St.Widget({name: 'infinity-updater-backdrop',
            reactive: false, clip_to_allocation: true});
        actor.insert_child_at_index(container, 0);
        const tint = new St.Widget({reactive: false});
        container.add_child(tint);
        const entry = {actor, container, tint, layers: [], signals: []};
        this._entries.set(window, entry);
        for (const signal of ['position-changed', 'size-changed'])
            entry.signals.push([window, window.connect(signal, () => this.sync(window))]);
        entry.signals.push([window, window.connect('unmanaged', () => this.detach(window))]);
        entry.signals.push([window, window.connect('notify::minimized', () => {
            if (window.minimized) this.detach(window);
        })]);
        entry.signals.push([actor, actor.connect('destroy', () => this.detach(window))]);
        this.sync(window);
        // Pipelines update their parameters directly. Poll only while the drawer
        // exists to reconnect after panel/BMS rebuilds and copy changing tints.
        if (!this._timer) this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
            this.syncAll();
            return GLib.SOURCE_CONTINUE;
        });
    }

    syncAll() {
        for (const window of this._entries.keys()) this.sync(window);
    }

    sync(window) {
        const entry = this._entries.get(window);
        if (!entry) return;
        const frame = window.get_frame_rect(), buffer = window.get_buffer_rect();
        if (frame.width <= 0 || frame.height <= 0) return;
        const monitorIndex = window.get_monitor() >= 0 ? window.get_monitor() : Main.layoutManager.primaryIndex;
        const monitor = Main.layoutManager.monitors[monitorIndex];
        if (!monitor) return;
        entry.container.set_position(frame.x - buffer.x, frame.y - buffer.y);
        entry.container.set_size(frame.width, frame.height);
        const blur = global.blur_my_shell?._panel_blur;
        const source = blur?.enabled && blur.createMatchingBackdrop ? blur : null;
        const key = source ? `${monitorIndex}:${source.settings.panel.STATIC_BLUR}:${source.settings.panel.PIPELINE}` : '';
        if (source !== entry.source || key !== entry.key || entry.backdrop?.destroyed) {
            entry.backdrop?.destroy();
            entry.backdrop = null;
            entry.source = source;
            entry.key = key;
            try { entry.backdrop = source?.createMatchingBackdrop(entry.container, monitorIndex); }
            catch (error) { console.warn(`InfinityUpdater backdrop: ${error}`); }
        }
        const backdrop = entry.backdrop;
        if (backdrop && !backdrop.destroyed) {
            const bg = backdrop.background;
            if (backdrop.staticBlur)
                bg.set_position(monitor.x - frame.x, monitor.y - frame.y + backdrop.offsetY);
            else {
                bg.set_position(0, 0);
                bg.set_size(frame.width, frame.height);
            }
            entry.tint.set_style(backgroundStyle(Main.panel));
        } else {
            const light = this._settings.get_string('color-scheme') !== 'prefer-dark';
            entry.tint.set_style(`background-color: ${light ? '#faf7ff' : '#181624'};`);
        }
        entry.tint.set_size(frame.width, frame.height);
        const layers = backdrop && !backdrop.destroyed
            ? Main.panel.get_children().filter(actor => LAYERS.has(actor.name)) : [];
        while (entry.layers.length > layers.length) entry.layers.pop().destroy();
        layers.forEach((source, index) => {
            let target = entry.layers[index];
            if (!target) {
                target = new St.Widget({reactive: false});
                entry.layers.push(target);
                entry.container.add_child(target);
            }
            // Wallpaper is rendered at the drawer's own stage coordinates by
            // the shared pipeline. Copy only the panel's translucent tints.
            target.set_style(backgroundStyle(source));
            target.opacity = source.opacity;
            target.visible = source.visible;
            target.set_size(frame.width, frame.height);
        });
    }

    detach(window) {
        const entry = this._entries.get(window);
        if (!entry) return;
        this._entries.delete(window);
        for (const [object, id] of entry.signals) object.disconnect(id);
        entry.backdrop?.destroy();
        entry.container.destroy();
        if (!this._entries.size && this._timer) {
            GLib.Source.remove(this._timer);
            this._timer = 0;
        }
    }

    destroy() {
        for (const window of [...this._entries.keys()]) this.detach(window);
        this._settings.disconnect(this._colorId);
        Main.extensionManager.disconnect(this._extensionId);
    }
}
