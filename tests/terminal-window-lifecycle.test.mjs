import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8');
const start = source.indexOf('(_display, window) => {', source.indexOf('this._windowCreatedId ='));
const end = source.indexOf('\n        });', start);
const created = vm.runInNewContext(`(${source.slice(start, end)}\n})` .replace('(_display, window) =>', 'function (_display, window)'));

function emitter() {
    let nextId = 1;
    const signals = new Map();
    return {
        disposed: false,
        connect(name, fn) { assert.equal(this.disposed, false); const id = nextId++; signals.set(id, {name, fn}); return id; },
        disconnect(id) { assert.equal(this.disposed, false, 'access to disposed object'); signals.delete(id); },
        emit(name) { for (const [id, signal] of [...signals]) if (signals.has(id) && signal.name === name) signal.fn(); },
        destroy() { this.emit('destroy'); this.disposed = true; signals.clear(); },
    };
}

for (const actorFirst of [true, false]) {
    test(`unidentified window cleanup with ${actorFirst ? 'actor' : 'window'} destroyed first`, () => {
        const actor = emitter();
        const window = Object.assign(emitter(), {get_compositor_private: () => actor});
        const controller = {_pendingWindows: new Map(), _isGhosTTY: () => false};
        created.call(controller, null, window);
        if (actorFirst) actor.destroy();
        window.emit('unmanaged');
        if (!actorFirst) actor.destroy();
        assert.equal(controller._pendingWindows.size, 0);
    });
}

test('recognizing a terminal disconnects discovery listeners before tracking it', () => {
    const actor = emitter();
    const window = Object.assign(emitter(), {get_compositor_private: () => actor});
    let recognized = false;
    let tracked = 0;
    const controller = {_pendingWindows: new Map(), _isGhosTTY: () => recognized,
        _track(w, fresh, waiting) { assert.equal(w, window); assert.equal(fresh, true); assert.equal(waiting, false); tracked++; }};
    created.call(controller, null, window);
    actor.emit('first-frame');
    recognized = true;
    window.emit('notify::gtk-application-id');
    actor.destroy();
    window.emit('unmanaged');
    assert.equal(tracked, 1);
    assert.equal(controller._pendingWindows.size, 0);
});
