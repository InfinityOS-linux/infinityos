import assert from 'node:assert/strict';
import test from 'node:test';
import {appendSample, defaultMetrics, formatMetric, moveMetric, resolveMetric, uniqueMetrics, toggleMetric, dropMetric, Stopwatch, Countdown, networkTotals, networkRate} from
    '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/monitor-model.mjs';

test('selected GPU identity is preserved across enumeration and disconnection', () => {
    const a = {id: 'nvidia:GPU-a:temp', label: 'GPU Temp A', value: 54, unit: '°C'};
    const b = {id: 'nvidia:GPU-b:temp', label: 'GPU Temp B', value: 48, unit: '°C'};
    assert.equal(resolveMetric(a.id, [b, a]), a);
    assert.equal(resolveMetric(a.id, [b]).value, null);
    assert.equal(formatMetric(resolveMetric(a.id, [b])), 'N/A');
    assert.equal(resolveMetric('auto:gpu-temp', [b, a]), b);
});

test('temperatures, memory, zero and unknown values format without inventing data', () => {
    assert.equal(formatMetric({value: 0, unit: '°C'}, true), '32 °F');
    assert.equal(formatMetric({value: 12, maximum: 32, unit: 'GiB'}), '12.0 / 32.0 GiB');
    assert.equal(formatMetric({value: null, unit: 'W'}), 'N/A');
    assert.equal(formatMetric({value: NaN, unit: 'W'}), 'N/A');
    assert.equal(resolveMetric('cpu:tdp', [], 105).value, 105);
    assert.equal(resolveMetric('cpu:tdp', [], 0).value, null);
});

test('history is bounded and missing readings create gaps', () => {
    assert.deepEqual(appendSample([1, 2, 3], null, 3), [2, 3, null]);
    assert.deepEqual(appendSample([1, null], 0, 3), [1, null, 0]);
});

test('reordering preserves sensor selections and handles first/last boundaries', () => {
    const ids = ['a', 'b', 'c'];
    assert.deepEqual(moveMetric(ids, 1, -1), ['b', 'a', 'c']);
    assert.deepEqual(moveMetric(ids, 0, -1), ids);
    assert.deepEqual(moveMetric(ids, 2, 1), ids);
    assert.deepEqual(ids, ['a', 'b', 'c']);
    assert.ok(defaultMetrics.includes('memory:used'));
});

test('monitor cells use GNOME 51 BoxLayout orientation', async () => {
    const {readFileSync} = await import('node:fs');
    const vm = await import('node:vm');
    const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/hardware-monitor.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export class', 'class');
    class Actor {
        constructor(properties = {}) {
            if ('vertical' in properties) throw Error('No property vertical on StBoxLayout');
            Object.assign(this, properties);
        }
        add_child(child) { (this.children ??= []).push(child); } set_child(child) { this.child = child; } connect() {} destroy_all_children() {}
    }
    const prototype = vm.runInNewContext(`${source}\nHardwareMonitor.prototype`, {
        GLib: {get_language_names: () => ['en']}, global: {stage: {}},
        DND: {makeDraggable: () => ({connect() {}})},
        Clutter: {Orientation: {VERTICAL: 1}, ActorAlign: {START: 0, FILL: 1}},
        St: {BoxLayout: Actor, ScrollView: Actor, Button: Actor, Label: Actor, DrawingArea: Actor,
            PolicyType: {AUTOMATIC: 1, NEVER: 2, EXTERNAL: 3}, ThemeContext: {get_for_stage: () => ({scale_factor: 1})}},
    });
    const monitor = Object.create(prototype);
    monitor.actor = new Actor();
    monitor._settings = {get_strv: () => ['auto:cpu-temp']};
    monitor._update = () => {};
    monitor._rebuild();
    assert.equal(monitor._cells.length, 1);
    assert.equal(monitor.actor.children[0].hscrollbar_policy, 3);
    assert.equal(monitor._cells[0].actor.child.children.at(-1), monitor._cells[0].label);
    assert.equal(monitor._cells[0].label.y_expand, false);
});

