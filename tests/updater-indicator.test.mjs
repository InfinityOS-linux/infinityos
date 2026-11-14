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

function drawer(area, deferred = false) {
    const redraws = new Map();
    const calls = [];
    const timers = new Map();
    const signals = new Map();
    let nextId = 1;
    const actor = {remove_all_transitions() {}, ease(options) { calls.push(options); }};
    const window = {
        get_monitor: () => 1,
        unmaximize() {},
        move_resize_frame: (...args) => calls.push(args),
        get_compositor_private: () => actor,
        get_frame_rect: () => ({x: area.x + area.width - Math.min(460, area.width), y: area.y, width: Math.min(460, area.width), height: area.height}),
        get_buffer_rect: () => ({x: area.x + area.width - Math.min(460, area.width), y: area.y, width: Math.min(460, area.width), height: area.height}),
        activate() { this.minimized = false; },
        minimize() { this.minimized = true; calls.push('minimized'); },
        delete: () => calls.push('closed'),
        connect(name, callback) { const id = nextId++; signals.set(id, {name, callback}); return id; },
        disconnect(id) { signals.delete(id); },
    };
    const extension = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
        Extension: class {}, Meta: {MaximizeFlags: {BOTH: 3}, LaterType: {BEFORE_REDRAW: 1}},
        GLib: {PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false,
            timeout_add(_priority, delay, callback) { const id = nextId++; timers.set(id, {delay, callback}); return id; },
            Source: {remove: id => timers.delete(id)}},
        St: {Settings: {get: () => ({enable_animations: true})}},
        Clutter: {AnimationMode: {EASE_OUT_CUBIC: 1, EASE_IN_CUBIC: 2, EASE_OUT_ELASTIC: 3}},
        global: {get_current_time: () => 1, compositor: {get_laters: () => ({
            add(_type, callback) { const id = nextId++; if (deferred) redraws.set(id, callback); else callback(); return id; },
            remove(id) { redraws.delete(id); },
        })}},
        Main: {layoutManager: {getWorkAreaForMonitor: () => area}, wm: {skipNextEffect() {}}},
    });
    return {extension, window, actor, calls, timers, signals, redraws};
}

test('drawer opens from the right within the selected monitor work area', () => {
    const {extension, window, actor, calls} = drawer({x: -1280, y: 32, width: 1280, height: 688});
    extension._showDrawer(window);
    assert.deepEqual(calls[0], [false, -460, 32, 460, 688]);
    assert.equal(actor.translation_x, 476);
    assert.equal(calls[1].translation_x, -24);
    assert.equal(calls[1].duration, 420);
});

test('drawer fits narrow screens and minimizes only after sliding out', () => {
    const {extension, window, actor, calls} = drawer({x: 0, y: 30, width: 360, height: 610});
    extension._placeDrawer(window);
    assert.deepEqual(calls[0], [false, 0, 30, 360, 610]);
    extension._hideDrawer(window);
    assert.equal(calls[1].translation_x, 376);
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
            global: {stage: {get_event_actor: () => sourceActor}, get_window_actors: () => [{meta_window: window}]},
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
    assert.equal(calls.at(-1).translation_x, -24);
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

for (const [label, target, hidden] of [
    ['another Wayland app', 'other', true],
    ['desktop window', 'desktop', true],
    ['updater itself', 'self', false],
    ['updater dialog', 'dialog', false],
    ['nested updater dialog', 'nested', false],
    ['shell focus', 'shell', false],
]) {
    test(`focus dismissal: ${label}`, () => {
        const window = {minimized: false};
        const dialog = {get_transient_for: () => window};
        const focus = {self: window, dialog, nested: {get_transient_for: () => dialog},
            other: {get_transient_for: () => null}, desktop: {get_transient_for: () => null}, shell: null}[target];
        let dismissed = false;
        const extension = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
            Extension: class {},
            global: {display: {focus_window: focus}, get_window_actors: () => [{meta_window: window}]},
        });
        extension._isUpdater = candidate => candidate === window;
        extension._hideDrawer = () => {dismissed = true;};
        extension._onFocusChanged();
        assert.equal(dismissed, hidden);
    });
}


test('hidden drawer closes after five seconds, not during its slide animation', () => {
    const {extension, window, calls, timers, signals} = drawer({x: 0, y: 32, width: 1280, height: 688});
    extension._hideDrawer(window);
    assert.equal(timers.size, 0);
    calls.at(-1).onComplete();
    const timer = [...timers.values()][0];
    assert.equal(timer.delay, 5000);
    assert.equal(calls.includes('closed'), false);
    timer.callback();
    assert.equal(calls.at(-1), 'closed');
    assert.equal(signals.size, 0);
});

