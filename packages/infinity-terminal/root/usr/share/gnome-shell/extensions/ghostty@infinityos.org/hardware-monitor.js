import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {appendSample, defaultMetrics, formatMetric, moveMetric, resolveMetric} from './monitor-model.mjs';

const pl = GLib.get_language_names()[0].startsWith('pl');
const tr = (en, polish) => pl ? polish : en;

export class HardwareMonitor {
    constructor(extension, changed) {
        this._extension = extension;
        this._settings = extension.getSettings();
        this._metrics = [];
        this._history = new Map();
        this._cells = [];
        this._alive = true;
        this.actor = new St.BoxLayout({reactive: true, visible: false,
            style_class: 'infinity-monitor', accessible_name: tr('Hardware monitors', 'Wskaźniki sprzętowe')});
        Main.layoutManager.addChrome(this.actor);
        this._menu = new PopupMenu.PopupMenu(this.actor, 0.5, St.Side.TOP);
        Main.uiGroup.add_child(this._menu.actor);
        this._menu.actor.hide();
        this._menu.actor.set_style('max-height: 650px;');
        this._manager = new PopupMenu.PopupMenuManager(this.actor);
        this._manager.addMenu(this._menu);
        this._settingsId = this._settings.connect('changed', (_settings, key) => {
            if (!key.startsWith('monitor-')) return;
            this._history.clear();
            this._rebuild();
            this._restart();
            changed();
        });
        const contextClick = new Clutter.ClickGesture({recognize_on_press: true});
        contextClick.connect('may-recognize', gesture => gesture.get_point_event(0).get_button() === 3);
        contextClick.connect('recognize', gesture => {
            const source = global.stage.get_event_actor(gesture.get_point_event(0));
            const index = this._cells.findIndex(cell => cell.actor === source || cell.actor.contains(source));
            this._openMenu(index);
        });
        this.actor.add_action_full('hardware-context-menu', Clutter.EventPhase.CAPTURE, contextClick);
        this._rebuild();
    }

    get height() { return this._settings.get_boolean('monitor-enabled')
        ? 112 * St.ThemeContext.get_for_stage(global.stage).scale_factor : 0; }
    get menuOpen() { return this._menu.isOpen; }
    contains(actor) { return actor && (this.actor.contains(actor) || this._menu.actor.contains(actor)); }

    sync(rect, visible, windowActor = null) {
        if (this._windowActor !== windowActor) {
            this._unfollow();
            this._windowActor = windowActor;
            if (windowActor) {
                this._translationId = windowActor.connect('notify::translation-y', () => {
                    this.actor.translation_y = windowActor.translation_y;
                });
                this._destroyActorId = windowActor.connect('destroy', () => {
                    this._unfollow();
                    this.hide();
                });
            }
        }
        this.actor.translation_y = windowActor?.translation_y ?? 0;
        const show = !!visible && this.height > 0;
        if (show) {
            this.actor.set_position(rect.x, rect.y - this.height);
            this.actor.set_size(rect.width, this.height);
        }
        if (show === this.actor.visible) return;
        this.actor.visible = show;
        if (!show) { this._menu.close(); this._history.clear(); }
        this._restart();
    }

    hide() { this.sync(null, false); }

    _unfollow() {
        if (this._windowActor) {
            this._windowActor.disconnect(this._translationId);
            this._windowActor.disconnect(this._destroyActorId);
        }
        this._windowActor = null;
    }