test('opening a Shell menu keeps terminal visible; switching apps still hides it', async () => {
    const {readFileSync} = await import('node:fs');
    const vm = await import('node:vm');
    const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8');
    const start = source.indexOf('() => {', source.indexOf('this._focusId ='));
    const end = source.indexOf('\n        });', start);
    const global = {display: {focus_window: null}};
    const callback = vm.runInNewContext(`(function () ${source.slice(start + 6, end)}\n})`, {global});
    let hidden = 0;
    const window = {minimized: false};
    const controller = {_hardware: {menuOpen: false}, _settings: {get_boolean: () => false},
        _findWindow: () => window, _hide() {hidden++;}};
    callback.call(controller);
    assert.equal(hidden, 0);
    global.display.focus_window = window;
    callback.call(controller);
    assert.equal(hidden, 0);
    global.display.focus_window = {};
    callback.call(controller);
    assert.equal(hidden, 1);
});

test('monitor hides missing readings without forgetting selections and restores recovered sensors', async () => {
    const {readFileSync} = await import('node:fs');
    const vm = await import('node:vm');
    const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/hardware-monitor.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export class', 'class');
    const prototype = vm.runInNewContext(`${source}\nHardwareMonitor.prototype`, {
        GLib: {get_language_names: () => ['en']}, resolveMetric, formatMetric, appendSample,
    });
    let hide = true;
    const monitor = Object.create(prototype);
    monitor._settings = {get_int: () => 0, get_boolean: key => key === 'monitor-hide-unavailable' && hide};
    monitor._metrics = [];
    monitor._emptyButton = {};
    monitor._cells = [{id: 'cpu:clock', actor: {}, value: {}, label: {}, graph: {queue_repaint() {}}}];
    monitor._update(false);
    assert.equal(monitor._cells[0].actor.visible, false);
    assert.equal(monitor._emptyButton.visible, true);
    hide = false;
    monitor._update(false);
    assert.equal(monitor._cells[0].actor.visible, true);
    hide = true;
    monitor._metrics = [{id: 'cpu:clock', label: 'CPU Clock', value: 2, unit: 'GHz'}];
    monitor._update(false);
    assert.equal(monitor._cells[0].actor.visible, true);
    assert.equal(monitor._emptyButton.visible, false);
});

test('sensor menu follows click coordinates and marks displayed, hidden and unselected sources', async () => {
    const {readFileSync} = await import('node:fs');
    const vm = await import('node:vm');
    const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/hardware-monitor.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export class', 'class');
    const items = [];
    class Item {
        constructor(label) { this.label = label; this.menu = {addMenuItem() {}}; items.push(this); }
        connect() {} setOrnament(value) { this.ornament = value; }
    }
    const prototype = vm.runInNewContext(`${source}\nHardwareMonitor.prototype`, {
        GLib: {get_language_names: () => ['en']}, global: {get_pointer: () => [900, 120, 0]},
        PopupMenu: {PopupMenuItem: Item, PopupSubMenuMenuItem: Item, PopupSeparatorMenuItem: Item,
            PopupSwitchMenuItem: Item, Ornament: {CHECK: 'check', DOT: 'dot', NONE: 'none'}},
        resolveMetric, formatMetric, uniqueMetrics, toggleMetric, widgetChoices: [],
    });
    const monitor = Object.create(prototype);
    const ram = {id: 'memory:used', label: 'RAM', group: 'System', value: 2, unit: 'GiB'};
    const gpu = {id: 'nvidia:GPU-a:temp', label: 'GPU Temp', group: 'GPU', value: null, unit: '°C'};
    const disk = {id: 'disk:/', label: 'Disk', group: 'Disks', value: 6, unit: 'GiB'};
    monitor._metrics = [ram, gpu, disk];
    monitor._cells = [{id: 'memory:used', metric: ram, actor: {visible: true}},
        {id: 'auto:gpu-temp', metric: gpu, actor: {visible: false}}];
    monitor._settings = {get_strv: () => ['memory:used', 'auto:gpu-temp'], get_int: () => 0, get_boolean: () => true};
    monitor._menuAnchor = {set_position(x, y) { this.position = [x, y]; }};
    monitor._menu = {close() {}, removeAll() {}, addMenuItem() {}, open() {this.opened = true;}};
    monitor._openMenu(-1, [300, 80]);
    assert.deepEqual(monitor._menuAnchor.position, [300, 80]);
    assert.equal(items.find(item => item.label.startsWith('RAM (')).ornament, 'check');
    const selectedGpu = items.find(item => item.label.startsWith('GPU Temp ('));
    assert.equal(selectedGpu.ornament, 'dot');
    assert.ok(selectedGpu.label.endsWith('hidden'));
    assert.equal(items.find(item => item.label.startsWith('Disk (')).ornament, 'none');
    assert.equal(monitor._menu.opened, true);
    monitor._openMenu(-1);
    assert.deepEqual(monitor._menuAnchor.position, [900, 120]);
});

