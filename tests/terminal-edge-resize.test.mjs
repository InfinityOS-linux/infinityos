import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import {clampTerminalHeight, isFullHeight} from '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/resize.mjs';
const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');
function fixture() {
    const rect = {x: 0, y: 40, width: 1600, height: 500};
    let grabs = 0, dismissals = 0, ratio, cursor, moves = 0, tick;
    let pointer = [500, 536, 1];
    const window = {minimized: false, get_frame_rect: () => rect,
        get_compositor_private: () => ({opacity: 255}),
        move_resize_frame(_user, x, y, width, height) {moves++; Object.assign(rect, {x, y, width, height});},
        move_frame(_user, x, y) {Object.assign(rect, {x, y});},
        maximize() {rect.height = 960;}, unmaximize() {}};
    const handle = {visible: true, set_cursor_type(value) {cursor = value;}, set_position(x, y) {this.x = x; this.y = y;}, set_size() {}};
    const layout = {primaryMonitor: {x: 0, y: 0, width: 1600, height: 1000}};
    const controller = vm.runInNewContext(`${source}\nnew InfinityTerminal()`, {
        Extension: class {}, clampTerminalHeight, isFullHeight,
        GLib: {PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false, SOURCE_CONTINUE: true,
            timeout_add(_priority, _delay, callback) {tick = callback; return 1;}, Source: {remove() {tick = null;}}},
        console: {error() {}},
        Clutter: {CursorType: {DEFAULT: 0, NS_RESIZE: 1}, ModifierType: {BUTTON1_MASK: 1}, EventType: {MOTION: 1, BUTTON_PRESS: 2, BUTTON_RELEASE: 3, KEY_PRESS: 4}, KEY_Escape: 27, EVENT_STOP: true, EVENT_PROPAGATE: false},
        Meta: {Cursor: {DEFAULT: 0, SOUTH_RESIZE: 1}, MaximizeFlags: {BOTH: 3}},
        Main: {overview: {visible: false}, panel: {height: 40},
            layoutManager: layout},
        global: {get_pointer: () => pointer, display: {set_cursor(value) {cursor = value;}}, stage: {grab(actor) {
            assert.equal(actor, handle); grabs++; return {dismiss() {dismissals++;}};
        }}},
    });
    Object.assign(controller, {_findWindow: () => window, _resizeHandle: handle,
        _settings: {set_double(_key, value) {ratio = value;}}});
    const event = (type, y, time) => controller._handleResize({type: () => type,
        get_state: () => pointer[2], get_key_symbol: () => 27, get_coords: () => [500, y], get_button: () => 1, get_time: () => time});
    return {controller, event, rect, handle, layout, frame(y, held = true) {pointer = [500, y, held ? 1 : 0]; tick?.();},
        get moves() {return moves;}, get cursor() {return cursor;}, get grabs() {return grabs;},
        get dismissals() {return dismissals;}, get ratio() {return ratio;}};
}
test('edge owns pointer while dragging and changes height without moving the top', () => {
    const f = fixture();
    assert.equal(f.event(2, 536, 1000), true);
    assert.equal(f.grabs, 1);
    assert.equal(f.event(1, 760, 1100), true);
    f.frame(760);
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

test('hover changes cursor but cannot resize, even after a lost release', () => {
    const f = fixture();
    f.event(1, 536, 900);
    assert.equal(f.cursor, 1);
    assert.equal(f.moves, 0);
    f.event(2, 536, 1000);
    f.frame(760);
    f.frame(800, false);
    assert.equal(f.controller._resize, null);
    assert.equal(f.grabs, f.dismissals);
    const height = f.rect.height;
    f.event(1, 900, 1300);
    assert.equal(f.rect.height, height);
});
test('fast motion is coalesced into one resize using the latest pointer position', () => {
    const f = fixture();
    f.event(2, 536, 1000);
    for (let y = 550; y < 850; y++) f.event(1, y, 1100);
    assert.equal(f.moves, 0);
    f.frame(850);
    assert.equal(f.moves, 1);
    assert.equal(f.rect.height, 814);
    f.frame(850);
    assert.equal(f.moves, 1);
    f.event(3, 850, 1200);
    assert.equal(f.grabs, f.dismissals);
});
test('Escape and window errors release the pointer', () => {
    const f = fixture();
    f.event(2, 536, 1000);
    f.event(4, 536, 1100);
    assert.equal(f.controller._resize, null);
    f.event(2, 536, 2000);
    f.controller._resize.window.move_resize_frame = () => {throw new Error('window destroyed');};
    f.frame(850);
    assert.equal(f.controller._resize, null);
    assert.equal(f.grabs, f.dismissals);
});

test('current monitor placement omits primary panel and falls back after unplug', () => {
    const f = fixture();
    const secondary = {x: 1600, y: 0, width: 1920, height: 1080};
    f.layout.monitors = [f.layout.primaryMonitor, secondary];
    f.layout.currentMonitor = secondary;
    f.controller._settings.get_boolean = () => true;
    f.controller._settings.get_double = () => 0.5;
    f.controller._selectMonitor();
    assert.equal(f.controller._monitor(), secondary);
    assert.equal(f.controller._panelHeight(), 0);
    f.layout.monitors = [f.layout.primaryMonitor];
    assert.equal(f.controller._monitor(), f.layout.primaryMonitor);
    assert.equal(f.controller._panelHeight(), 40);
});

test('hardware strip reserves space during placement and full-height resize', () => {
    const f = fixture();
    f.controller._hardware = {height: 112, sync() {}};
    f.controller._settings.get_double = () => 0.5;
    f.controller._place(f.controller._findWindow());
    assert.equal(f.rect.y, 152);
    assert.equal(f.rect.height, 500);
    f.event(2, 648, 1000); f.event(3, 648, 1050); f.event(2, 648, 1150);
    assert.equal(f.rect.y, 152);
    assert.equal(f.rect.height, 848);
    assert.equal(f.rect.y + f.rect.height, 1000);
    assert.equal(f.ratio, 0.848);
});