    _restart() {
        if (this._timer) GLib.Source.remove(this._timer);
        this._timer = 0;
        if (!this.actor.visible) {
            this._process?.force_exit();
            return;
        }
        this._sample();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,
            this._settings.get_int('monitor-interval'), () => {
                this._sample();
                return GLib.SOURCE_CONTINUE;
            });
    }

    _sample() {
        if (this._process || !this._alive) return;
        try {
            const process = Gio.Subprocess.new(['python3', `${this._extension.path}/hardware-snapshot.py`],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            this._process = process;
            const timeout = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 4, () => {
                this._timeout = 0;
                process.force_exit();
                return GLib.SOURCE_REMOVE;
            });
            this._timeout = timeout;
            process.communicate_utf8_async(null, null, (proc, result) => {
                if (this._timeout) GLib.Source.remove(this._timeout);
                this._timeout = 0;
                this._process = null;
                let metrics = [];
                try {
                    const [, output] = proc.communicate_utf8_finish(result);
                    if (proc.get_successful()) metrics = JSON.parse(output);
                } catch (_error) { /* Unavailable sensors remain N/A. */ }
                if (!this._alive || !this.actor.visible) return;
                this._metrics = Array.isArray(metrics) ? metrics : [];
                this._update();
            });
        } catch (_error) {
            this._metrics = [];
            this._update();
        }
    }

    _rebuild() {
        this.actor.destroy_all_children();
        this._cells = [];
        const scroll = new St.ScrollView({x_expand: true, y_expand: true,
            hscrollbar_policy: St.PolicyType.AUTOMATIC, vscrollbar_policy: St.PolicyType.NEVER});
        const row = new St.BoxLayout({x_expand: true});
        scroll.set_child(row);
        this.actor.add_child(scroll);
        for (const id of this._settings.get_strv('monitor-metrics')) {
            const actor = new St.Button({style_class: 'infinity-monitor-cell', width: 180 * St.ThemeContext.get_for_stage(global.stage).scale_factor, x_expand: true, can_focus: true});
            const box = new St.BoxLayout({vertical: true});
            const value = new St.Label({style_class: 'infinity-monitor-value', text: 'N/A'});
            const graph = new St.DrawingArea({height: 28, x_expand: true});
            const label = new St.Label({style_class: 'infinity-monitor-label'});
            box.add_child(value); box.add_child(graph); box.add_child(label);
            actor.set_child(box); row.add_child(actor);
            const cell = {id, actor, value, graph, label};
            graph.connect('repaint', () => this._paint(cell));
            actor.connect('clicked', () => this._openMenu(this._cells.indexOf(cell)));
            this._cells.push(cell);
        }
        if (!this._cells.length) {
            const button = new St.Button({label: tr('Add monitors…', 'Dodaj wskaźniki…'), can_focus: true});
            button.connect('clicked', () => this._openMenu(-1));
            row.add_child(button);
        }
        this._update(false);
    }

    _update(record = true) {
        const recorded = new Set();
        for (const cell of this._cells) {
            const metric = resolveMetric(cell.id, this._metrics, this._settings.get_int('monitor-cpu-tdp'));
            // Auto sources must never join histories from different devices.
            const key = metric.id;
            if (record && !recorded.has(key)) this._history.set(key, appendSample(this._history.get(key) ?? [], metric.value,
                Math.ceil(this._settings.get_int('monitor-history') / this._settings.get_int('monitor-interval'))));
            recorded.add(key);
            cell.metric = metric;
            cell.value.text = formatMetric(metric, this._settings.get_boolean('monitor-fahrenheit'));
            cell.label.text = metric.label;
            cell.actor.accessible_name = `${metric.group ?? ''} ${metric.label}: ${cell.value.text}`;
            cell.graph.visible = this._settings.get_boolean('monitor-graphs');
            cell.graph.queue_repaint();
        }
    }

    _paint(cell) {
        const cr = cell.graph.get_context();
        try {
            const [width, height] = cell.graph.get_surface_size();
            const metric = cell.metric;
            const history = this._history.get(metric?.id) ?? [];
            cr.setSourceRGBA(0.65, 0.42, 0.92, 0.12);
            cr.rectangle(0, 0, width, height); cr.fill();
            if (!this._settings.get_boolean('monitor-graphs')) return;
            cr.setSourceRGBA(0.73, 0.53, 0.96, 1); cr.setLineWidth(1.5);
            if (metric?.maximum > 0 && Number.isFinite(metric.value)) {
                cr.rectangle(0, height - 8, width * Math.max(0, Math.min(1, metric.value / metric.maximum)), 8);
                cr.fill(); return;
            }
            const maximum = Math.max(1, ...history.filter(Number.isFinite)) * 1.1;
            let started = false;
            history.forEach((value, index) => {
                if (value === null) { started = false; return; }
                const x = index * width / Math.max(1, history.length - 1);
                const y = height - 2 - Math.max(0, value) / maximum * (height - 4);
                if (started) cr.lineTo(x, y); else cr.moveTo(x, y);
                started = true;
            });
            cr.stroke();
        } finally { cr.$dispose(); }
    }

    _openMenu(index) {
        this._menu.removeAll();
        const ids = this._settings.get_strv('monitor-metrics');
        const save = next => this._settings.set_strv('monitor-metrics', next);
        const action = (menu, label, callback) => {
            const item = new PopupMenu.PopupMenuItem(label);
            item.connect('activate', callback); menu.addMenuItem(item);
        };
        const sources = (title, select) => {
            const parent = new PopupMenu.PopupSubMenuMenuItem(title);
            this._menu.addMenuItem(parent);
            const groups = new Map();
            const available = [...this._metrics, resolveMetric('cpu:tdp', [], this._settings.get_int('monitor-cpu-tdp'))];
            for (const metric of available) {
                if (!groups.has(metric.group)) {
                    parent.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(metric.group));
                    groups.set(metric.group, parent.menu);
                }
                action(groups.get(metric.group), `${metric.label} (${formatMetric(metric)})`, () => select(metric.id));
            }
        };
        if (index >= 0) {
            const metric = this._cells[index].metric;
            const heading = new PopupMenu.PopupMenuItem(`${metric.group ?? ''} · ${metric.label}`, {reactive: false});
            this._menu.addMenuItem(heading);
            sources(tr('Change sensor / device', 'Zmień czujnik / urządzenie'), id => { ids[index] = id; save(ids); });
            action(this._menu, tr('Move left', 'Przesuń w lewo'), () => save(moveMetric(ids, index, -1)));
            action(this._menu, tr('Move right', 'Przesuń w prawo'), () => save(moveMetric(ids, index, 1)));
            action(this._menu, tr('Remove monitor', 'Usuń wskaźnik'), () => save(ids.filter((_id, i) => i !== index)));
            this._menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        }
        sources(tr('Add monitor', 'Dodaj wskaźnik'), id => save([...ids, id]));
        for (const [title, key, options] of [
            [tr('Refresh interval', 'Odświeżanie'), 'monitor-interval', [1, 2, 5, 10]],
            [tr('History length', 'Długość historii'), 'monitor-history', [30, 60, 120, 300]],
        ]) {
            const submenu = new PopupMenu.PopupSubMenuMenuItem(title); this._menu.addMenuItem(submenu);
            for (const seconds of options)
                action(submenu.menu, `${seconds === this._settings.get_int(key) ? '✓ ' : ''}${seconds} s`, () => this._settings.set_int(key, seconds));
        }
        for (const [label, key] of [[tr('Show graphs', 'Pokaż wykresy'), 'monitor-graphs'], ['Fahrenheit (°F)', 'monitor-fahrenheit']]) {
            const item = new PopupMenu.PopupSwitchMenuItem(label, this._settings.get_boolean(key));
            item.connect('toggled', (_item, state) => this._settings.set_boolean(key, state));
            this._menu.addMenuItem(item);
        }
        action(this._menu, tr('Settings / manual CPU TDP…', 'Ustawienia / ręczne TDP CPU…'), () => this._extension.openPreferences());
        action(this._menu, tr('Restore default monitors', 'Przywróć domyślne wskaźniki'), () => save(defaultMetrics));
        this._menu.open();
    }

    destroy() {
        this._alive = false;
        this._unfollow();
        if (this._timer) GLib.Source.remove(this._timer);
        if (this._timeout) GLib.Source.remove(this._timeout);
        this._timeout = 0;
        this._process?.force_exit();
        this._settings.disconnect(this._settingsId);
        this._menu.destroy();
        Main.layoutManager.removeChrome(this.actor);
        this.actor.destroy();
    }
}
