import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');
function fixture(open = false) {
    const events = [];
    const actor = {remove_all_transitions() {}, translation_y: -20};
    const window = {minimized: !open, get_compositor_private: () => actor,
        minimize() { events.push('minimize'); this.minimized = true; }};
    const overview = {visible: false, _overview: {controls: {}},
        show() {events.push('overview'); this.visible = true;},
        hide() {this.visible = false;}};
    const controller = vm.runInNewContext(`${source}\nnew InfinityTerminal()`, {
        Extension: class {}, Main: {actionMode: 1, overview, wm: {skipNextEffect() {}}},
        Shell: {ActionMode: {NORMAL: 1, OVERVIEW: 2}},
        Clutter: {EventType: {TOUCHPAD_SWIPE: 1},
            TouchpadGesturePhase: {BEGIN: 0, UPDATE: 1, END: 2, CANCEL: 3},
            EVENT_STOP: true, EVENT_PROPAGATE: false},
    });
    controller._resizeCursor = false;
    controller._findWindow = () => window;
    controller._hide = () => {events.push('hide'); window.minimized = true;};
    controller._showTerminal = () => {events.push('show'); window.minimized = false;};
    const event = (phase, dx = 0, dy = 0) => controller._handleGesture({
        type: () => 1, get_touchpad_gesture_finger_count: () => 3,
        get_gesture_phase: () => phase, get_gesture_motion_delta_unaccelerated: () => [dx, dy],
    });
    const swipe = (dx, dy, end = 2) => {event(0); const handled = event(1, dx, dy); event(end); return handled;};
    return {controller, events, window, overview, actor, swipe};
}
test('down opens terminal, next down hides it before opening overview', () => {
    const f = fixture();
    assert.equal(f.swipe(0, 20), true);
    assert.equal(f.swipe(0, 20), true);
    assert.deepEqual(f.events, ['show', 'minimize', 'overview']);
    assert.equal(f.window.minimized, true);
});
test('up closes an open terminal without opening overview', () => {
    const f = fixture(true);
    assert.equal(f.swipe(0, -20), true);
    assert.deepEqual(f.events, ['hide']);
    assert.equal(f.overview.visible, false);
});
test('up with no terminal and horizontal swipes remain with GNOME', () => {
    for (const [open, dx, dy] of [[false, 0, -20], [true, 20, 0], [false, -20, 0]]) {
        const f = fixture(open);
        assert.equal(f.swipe(dx, dy), false);
        assert.deepEqual(f.events, []);
    }
});
test('cancelled swipe does not toggle terminal or overview', () => {
    const f = fixture(true);
    f.swipe(0, -20, 3);
    assert.deepEqual(f.events, []);
});
test('entering overview hides terminal and cancels pending cold launch', () => {
    const f = fixture(true);
    f.controller._pendingShow = true;
    f.controller._hideForOverview();
    assert.equal(f.controller._pendingShow, false);
    assert.equal(f.window.minimized, true);
    assert.equal(f.actor.translation_y, 0);
});