for (const reason of ['reopen', 'unmanaged']) {
    test(`pending close is cancelled on ${reason}`, () => {
        const {extension, window, calls, timers, signals} = drawer({x: 0, y: 32, width: 1280, height: 688});
        extension._hideDrawer(window);
        calls.at(-1).onComplete();
        if (reason === 'reopen')
            extension._showDrawer(window);
        else
            [...signals.values()].find(signal => signal.name === 'unmanaged').callback();
        assert.equal(timers.size, 0);
        assert.equal(signals.size, 0);
        assert.equal(calls.includes('closed'), false);
    });
}

for (const [appId, id, action, target, expected] of [
    ['org.gnome.Software', 'offline-updates', 'app.set-mode', 'updated', true],
    ['org.gnome.Software', 'updates-installed', 'app.set-mode', 'updated', true],
    ['org.gnome.Software', 'offline-updates', 'app.show-offline-update-error', null, false],
    ['org.gnome.Software', 'offline-updates', 'app.set-mode', 'updates', false],
    ['org.gnome.Software', 'updates-available', 'app.set-mode', 'updates', false],
    ['org.example.Other', 'updates-installed', 'app.set-mode', 'updated', false],
]) {
    for (const locale of ['pl_PL.UTF-8', 'en_US.UTF-8']) {
        test(`completion notification ${appId}/${id}/${action}/${target} in ${locale}`, () => {
            let opened = false;
            let dismissed = false;
            const extension = vm.runInNewContext(`${source}\nnew InfinityUpdater()`, {
                Extension: class {},
                GLib: {get_language_names: () => [locale]},
                MessageTray: {Notification: class { activate() { dismissed = true; } }},
            });
            extension._simplifiedNotifications = new WeakSet();
            extension._notificationOverrides = {overrideMethod(object, name, factory) {
                object[name] = factory(object[name]);
            }};
            const notification = {
                source: {_appId: appId}, id, title: 'Original', body: 'Details', actions: ['Review'],
                serialize: () => ({deepUnpack: () => ({
                    'default-action': {unpack: () => action},
                    'default-action-target': {unpack: () => target},
                })}),
                set(values) { Object.assign(this, values); },
                clearActions() { this.actions = []; },
                activate() { opened = true; },
            };
            extension._simplifyInstalledNotification(notification);
            extension._simplifyInstalledNotification(notification);
            notification.activate();
            assert.equal(opened, !expected);
            assert.equal(dismissed, expected);
            assert.deepEqual(notification.actions, expected ? [] : ['Review']);
            assert.equal(notification.body, expected ? '' : 'Details');
            assert.equal(notification.title, expected
                ? locale.startsWith('pl') ? 'Aktualizacje zostały zainstalowane.' : 'Updates installed.'
                : 'Original');
        });
    }
}


test('first map stays invisible until placement and restore handlers finish', () => {
    const {extension, window, actor, calls, redraws} = drawer({x: 0, y: 32, width: 1280, height: 688}, true);
    extension._showDrawer(window);
    assert.equal(actor.opacity, 0);
    assert.equal(calls.length, 1);
    const callback = [...redraws.values()][0];
    callback();
    assert.equal(actor.opacity, 255);
    assert.equal(actor.translation_x, 476);
    assert.equal(calls[1].translation_x, -24);
    assert.equal(extension._openingWindows.size, 0);
});

test('closing before the first redraw cancels the delayed opening', () => {
    const {extension, window, calls, redraws} = drawer({x: 0, y: 32, width: 1280, height: 688}, true);
    extension._showDrawer(window);
    const obsolete = [...redraws.values()][0];
    extension._hideDrawer(window);
    assert.equal(redraws.size, 0);
    const count = calls.length;
    obsolete();
    assert.equal(calls.length, count);
});


test('panel surface is shared while open and restored after closing', () => {
    const {extension, window, calls} = drawer({x: 0, y: 32, width: 1280, height: 688});
    const surface = {visible: false, show() { this.visible = true; }, hide() { this.visible = false; }};
    extension._panelSurface = surface;
    extension._showDrawer(window);
    assert.equal(surface.visible, true);
    extension._hideDrawer(window);
    assert.equal(surface.visible, true);
    calls.at(-1).onComplete();
    assert.equal(surface.visible, false);
});


test('Wayland initial small surface stays hidden until its resize is acknowledged', () => {
    const {extension, window, actor, calls, redraws} = drawer({x: 0, y: 32, width: 1280, height: 688}, true);
    const configured = window.get_frame_rect;
    window.get_frame_rect = () => ({x: 0, y: 0, width: 200, height: 100});
    extension._showDrawer(window);
    const redraw = [...redraws.values()][0];
    assert.equal(redraw(), true);
    assert.equal(actor.opacity, 0);
    assert.equal(calls.length, 1);
    window.get_frame_rect = configured;
    assert.equal(redraw(), false);
    assert.equal(actor.opacity, 255);
    const entry = calls.at(-1);
    assert.equal(entry.translation_x, -24);
    entry.onComplete();
    assert.equal(calls.at(-1).translation_x, 0);
    assert.equal(calls.at(-1).mode, 3);
    assert.equal(calls.at(-1).duration, 460);
});
