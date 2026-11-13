import assert from 'node:assert/strict';
import test from 'node:test';
import {appendSample, defaultMetrics, formatMetric, moveMetric, resolveMetric} from
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
        add_child() {} set_child() {} connect() {} destroy_all_children() {}
    }
    const prototype = vm.runInNewContext(`${source}\nHardwareMonitor.prototype`, {
        GLib: {get_language_names: () => ['en']}, global: {stage: {}},
        Clutter: {Orientation: {VERTICAL: 1}, ActorAlign: {START: 0, FILL: 1}},
        St: {BoxLayout: Actor, ScrollView: Actor, Button: Actor, Label: Actor, DrawingArea: Actor,
            PolicyType: {AUTOMATIC: 1, NEVER: 2}, ThemeContext: {get_for_stage: () => ({scale_factor: 1})}},
    });
    const monitor = Object.create(prototype);
    monitor.actor = new Actor();
    monitor._settings = {get_strv: () => ['auto:cpu-temp']};
    monitor._update = () => {};
    monitor._rebuild();
    assert.equal(monitor._cells.length, 1);
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
