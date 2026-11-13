import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');

function fixture(enableAnimations = true, inset = 0) {
    let nextId = 1;
    const callbacks = new Map();
    const signals = new Map();
    const animations = [];
    const focus = {owner: 'panel', activations: 0};
    const actor = {
        opacity: 255, translation_y: 0, disposed: false,
        connect(name, callback) { const id = nextId++; signals.set(id, {name, callback}); return id; },
        disconnect(id) { assert.equal(this.disposed, false, 'access to disposed actor'); signals.delete(id); },
        destroy() {
            for (const {name, callback} of [...signals.values()])
                if (name === 'destroy') callback();
            this.disposed = true; signals.clear();
        },
        remove_all_transitions() {},
        ease(options) { animations.push({start: this.translation_y, ...options}); },
    };
    const window = {
        minimized: false,
        connect() { return nextId++; }, disconnect() {},
        get_compositor_private: () => actor,
        get_frame_rect: () => ({height: 600}),
        minimize() { this.minimized = true; },
        unminimize() { this.minimized = false; }, activate() {
            focus.activations++;
            if (focus.owner !== 'panel') focus.owner = 'terminal';
        },
    };
    const schedule = (_priority, callback) => { const id = nextId++; callbacks.set(id, callback); return id; };
    const context = vm.createContext({
        St: {Settings: {get: () => ({enable_animations: enableAnimations})}},
        Extension: class {},
        GLib: {idle_add: schedule, timeout_add: (p, _delay, callback) => schedule(p, callback),
            Source: {remove(id) { callbacks.delete(id); }}, SOURCE_REMOVE: false},
        Main: {layoutManager: {primaryMonitor: {}}, wm: {skipNextEffect() { actor.skipEffect = true; }}},
        Clutter: {AnimationMode: {EASE_OUT_CUBIC: 1, EASE_IN_CUBIC: 2, EASE_OUT_ELASTIC: 3}},
        global: {get_current_time: () => 0, stage: {set_key_focus(value) {focus.owner = value;}}},
    });
    vm.runInContext(source + '\nglobalThis.Controller = InfinityTerminal;', context);
    const controller = new context.Controller();
    Object.assign(controller, {_geometryIds: [], _pendingShow: true, _sourceId: 0,
        _firstFrame: null, _icon: {}, _topInset: () => inset, _place() {}, _setResizeCursor() {}});
    return {controller, actor, window, animations, focus,
        flush() {
            while (callbacks.size) {
                const pending = [...callbacks]; callbacks.clear();
                for (const [, callback] of pending) callback();
            }
        },
        firstFrame() {
            for (const {name, callback} of [...signals.values()])
                if (name === 'first-frame') callback();
        },
    };
}

test('cold launch waits for rendered contents and suppresses the normal map effect', () => {
    const f = fixture();
    f.controller._track(f.window, true, true);
    f.flush(); // A slow first frame arrives after every old startup timeout.
    assert.equal(f.animations.length, 0);
    assert.equal(f.actor.opacity, 0);
    assert.equal(f.actor.skipEffect, true);
    f.firstFrame();
    f.flush();
    assert.equal(f.animations.length, 1);
    assert.equal(f.animations[0].start, -616);
    assert.equal(f.animations[0].translation_y, 24);
    assert.equal(f.actor.opacity, 255);
});

test('second click during cold launch cancels opening without flashing the window', () => {
    const f = fixture();
    f.controller._track(f.window, true, true);
    f.controller._toggle();
    f.firstFrame();
    f.flush();
    assert.equal(f.animations.length, 0);
    assert.equal(f.window.minimized, true);
});

test('already rendered windows do not wait for another first-frame signal', () => {
    const f = fixture();
    f.controller._track(f.window, true);
    f.flush();
    assert.equal(f.animations.length, 1);
    assert.equal(f.animations[0].start, -616);
});