test('selection toggles off aliases and legacy duplicates without losing other devices', () => {
    const metrics = [{id: 'gpu:a', label: 'GPU Temp A'}, {id: 'gpu:b', label: 'GPU Temp B'}];
    assert.deepEqual(toggleMetric(['auto:gpu-temp', 'gpu:a', 'gpu:b'], 'gpu:a', metrics), ['gpu:b']);
    assert.deepEqual(toggleMetric(['gpu:b'], 'gpu:a', metrics), ['gpu:b', 'gpu:a']);
    assert.deepEqual(uniqueMetrics(['auto:gpu-temp', 'gpu:a', 'gpu:b', 'gpu:b'], metrics), ['auto:gpu-temp', 'gpu:b']);
    assert.deepEqual(toggleMetric(['widget:weather'], 'widget:weather', []), []);
});

test('drop inserts before or after target, preserving hidden sensors and widgets', () => {
    const ids = ['cpu', 'hidden', 'widget:weather', 'ram'];
    assert.deepEqual(dropMetric(ids, 'ram', 'cpu', false), ['ram', 'cpu', 'hidden', 'widget:weather']);
    assert.deepEqual(dropMetric(ids, 'cpu', 'widget:weather', true), ['hidden', 'widget:weather', 'cpu', 'ram']);
    assert.deepEqual(dropMetric(ids, 'cpu', 'cpu', true), ids);
    assert.deepEqual(dropMetric(ids, 'missing', 'ram', true), ids);
});

test('stopwatch keeps monotonic elapsed time across hidden intervals, pause and reset', () => {
    let now = 0;
    const watch = new Stopwatch(() => now);
    watch.toggle(); now = 3661;
    assert.equal(watch.text, '01:01:01');
    watch.toggle(); now = 4000;
    assert.equal(watch.text, '01:01:01');
    watch.toggle(); now += 2;
    assert.equal(watch.text, '01:01:03');
    watch.reset();
    assert.equal(watch.text, '00:00:00');
    assert.equal(watch.running, false);
});

test('weather shares Shell settings, handles removal and throttles refreshes', async () => {
    const {readFileSync} = await import('node:fs');
    const vm = await import('node:vm');
    let now = 0, requests = 0, disconnected = false; const alarms = new Map(); const notices = []; let nextAlarm = 0;
    const client = {available: true, hasLocation: true, loading: false,
        connect: () => 12, disconnect(id) { disconnected = id === 12; }, update() { requests++; },
        info: {is_valid: () => true, get_temp: () => '72 °F', get_symbolic_icon_name: () => 'weather-clear-symbolic',
            get_location: () => ({get_name: () => 'Warsaw'})}};
    const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/monitor-widgets.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replaceAll('export ', '');
    const Widgets = vm.runInNewContext(`${source}\nMonitorWidgets`, {Stopwatch, Countdown, networkTotals, networkRate,
        Gio: {Cancellable: class { cancel() {} }},
        GLib: {get_language_names: () => ['en'], get_monotonic_time: () => now * 1000000,
            timeout_add_seconds(_priority, _seconds, callback) { alarms.set(++nextAlarm, callback); return nextAlarm; },
            Source: {remove(id) { alarms.delete(id); }}},
        Main: {notify: (...args) => notices.push(args), panel: {statusArea: {dateMenu: {_weatherItem: {_weatherClient: client}}}}}});
    const widgets = new Widgets(() => {});
    assert.equal(widgets.read('widget:weather').text, '72 °F');
    assert.equal(widgets.read('widget:weather').detail, 'Warsaw');
    widgets.refreshWeather(); widgets.refreshWeather();
    assert.equal(requests, 1);
    now = 600; widgets.refreshWeather(); assert.equal(requests, 2);
    client.hasLocation = false;
    assert.match(widgets.read('widget:weather').detail, /Choose a location/);
    client.available = false;
    assert.match(widgets.read('widget:weather').detail, /not installed/);
    widgets.refreshWeather(); assert.equal(requests, 2);
    widgets.select(['widget:timer']); widgets.toggleTimer('widget:timer');
    assert.equal(alarms.size, 1);
    now += 300; alarms.get(nextAlarm)();
    assert.equal(notices.length, 1); assert.equal(widgets.timers['widget:timer'].running, false);
    widgets._battery = {get_cached_property: name => ({deepUnpack: () => ({IsPresent: true, Percentage: 65,
        State: 2, TimeToEmpty: 5400, IconName: 'battery-good-symbolic'})[name]})};
    assert.equal(widgets.read('widget:battery').text, '65%');
    assert.equal(widgets.read('widget:battery').detail, '1h 30m');
    widgets.destroy(); assert.equal(disconnected, true);
});

