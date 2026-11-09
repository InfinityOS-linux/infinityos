import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import {clampTerminalHeight, isFullHeight} from '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/resize.mjs';
const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');
function fixture() {
    const rect = {x: 0, y: 40, width: 1600, height: 500};
    let grabs = 0, dismissals = 0, ratio;
    const window = {minimized: false, get_frame_rect: () => rect,
        get_compositor_private: () => ({opacity: 255}),
        move_resize_frame(_user, x, y, width, height) {Object.assign(rect, {x, y, width, height});},
        move_frame(_user, x, y) {Object.assign(rect, {x, y});},
        maximize() {rect.height = 960;}, unmaximize() {}};
    const handle = {set_position(x, y) {this.x = x; this.y = y;}, set_size() {}};
    const controller = vm.runInNewContext(`${source}\nnew InfinityTerminal()`, {
        Extension: class {}, clampTerminalHeight, isFullHeight,
        Clutter: {EventType: {MOTION: 1, BUTTON_PRESS: 2, BUTTON_RELEASE: 3}, EVENT_STOP: true, EVENT_PROPAGATE: false},
        Meta: {Cursor: {DEFAULT: 0, SOUTH_RESIZE: 1}, MaximizeFlags: {BOTH: 3}},
        Main: {overview: {visible: false}, panel: {height: 40},
            layoutManager: {primaryMonitor: {x: 0, y: 0, width: 1600, height: 1000}}},
        global: {display: {set_cursor() {}}, stage: {grab(actor) {
            assert.equal(actor, handle); grabs++; return {dismiss() {dismissals++;}};
        }}},
    });
    Object.assign(controller, {_findWindow: () => window, _resizeHandle: handle,
        _settings: {set_double(_key, value) {ratio = value;}}});
    const event = (type, y, time) => controller._handleResize({type: () => type,
        get_coords: () => [500, y], get_button: () => 1, get_time: () => time});
    return {controller, event, rect, handle, get grabs() {return grabs;},
        get dismissals() {return dismissals;}, get ratio() {return ratio;}};
}
test('edge owns pointer while dragging and changes height without moving the top', () => {
    const f = fixture();
    assert.equal(f.event(2, 536, 1000), true);
    assert.equal(f.grabs, 1);
    assert.equal(f.event(1, 760, 1100), true);
    assert.equal(f.rect.y, 40);
    assert.equal(f.rect.height, 724);
    assert.equal(f.event(3, 760, 1200), true);
    assert.equal(f.dismissals, 1);
    assert.equal(f.ratio, 0.724);
    assert.equal(f.controller._resize, null);
});
test('double click on edge expands to screen height and releases pointer', () => {
    const f = fixture();
    f.event(2, 536, 1000); f.event(3, 536, 1050); f.event(2, 536, 1150);
    assert.equal(f.rect.height, 960);
    assert.equal(f.ratio, 0.96);
    assert.equal(f.controller._resize, null);
    assert.equal(f.grabs, f.dismissals);
});
