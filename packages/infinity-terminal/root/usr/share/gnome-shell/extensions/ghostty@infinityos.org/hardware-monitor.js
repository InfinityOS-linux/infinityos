import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as DND from 'resource:///org/gnome/shell/ui/dnd.js';
import {MonitorWidgets, widgetChoices} from './monitor-widgets.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {appendSample, defaultMetrics, formatMetric, moveMetric, resolveMetric, uniqueMetrics, toggleMetric, dropMetric} from './monitor-model.mjs';

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
        this._widgets = new MonitorWidgets(() => { if (this._alive) this._updateWidgets(); }, this._settings);
        this.actor = new St.BoxLayout({reactive: true, visible: false,
            style_class: 'infinity-monitor', accessible_name: tr('Hardware monitors', 'Wskaźniki sprzętowe')});
        this._colorSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        const syncTheme = () => {
            this._light = this._colorSettings.get_string('color-scheme') !== 'prefer-dark';
            if (this._light)
                this.actor.add_style_class_name('light');
            else this.actor.remove_style_class_name('light');
            if (this._menu) {
                this._menu.actor.set_style(this._menuStyle());
                if (this._light) this._menu.actor.add_style_class_name('light');
                else this._menu.actor.remove_style_class_name('light');
            }
            this._cells.forEach(cell => cell.graph?.queue_repaint());
        };
        this._colorId = this._colorSettings.connect('changed::color-scheme', syncTheme);
        syncTheme();
        Main.layoutManager.addChrome(this.actor);
        this._menuAnchor = new St.Widget({width: 1, height: 1, opacity: 0, reactive: false});
        Main.layoutManager.addChrome(this._menuAnchor);
        this._menu = new PopupMenu.PopupMenu(this._menuAnchor, 0, St.Side.TOP);
        Main.uiGroup.add_child(this._menu.actor);
        this._menu.actor.hide();
        this._menu.actor.add_style_class_name('infinity-monitor-menu');
        if (this._light) this._menu.actor.add_style_class_name('light');
        this._menu.actor.set_style(this._menuStyle());
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
            this._openMenu(index, gesture.get_point_event(0).get_coords());
        });
        this.actor.add_action_full('hardware-context-menu', Clutter.EventPhase.CAPTURE, contextClick);
        this._rebuild();
    }

    get height() { return this._settings.get_boolean('monitor-enabled')
        ? 72 * St.ThemeContext.get_for_stage(global.stage).scale_factor : 0; }
    get menuOpen() { return this._menu.isOpen || this._dragging; }
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
        if (this._widgetTimer) GLib.Source.remove(this._widgetTimer);
        this._widgetTimer = 0;
        if (!this.actor.visible) {
            this._widgets?.pauseNetwork();
            this._process?.force_exit();
            return;
        }
        this._updateWidgets();
        if (this._cells.some(cell => cell.id.startsWith('widget:'))) {
            const ticking = this._cells.some(cell => ['widget:stopwatch', 'widget:timer', 'widget:pomodoro', 'widget:clock', 'widget:network'].includes(cell.id));
            this._widgetTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, ticking ? 1 : 60, () => {
                this._updateWidgets();
                return GLib.SOURCE_CONTINUE;
            });
        }
        this._sample();
        if (!this._cells.some(cell => !cell.id.startsWith('widget:'))) return;
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
        this._widgets?.select(this._settings.get_strv('monitor-metrics'));
        this.actor.destroy_all_children();
        this._cells = [];
        const scroll = new St.ScrollView({x_expand: true, y_expand: true,
            hscrollbar_policy: St.PolicyType.EXTERNAL, vscrollbar_policy: St.PolicyType.NEVER});
        const row = new St.BoxLayout({x_expand: false, x_align: Clutter.ActorAlign.CENTER});
        scroll.set_child(row);
        this.actor.add_child(scroll);
        for (const id of new Set(this._settings.get_strv('monitor-metrics'))) {
            const actor = new St.Button({style_class: 'infinity-monitor-cell', width: 128 * St.ThemeContext.get_for_stage(global.stage).scale_factor, x_expand: false, can_focus: true});
            if (id.startsWith('widget:')) {
                if (!widgetChoices.some(choice => choice.id === id)) continue;
                this._addWidget(id, actor, row);
                continue;
            }
            const box = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, y_align: Clutter.ActorAlign.START, x_expand: true, x_align: Clutter.ActorAlign.FILL});
            const value = new St.Label({style_class: 'infinity-monitor-value', text: 'N/A'});
            const graph = new St.DrawingArea({style_class: 'infinity-monitor-graph', x_expand: true, y_expand: false});
            const label = new St.Label({style_class: 'infinity-monitor-label', y_expand: false});
            box.add_child(value); box.add_child(graph); box.add_child(label);
            actor.set_child(box); row.add_child(actor);
            const cell = {id, actor, value, graph, label};
            graph.connect('repaint', () => this._paint(cell));
            actor.connect('clicked', () => this._openMenu(this._cells.indexOf(cell)));
            this._cells.push(cell);
            this._enableDrag(cell);
        }
        {
            const button = new St.Button({label: tr('Add monitors…', 'Dodaj wskaźniki…'), can_focus: true});
            button.connect('clicked', () => this._openMenu(-1));
            row.add_child(button);
            this._emptyButton = button;
        }
        this._update(false);
    }

    _update(record = true) {
        const recorded = new Set();
        const displayed = new Set();
        for (const cell of this._cells) {
            if (cell.id.startsWith('widget:')) continue;
            const metric = resolveMetric(cell.id, this._metrics, this._settings.get_int('monitor-cpu-tdp'));
            // Auto sources must never join histories from different devices.
            const key = metric.id;
            if (record && !recorded.has(key)) this._history.set(key, appendSample(this._history.get(key) ?? [], metric.value,
                Math.ceil(this._settings.get_int('monitor-history') / this._settings.get_int('monitor-interval'))));
            recorded.add(key);
            cell.metric = metric;
            cell.actor.visible = !displayed.has(key) && (!this._settings.get_boolean('monitor-hide-unavailable') || Number.isFinite(metric.value));
            displayed.add(key);
            cell.value.text = formatMetric(metric, this._settings.get_boolean('monitor-fahrenheit'));
            cell.label.text = metric.label.toUpperCase();
            cell.actor.accessible_name = `${metric.group ?? ''} ${metric.label}: ${cell.value.text}`;
            cell.graph.visible = this._settings.get_boolean('monitor-graphs');
            cell.graph.queue_repaint();
        }
        this._updateWidgets();
        this._emptyButton.visible = !this._cells.some(cell => cell.actor.visible);
    }

    _paint(cell) {
        const cr = cell.graph.get_context();
        try {
            const [width, height] = cell.graph.get_surface_size();
            const metric = cell.metric;
            const history = this._history.get(metric?.id) ?? [];
            if (this._light) cr.setSourceRGBA(0.35, 0.20, 0.56, 0.12);
            else cr.setSourceRGBA(0.65, 0.42, 0.92, 0.12);
            cr.rectangle(0, 0, width, height); cr.fill();
            if (!this._settings.get_boolean('monitor-graphs')) return;
            if (this._light) cr.setSourceRGBA(0.35, 0.20, 0.56, 1);
            else cr.setSourceRGBA(0.73, 0.53, 0.96, 1);
            cr.setLineWidth(1.5);
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

    _openMenu(index, coordinates = null) {
        this._menu.close();
        const [x, y] = coordinates ?? global.get_pointer();
        this._menuAnchor.set_position(x, y);
        this._menu.removeAll();
        const selectedId = this._cells[index]?.id;
        const ids = this._settings.get_strv('monitor-metrics');
        index = selectedId === undefined ? -1 : ids.indexOf(selectedId);
        const save = next => this._settings.set_strv('monitor-metrics', uniqueMetrics(next, this._metrics));
        const action = (menu, label, callback) => {
            const item = new PopupMenu.PopupMenuItem(label);
            item.connect('activate', callback); menu.addMenuItem(item);
            return item;
        };
        const sources = (title, select) => {
            const parent = new PopupMenu.PopupSubMenuMenuItem(title);
            this._menu.addMenuItem(parent);
            const groups = new Map();
            const available = [...new Map([...this._metrics, ...ids.filter(id => !id.startsWith('widget:')).map(id => resolveMetric(id, this._metrics)), resolveMetric('cpu:tdp', [], this._settings.get_int('monitor-cpu-tdp'))].map(metric => [metric.id, metric])).values()];
            for (const metric of available) {
                if (!groups.has(metric.group)) {
                    parent.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(metric.group));
                    groups.set(metric.group, parent.menu);
                }
                const selected = this._cells.filter(cell => cell.metric?.id === metric.id);
                const displayed = selected.some(cell => cell.actor.visible);
                const hidden = selected.length && !displayed ? tr(' · hidden', ' · ukryty') : '';
                const item = action(groups.get(metric.group), `${metric.label} (${formatMetric(metric)})${hidden}`, () => select(metric.id));
                item.setOrnament(displayed ? PopupMenu.Ornament.CHECK
                    : selected.length ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
            }
        };
        if (index >= 0) {
            const metric = this._cells.find(cell => cell.id === selectedId).metric;
            if (ids[index] === 'widget:stopwatch') {
                action(this._menu, this._widgets.stopwatch.running ? tr('Pause', 'Pauza') : tr('Start', 'Start'), () => {
                    this._widgets.stopwatch.toggle(); this._updateWidgets();
                });
                action(this._menu, tr('Reset stopwatch', 'Wyzeruj stoper'), () => {
                    this._widgets.stopwatch.reset(); this._updateWidgets();
                });
            }
            if (this._widgets?.timers[ids[index]]) {
                const timer = this._widgets.timers[ids[index]];
                action(this._menu, timer.running ? tr('Pause', 'Pauza') : tr('Start', 'Start'), () => this._widgets.toggleTimer(ids[index]));
                action(this._menu, tr('Reset', 'Wyzeruj'), () => this._widgets.resetTimer(ids[index]));
                if (ids[index] === 'widget:timer') {
                    const duration = new PopupMenu.PopupSubMenuMenuItem(tr('Duration', 'Czas'));
                    this._menu.addMenuItem(duration);
                    for (const minutes of [1, 5, 10, 15, 25, 50, 60])
                        action(duration.menu, `${minutes} min`, () => this._widgets.resetTimer(ids[index], minutes));
                }
            }
            if (ids[index] === 'widget:clock') {
                const zones = new PopupMenu.PopupSubMenuMenuItem(tr('Time zone', 'Strefa czasowa'));
                this._menu.addMenuItem(zones);
                for (const zone of ['UTC', 'Europe/Warsaw', 'Europe/London', 'America/New_York', 'Asia/Tokyo'])
                    action(zones.menu, zone, () => this._settings.set_string('monitor-timezone', zone));
            }
            if (ids[index] === 'widget:weather' && this._widgets.weather?.available)
                action(this._menu, tr('Open Weather / location settings', 'Otwórz Pogodę / ustawienia lokalizacji'), () => this._widgets.weather.activateApp());
            const heading = new PopupMenu.PopupMenuItem(`${metric.group ?? ''} · ${metric.label}`, {reactive: false});
            this._menu.addMenuItem(heading);
            if (!ids[index].startsWith('widget:')) sources(tr('Change sensor / device', 'Zmień czujnik / urządzenie'), id => { ids[index] = id; save(ids); });
            action(this._menu, tr('Move left', 'Przesuń w lewo'), () => save(moveMetric(ids, index, -1)));
            action(this._menu, tr('Move right', 'Przesuń w prawo'), () => save(moveMetric(ids, index, 1)));
            action(this._menu, tr('Remove monitor', 'Usuń wskaźnik'), () => save(ids.filter((_id, i) => i !== index)));
            this._menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        }
        sources(tr('Add monitor', 'Dodaj wskaźnik'), id => save(toggleMetric(ids, id, this._metrics)));
        const widgets = new PopupMenu.PopupSubMenuMenuItem(tr('Add widget', 'Dodaj widget'));
        this._menu.addMenuItem(widgets);
        for (const choice of widgetChoices) {
            const item = new PopupMenu.PopupImageMenuItem(choice.label, choice.icon);
            item.setOrnament(ids.includes(choice.id) ? PopupMenu.Ornament.CHECK : PopupMenu.Ornament.NONE);
            item.connect('activate', () => save(toggleMetric(ids, choice.id, this._metrics)));
            widgets.menu.addMenuItem(item);
        }
        if (this._cells.some(cell => !cell.id.startsWith('widget:') && !Number.isFinite(cell.metric?.value)))
            this._menu.addMenuItem(new PopupMenu.PopupMenuItem(
                tr('Some sensors are not exposed by this system or VM', 'Niektóre czujniki nie są udostępniane przez system lub VM'),
                {reactive: false}));
        for (const [title, key, options] of [
            [tr('Refresh interval', 'Odświeżanie'), 'monitor-interval', [1, 2, 5, 10]],
            [tr('History length', 'Długość historii'), 'monitor-history', [30, 60, 120, 300]],
        ]) {
            const submenu = new PopupMenu.PopupSubMenuMenuItem(title); this._menu.addMenuItem(submenu);
            for (const seconds of options)
                action(submenu.menu, `${seconds === this._settings.get_int(key) ? '✓ ' : ''}${seconds} s`, () => this._settings.set_int(key, seconds));
        }
        for (const [label, key] of [[tr('Hide unavailable sensors', 'Ukryj niedostępne czujniki'), 'monitor-hide-unavailable'], [tr('Show graphs', 'Pokaż wykresy'), 'monitor-graphs'], ['Fahrenheit (°F)', 'monitor-fahrenheit']]) {
            const item = new PopupMenu.PopupSwitchMenuItem(label, this._settings.get_boolean(key));
            item.connect('toggled', (_item, state) => this._settings.set_boolean(key, state));
            this._menu.addMenuItem(item);
        }
        action(this._menu, tr('Settings / manual CPU TDP…', 'Ustawienia / ręczne TDP CPU…'), () => this._extension.openPreferences());
        action(this._menu, tr('Restore default monitors', 'Przywróć domyślne wskaźniki'), () => save(defaultMetrics));
        this._menu.open();
    }

    _menuStyle() {
        return `max-height: 650px; background-color: transparent; border: none; box-shadow: none; color: ${this._light ? '#211b2b' : '#f4f0fa'};`;
    }

    _addWidget(id, actor, row) {
        if (id === 'widget:network') actor.width = 180 * St.ThemeContext.get_for_stage(global.stage).scale_factor;
        const box = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL});
        const top = new St.BoxLayout({style_class: 'infinity-widget-top'});
        const icon = new St.Icon({style_class: 'infinity-widget-icon'});
        const value = new St.Label({style_class: 'infinity-monitor-value'});
        const label = new St.Label({style_class: 'infinity-monitor-label'});
        top.add_child(icon); top.add_child(value);
        box.add_child(top); box.add_child(label); actor.set_child(box); row.add_child(actor);
        const cell = {id, actor, value, label, icon};
        this._cells.push(cell);
        actor.connect('clicked', () => this._openMenu(this._cells.indexOf(cell)));
        this._enableDrag(cell);
    }

    _updateWidgets() {
        if (!this._widgets) return;
        if (this.actor.visible) this._widgets.refreshNetwork();
        for (const cell of this._cells) {
            if (!cell.id.startsWith('widget:')) continue;
            const widget = this._widgets.read(cell.id);
            cell.metric = {...widget, group: tr('Widgets', 'Widgety')};
            cell.value.text = widget.text;
            cell.label.text = `${widget.label} · ${widget.detail}`.toUpperCase();
            cell.icon.icon_name = widget.icon;
            cell.actor.accessible_name = `${widget.label}: ${widget.text}. ${widget.detail}`;
            if (cell.id === 'widget:weather' && this.actor.visible) this._widgets.refreshWeather();
        }
    }

    _enableDrag(cell) {
        cell.actor._delegate = {
            monitor: this, id: cell.id,
            getDragActor: () => new Clutter.Clone({source: cell.actor, width: cell.actor.width, height: cell.actor.height}),
            getDragActorSource: () => cell.actor,
            handleDragOver: source => source?.monitor === this ? DND.DragMotionResult.MOVE_DROP : DND.DragMotionResult.CONTINUE,
            acceptDrop: (source, _actor, x) => {
                if (source?.monitor !== this) return false;
                const next = dropMetric(this._settings.get_strv('monitor-metrics'), source.id, cell.id, x > cell.actor.width / 2);
                // DND must finish with the old actors before rebuilding the strip.
                this._dropIdle = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
                    this._dropIdle = 0;
                    if (this._alive) this._settings.set_strv('monitor-metrics', uniqueMetrics(next, this._metrics));
                    return GLib.SOURCE_REMOVE;
                });
                return true;
            },
        };
        const drag = DND.makeDraggable(cell.actor, {restoreOnSuccess: false, dragActorOpacity: 200});
        drag.connect('drag-begin', () => { this._dragging = true; this._menu.close(); });
        drag.connect('drag-end', () => { this._dragging = false; });
    }

    destroy() {
        this._alive = false;
        this._widgets.destroy();
        if (this._widgetTimer) GLib.Source.remove(this._widgetTimer);
        if (this._dropIdle) GLib.Source.remove(this._dropIdle);
        this._colorSettings.disconnect(this._colorId);
        this._unfollow();
        if (this._timer) GLib.Source.remove(this._timer);
        if (this._timeout) GLib.Source.remove(this._timeout);
        this._timeout = 0;
        this._process?.force_exit();
        this._settings.disconnect(this._settingsId);
        this._menu.destroy();
        Main.layoutManager.removeChrome(this._menuAnchor);
        this._menuAnchor.destroy();
        Main.layoutManager.removeChrome(this.actor);
        this.actor.destroy();
    }
}