test('countdown pauses and Pomodoro advances through focus and long breaks', () => {
    let now = 0;
    const timer = new Countdown(() => now);
    timer.reset(1); timer.toggle(); now = 30; timer.toggle(); now = 300;
    assert.equal(timer.text, '0:30');
    timer.toggle(); now += 30;
    assert.equal(timer.finish(), 'done'); assert.equal(timer.running, false);
    assert.equal(timer.finish(), null);
    const pomodoro = new Countdown(() => now, true);
    pomodoro.toggle();
    for (let round = 1; round <= 4; round++) {
        now += 25 * 60; assert.equal(pomodoro.finish(), 'break');
        const duration = round === 4 ? 15 * 60 : 5 * 60;
        assert.equal(pomodoro.seconds, duration);
        now += duration; assert.equal(pomodoro.finish(), 'work');
    }
    pomodoro.reset(); assert.equal(pomodoro.running, false); assert.equal(pomodoro.text, '25:00');
});

test('network rates exclude loopback and handle counter resets', () => {
    const line = (name, rx, tx) => `${name}: ${rx} 0 0 0 0 0 0 0 ${tx} 0 0 0 0 0 0 0`;
    const totals = networkTotals([line('lo', 1000, 1000), line('eth0', 100, 200), line('wlan0', 10, 20)].join('\n'));
    assert.deepEqual(totals, {rx: 110, tx: 220});
    assert.deepEqual(networkRate(totals, {rx: 150, tx: 300}, 2), {rx: 20, tx: 40});
    assert.deepEqual(networkRate(totals, {rx: 0, tx: 0}, 1), {rx: 0, tx: 0});
    assert.deepEqual(networkRate(null, totals, 1), {rx: 0, tx: 0});
});

test('drag commits only after DND releases actors, ignores foreign sources', async () => {
    const {readFileSync} = await import('node:fs');
    const vm = await import('node:vm');
    const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/hardware-monitor.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export class', 'class');
    let idle, saved; const signals = {};
    const prototype = vm.runInNewContext(`${source}\nHardwareMonitor.prototype`, {
        GLib: {get_language_names: () => ['en'], idle_add(_priority, callback) { idle = callback; return 1; }},
        DND: {makeDraggable(_actor, options) { assert.equal(options.restoreOnSuccess, false); return {connect(name, cb) { signals[name] = cb; }}; }},
        dropMetric, uniqueMetrics,
    });
    const monitor = Object.assign(Object.create(prototype), {_alive: true, _metrics: [],
        _settings: {get_strv: () => ['a', 'b'], set_strv(_key, value) { saved = value; }}, _menu: {close() {}}});
    const cell = {id: 'a', actor: {width: 100}};
    monitor._enableDrag(cell);
    assert.equal(cell.actor._delegate.acceptDrop({monitor: {}}, null, 0), false);
    signals['drag-begin'](); assert.equal(monitor._dragging, true);
    assert.equal(cell.actor._delegate.acceptDrop({monitor, id: 'b'}, null, 0), true);
    assert.equal(saved, undefined);
    signals['drag-end'](); idle();
    assert.deepEqual(saved, ['b', 'a']); assert.equal(monitor._dragging, false);
});