test('background startup stays invisible until explicitly requested', () => {
    const f = fixture();
    f.controller._pendingShow = false;
    f.controller._track(f.window, true, true);
    f.flush();
    assert.equal(f.actor.opacity, 0);
    f.firstFrame();
    f.flush();
    assert.equal(f.window.minimized, true);
    assert.equal(f.animations.length, 0);
    f.controller._toggle();
    f.flush();
    assert.equal(f.animations.length, 1);
    assert.equal(f.animations[0].start, -616);
});

test('show request during background startup waits for the first frame', () => {
    const f = fixture();
    f.controller._pendingShow = false;
    f.controller._track(f.window, true, true);
    f.controller._showTerminal();
    f.flush();
    assert.equal(f.animations.length, 0);
    f.firstFrame();
    f.flush();
    assert.equal(f.animations.length, 1);
});

test('hide request during startup cancels opening without animating an empty actor', () => {
    const f = fixture();
    f.controller._track(f.window, true, true);
    f.controller._hide(f.window);
    f.firstFrame();
    f.flush();
    assert.equal(f.animations.length, 0);
    assert.equal(f.window.minimized, true);
});

test('clearing a pending first frame disconnects the delayed reveal', () => {
    const f = fixture();
    f.controller._track(f.window, true, true);
    f.controller._clearFirstFrame();
    f.firstFrame();
    f.flush();
    assert.equal(f.animations.length, 0);
});

for (const cold of [false, true]) {
    test(`opening ${cold ? 'a new' : 'an existing'} terminal gives keyboard focus after panel event`, () => {
        const f = fixture();
        f.controller._track(f.window, true, cold);
        if (cold) f.firstFrame();
        f.flush();
        assert.equal(f.focus.owner, 'terminal');
    });
}

test('hiding before deferred reveal does not take keyboard focus back', () => {
    const f = fixture();
    f.controller._window = f.window;
    f.controller._reveal(f.window);
    f.controller._hide(f.window);
    f.focus.owner = 'other app';
    const activations = f.focus.activations;
    f.flush();
    assert.equal(f.focus.activations, activations);
    assert.equal(f.focus.owner, 'other app');
    assert.equal(f.animations.length, 1);
    assert.equal(f.animations[0].translation_y, -616);
});

test('opening overview before deferred reveal keeps focus out of the terminal', () => {
    const f = fixture();
    f.controller._window = f.window;
    f.controller._reveal(f.window);
    f.controller._hideForOverview();
    f.focus.owner = 'overview';
    const activations = f.focus.activations;
    f.flush();
    assert.equal(f.focus.owner, 'overview');
    assert.equal(f.focus.activations, activations);
    assert.equal(f.animations.length, 0);
});

test('actor destruction clears a pending first frame before window cleanup', () => {
    const f = fixture();
    f.controller._track(f.window, true, true);
    f.actor.destroy();
    f.controller._clearFirstFrame();
    assert.equal(f.controller._firstFrame, null);
    f.flush();
    assert.equal(f.animations.length, 0);
});

test('reduced motion disables slide animation', () => {
    const f = fixture(false);
    f.controller._track(f.window, true, true);
    f.firstFrame();
    f.flush();
    assert.ok(f.animations.length > 0);
    assert.ok(f.animations.every(animation => animation.duration === 0));
});

for (const inset of [72, 144, 176]) {
    test(`the entire terminal begins above the screen with ${inset}px inset`, () => {
        const f = fixture(true, inset);
        f.controller._track(f.window, true, true);
        f.firstFrame(); f.flush();
        assert.equal(f.animations[0].start + 600 + inset, -16);
        assert.equal(f.controller._sliding, true);
        f.animations[0].onComplete();
        assert.equal(f.animations[1].translation_y, 0);
        assert.equal(f.animations[1].mode, 3);
        f.animations[1].onComplete();
        assert.equal(f.controller._sliding, false);
    });
}
