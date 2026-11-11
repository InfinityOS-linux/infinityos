import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-updater/root/usr/share/gnome-shell/extensions/infinity-updater@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');

for (const [name, state, total] of [
    ['failed check stays hidden', {errors: ['offline'], updates: []}, 0],
    ['partial results keep their count', {errors: ['firmware'], updates: [{}, {}]}, 2],
    ['release remains visible', {updates: [], release: {version: '2.1'}}, 1],
]) {
    test(name, () => {
        const indicator = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
            Extension: class {}, TextDecoder,
            GLib: {file_get_contents: () => [true, Buffer.from(JSON.stringify(state))]},
            Main: {notify() {}},
        });
        indicator._badge = {};
        indicator._indicator = {};
        indicator._icon = {icon_name: 'infinity-update-available-symbolic'};
        indicator._refresh();
        assert.equal(indicator._indicator.visible, total > 0);
        assert.equal(indicator._badge.text, String(total));
        assert.equal(indicator._icon.icon_name, 'infinity-update-available-symbolic');
    });
}

for (const [name, status, checkedAt, remaining] of [
    ['successful offline install hides old RPM and release counts', 'success', '2026-11-09T19:00:00Z', 0],
    ['failed offline install keeps pending updates', 'failed', '2026-11-09T19:00:00Z', 3],
    ['new checks remain visible after an older successful install', 'success', '2026-11-09T21:00:00Z', 3],
]) {
    test(name, () => {
        const state = {checked_at: checkedAt, updates: [{kind: 'RPM'}, {kind: 'RPM'}], release: {version: '2.1'}};
        const resultPath = '/var/lib/infinityos/offline-update-result.json';
        const indicator = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
            Extension: class {}, TextDecoder,
            GLib: {file_get_contents: path => [true, Buffer.from(JSON.stringify(path === resultPath ? {status} : state))]},
            Gio: {FileQueryInfoFlags: {NONE: 0}, File: {new_for_path: () => ({
                query_info: () => ({get_attribute_uint64: () => Date.parse('2026-11-09T20:00:00Z') / 1000}),
            })}},
            Main: {notify() {}},
        });
        indicator._badge = {};
        indicator._indicator = {};
        indicator._refresh();
        assert.equal(indicator._badge.text, String(remaining));
        assert.equal(indicator._indicator.visible, remaining > 0);
        state.updates.push({kind: 'Flatpak user'});
        indicator._refresh();
        assert.equal(indicator._badge.text, String(remaining + 1));
    });
}

function drawer(area) {
    const calls = [];
    const actor = {remove_all_transitions() {}, ease(options) { calls.push(options); }};
    const window = {
        get_monitor: () => 1,
        unmaximize() {},
        move_resize_frame: (...args) => calls.push(args),
        get_compositor_private: () => actor,
        get_frame_rect: () => ({width: Math.min(460, area.width)}),
        get_buffer_rect: () => ({x: area.x + area.width - Math.min(460, area.width), y: area.y}),
        activate() {}, minimize: () => calls.push('minimized'),
    };
    const extension = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
        Extension: class {}, Meta: {MaximizeFlags: {BOTH: 3}},
        St: {Settings: {get: () => ({enable_animations: true})}},
        Clutter: {AnimationMode: {EASE_OUT_CUBIC: 1, EASE_IN_CUBIC: 2}},
        global: {get_current_time: () => 1},
        Main: {layoutManager: {getWorkAreaForMonitor: () => area}, wm: {skipNextEffect() {}}},
    });
    return {extension, window, actor, calls};
}

test('drawer opens from the right within the selected monitor work area', () => {
    const {extension, window, actor, calls} = drawer({x: -1280, y: 32, width: 1280, height: 688});
    extension._showDrawer(window);
    assert.deepEqual(calls[0], [false, -460, 32, 460, 688]);
    assert.equal(actor.translation_x, 460);
    assert.equal(calls[1].translation_x, 0);
    assert.equal(calls[1].duration, 280);
});

test('drawer fits narrow screens and minimizes only after sliding out', () => {
    const {extension, window, actor, calls} = drawer({x: 0, y: 30, width: 360, height: 610});
    extension._placeDrawer(window);
    assert.deepEqual(calls[0], [false, 0, 30, 360, 610]);
    extension._hideDrawer(window);
    assert.equal(calls[1].translation_x, 360);
    assert.equal(calls.includes('minimized'), false);
    calls[1].onComplete();
    assert.equal(calls[2], 'minimized');
    assert.equal(actor.translation_x, 0);
});

for (const [label, x, y, sourceActor, minimized, hide] of [
    ['desktop', 100, 100, null, false, true],
    ['top bar', 900, 10, null, false, true],
    ['another monitor', 1500, 400, null, false, true],
    ['inside drawer', 900, 400, null, false, false],
    ['own indicator', 900, 10, 'indicator', false, false],
    ['already hidden', 100, 100, null, true, false],
]) {
    test(`outside click: ${label}`, () => {
        const window = {minimized, get_frame_rect: () => ({x: 820, y: 30, width: 460, height: 690})};
        let hidden = false;
        const extension = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
            Extension: class {},
            Clutter: {EventType: {BUTTON_PRESS: 1, TOUCH_BEGIN: 2}, EVENT_PROPAGATE: 0},
            global: {get_window_actors: () => [{meta_window: window}]},
        });
        extension._isUpdater = w => w === window;
        extension._indicator = {contains: actor => actor === 'indicator'};
        extension._hideDrawer = () => {hidden = true;};
        const result = extension._onCapturedEvent({type: () => 1, get_source: () => sourceActor, get_coords: () => [x, y]});
        assert.equal(result, 0, 'outside clicks still reach the target');
        assert.equal(hidden, hide);
    });
}


test('opening restores actor position after interrupting the GNOME restore effect', () => {
    const {extension, window, actor} = drawer({x: 0, y: 32, width: 1280, height: 688});
    actor.x = 0;
    actor.y = 0;
    extension._showDrawer(window);
    assert.equal(actor.x, 820);
    assert.equal(actor.y, 32);
});

test('rapid toggle reverses closing and repeated outside clicks do not restart it', () => {
    const {extension, window, actor, calls} = drawer({x: 0, y: 32, width: 1280, height: 688});
    extension._hideDrawer(window);
    const closing = calls.at(-1);
    extension._hideDrawer(window);
    assert.equal(calls.at(-1), closing);
    actor.translation_x = 120;
    extension._toggleDrawer(window);
    assert.equal(actor.translation_x, 120, 'reverse from the current position');
    assert.equal(calls.at(-1).translation_x, 0);
    closing.onComplete();
    assert.equal(calls.includes('minimized'), false, 'an obsolete completion must not hide the reopened drawer');
    extension._toggleDrawer(window);
    calls.at(-1).onComplete();
    assert.equal(calls.includes('minimized'), true);
});

test('tray restores the existing minimized window without launching another process', () => {
    const {extension, window} = drawer({x: 0, y: 32, width: 1280, height: 688});
    window.minimized = true;
    let activated = 0;
    window.activate = () => activated++;
    extension._toggleDrawer(window);
    assert.equal(activated, 1);
});
