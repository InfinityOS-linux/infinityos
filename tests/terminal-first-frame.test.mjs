import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');
const monitorSource = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/hardware-monitor.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export class', 'class');

function fixture(enableAnimations = true, inset = 0) {
    let nextId = 1;
    const callbacks = new Map();
    const signals = new Map();
    const windowSignals = new Map();
    const emit = (handlers, signal) => {
        for (const [id, {name, callback}] of [...handlers])
            if (name === signal && handlers.has(id)) callback();
    };
    const animations = [];
    const windows = [];
    const focus = {owner: 'panel', activations: 0};
    const actor = {
        opacity: 255, translation_y: 0, mapped: true, disposed: false,
        connect(name, callback) { const id = nextId++; signals.set(id, {name, callback}); return id; },
        disconnect(id) { assert.equal(this.disposed, false, 'access to disposed actor'); signals.delete(id); },
        emit(signal) { emit(signals, signal); },
        destroy() {
            this.emit('destroy');
            this.disposed = true; signals.clear();
        },
        remove_all_transitions() {},
        ease(options) { animations.push({start: this.translation_y, ...options}); },
    };
    const window = {
        minimized: false,
        connect(name, callback) { const id = nextId++; windowSignals.set(id, {name, callback}); return id; },
        disconnect(id) { windowSignals.delete(id); },
        emit(signal) { emit(windowSignals, signal); },
        get_compositor_private: () => actor,
        get_frame_rect: () => ({height: 600}),
        showing_on_its_workspace() { return actor.mapped && !this.minimized; },
        minimize() { this.minimized = true; },
        unminimize() { this.minimized = false; }, activate() {
            focus.activations++;
            if (focus.owner !== 'panel') focus.owner = 'terminal';
        },
    };
    const schedule = (_priority, callback) => { const id = nextId++; callbacks.set(id, callback); return id; };
    const sessionMode = {isLocked: false, isGreeter: false};
    const screenShieldGroup = {visible: false};
    const context = vm.createContext({
        St: {Settings: {get: () => ({enable_animations: enableAnimations})}},
        Extension: class {},
        GLib: {get_language_names: () => ['en'], idle_add: schedule, timeout_add: (p, _delay, callback) => schedule(p, callback),
            Source: {remove(id) { callbacks.delete(id); }}, SOURCE_REMOVE: false},
        Main: {overview: {visible: false, _overview: {controls: {_workspacesDisplay: {_updateWorkspacesViews() {}}}}},
            sessionMode, layoutManager: {primaryMonitor: {}, screenShieldGroup},
            wm: {skipNextEffect() { actor.skipEffect = true; }}},
        Clutter: {AnimationMode: {EASE_OUT_CUBIC: 1, EASE_IN_CUBIC: 2, EASE_OUT_ELASTIC: 3}},
        global: {get_current_time: () => 0, get_window_actors: () => windows,
            stage: {set_key_focus(value) {focus.owner = value;}}},
    });
    vm.runInContext(source + '\nglobalThis.Controller = InfinityTerminal;', context);
    const controller = new context.Controller();
    Object.assign(controller, {_geometryIds: [], _pendingShow: true, _sourceId: 0,
        _firstFrame: null, _topInset: () => inset, _place() {}, _setResizeCursor() {}});
    return {controller, actor, window, animations, focus, windows, sessionMode, screenShieldGroup,
        monitor() {
            const prototype = vm.runInContext(monitorSource + '\nHardwareMonitor.prototype', context);
            const hardware = Object.create(prototype, {height: {value: 72}});
            Object.assign(hardware, {
                actor: {visible: false, set_position() {}, set_size() {}},
                _mappedChanged: () => controller._syncResizeHandle(),
                _menu: {isOpen: false, close() { this.isOpen = false; }}, _history: new Map(), _restart() {},
            });
            controller._hardware = hardware;
            controller._resizeHandle = {set_position() {}, set_size() {}};
            return hardware;
        },
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

for (const cold of [false, true]) {
    test(`manual pull has no overshoot or elastic bounce, cold=${cold}`, () => {
        const f = fixture();
        f.controller._pendingBounce = false;
        f.controller._track(f.window, true, cold);
        if (cold) f.firstFrame();
        f.flush();
        assert.equal(f.animations.length, 1);
        assert.equal(f.animations[0].translation_y, 0);
        assert.equal(f.animations[0].mode, 1);
        assert.equal(f.animations[0].duration, 120);
        f.animations[0].onComplete();
        assert.equal(f.animations.length, 1);
        assert.equal(f.controller._sliding, false);
    });
}

test('a regular click or keyboard toggle restores the default bounce after a manual pull', () => {
    const f = fixture();
    f.controller._pendingBounce = false;
    f.controller._findWindow = () => null;
    f.controller._spawn = () => {};
    f.controller._toggle();
    assert.equal(f.controller._pendingBounce, true);
    f.controller._track(f.window, true, true);
    f.firstFrame(); f.flush();
    assert.equal(f.animations[0].translation_y, 24);
    f.animations[0].onComplete();
    assert.equal(f.animations[1].mode, 3);
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

test('app-list restore shows widgets and uses the same animated reveal as the shortcut', () => {
    const f = fixture();
    const hardware = [];
    f.window.minimized = true;
    f.controller._window = f.window;
    f.controller._findWindow = () => f.window;
    f.controller._hardware = {sync(_rect, visible, actor) { hardware.push({visible, actor}); }};
    f.controller._resizeHandle = {set_position() {}, set_size() {}};
    f.controller._launchFromApp();
    f.flush();
    assert.equal(f.window.minimized, false);
    assert.equal(f.animations.length, 1);
    assert.equal(f.animations[0].start, -616);
    assert.equal(f.animations[0].translation_y, 24);
    assert(hardware.some(call => call.visible && call.actor === f.actor));
});

test('terminal tracking works without the retired panel icon', () => {
    const f = fixture();
    f.controller._track(f.window, false);
    assert.equal(f.controller._window, f.window);
    assert.ok(f.controller._unmanagedId > 0);
    assert.ok(f.controller._minimizedId > 0);
});

test('window lookup skips compositor actors with no attached window', () => {
    const f = fixture();
    f.window.get_wm_class = () => 'com.infinityos.GhosTTY';
    f.windows.push({meta_window: null}, {meta_window: f.window});
    assert.equal(f.controller._findWindow(), f.window);
});

test('Show Desktop hides the widgets even when Mutter does not minimize the window', () => {
    const f = fixture();
    const hardware = f.monitor();
    f.controller._window = f.window;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, true);

    f.actor.mapped = false;
    f.actor.emit('notify::mapped');
    assert.equal(f.window.minimized, false);
    assert.equal(hardware.actor.visible, false);
    assert.equal(f.controller._resizeHandle.visible, false);

    f.actor.mapped = true;
    f.actor.emit('notify::mapped');
    assert.equal(hardware.actor.visible, true);
});

test('closing the terminal hides its widgets while the old actor is still in the compositor', () => {
    const f = fixture();
    const hardware = f.monitor();
    f.controller._findWindow = () => f.window;
    f.controller._track(f.window, false);
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, true);

    f.window.emit('unmanaged');
    assert.equal(f.actor.mapped, true);
    assert.equal(hardware.actor.visible, false);
    assert.equal(f.controller._resizeHandle.visible, false);
    assert.equal(hardware._windowActor, null);
});

test('minimized terminal hides widgets even if Mutter still reports the actor mapped', () => {
    const f = fixture();
    const hardware = f.monitor();
    f.window.showing_on_its_workspace = () => true;
    f.controller._track(f.window, false);
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, true);

    f.window.minimized = true;
    f.window.emit('notify::minimized');
    assert.equal(hardware.actor.visible, false);
    assert.equal(f.controller._resizeHandle.visible, false);
});

test('collapse hides widgets immediately and settles if Shell interrupts the animation', () => {
    const f = fixture();
    const hardware = f.monitor();
    f.controller._window = f.window;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, true);
    hardware._menu.isOpen = true;

    f.controller._hide(f.window);
    assert.equal(hardware.actor.visible, false);
    assert.equal(hardware._menu.isOpen, false);
    assert.equal(f.window.minimized, false);
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, false);
    f.animations[0].onStopped(false);
    assert.equal(f.window.minimized, true);
    assert.equal(f.actor.translation_y, 0);
    assert.equal(hardware.actor.visible, false);
});

test('reopening during collapse cancels the stale collapse callback', () => {
    const f = fixture();
    const hardware = f.monitor();
    f.controller._window = f.window;
    f.controller._syncResizeHandle();
    f.controller._hide(f.window);
    f.controller._toggle();
    f.animations[0].onStopped(false);
    assert.equal(f.window.minimized, false);
    assert.equal(hardware.actor.visible, true);
});

test('widgets stay hidden while the screen shield is up and for locked or greeter modes', () => {
    const f = fixture();
    const hardware = f.monitor();
    f.controller._window = f.window;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, true);

    f.screenShieldGroup.visible = true;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, false);
    f.sessionMode.isLocked = true;
    f.screenShieldGroup.visible = false;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, false);
    f.sessionMode.isLocked = false;
    f.sessionMode.isGreeter = true;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, false);
    f.sessionMode.isGreeter = false;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, true);
    f.window.minimized = true;
    f.controller._syncResizeHandle();
    assert.equal(hardware.actor.visible, false);
});
