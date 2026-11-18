import assert from 'node:assert/strict';
import {test} from 'node:test';
import {paintDockOutline} from '../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock-outline.mjs';

for (const light of [false, true]) for (const scale of [1, 1.25, 2]) {
    test(`one lower contour, isolated upper highlight: light=${light}, scale=${scale}`, () => {
        const calls = [];
        const cr = new Proxy({}, {get: (_, name) => (...args) => calls.push([name, ...args])});
        paintDockOutline(cr, 400 * scale, 72 * scale, 40, 1, light, scale);
        const strokes = calls.flatMap((call, i) => call[0] === 'stroke' ? [i] : []);
        assert.equal(strokes.length, 2);
        const base = calls.slice(0, strokes[0]);
        assert.equal(base.filter(call => call[0] === 'arc').length, 4);
        assert.equal(base.filter(call => call[0] === 'setSourceRGBA').length, 1);
        assert.equal(base.at(-2)[0], 'setSourceRGBA');
        assert.equal(base.at(-1)[1], scale);
        const topClip = calls.find(call => call[0] === 'rectangle');
        assert(topClip[4] < 36 * scale, 'upper color must not touch lower corners');
        assert(calls.findIndex(call => call[0] === 'clip') > strokes[0]);
        for (const call of calls)
            for (const value of call.slice(1)) assert(Number.isFinite(value));
    });
}

test('empty allocations are harmless and zero border retains only the top highlight', () => {
    const calls = [];
    const cr = new Proxy({}, {get: (_, name) => (...args) => calls.push([name, ...args])});
    paintDockOutline(cr, 0, 0, 40, 1, false);
    assert.equal(calls.length, 0);
    paintDockOutline(cr, 320, 64, 40, 0, false);
    assert.equal(calls.filter(call => call[0] === 'stroke').length, 1);
});
