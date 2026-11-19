import assert from 'node:assert/strict';
import {test} from 'node:test';
import {dockSurfaceLayers, paintDockSurface} from '../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock-surface.mjs';

function actor(name, color, opacity = 255, visible = true) {
    return {name, opacity, visible, get_theme_node: () => ({get_background_color: () => color})};
}

test('dock copies the same panel tint layers and effective alpha in paint order', () => {
    const layers = [
        actor('unrelated', {red: 255, green: 0, blue: 0, alpha: 255}),
        actor('wackPanelBackdrop', {red: 40, green: 30, blue: 60, alpha: 80}, 128),
        actor('wackPanelProximityOverlay', {red: 20, green: 10, blue: 30, alpha: 60}, 255, false),
        actor('wackPanelBackdropOverlay', {red: 80, green: 50, blue: 100, alpha: 40}),
    ];
    const panel = {...actor('panel', {red: 0, green: 0, blue: 0, alpha: 20}), get_children: () => layers};
    assert.deepEqual(dockSurfaceLayers(panel, false, true), [
        [0, 0, 0, 20 / 255], [40 / 255, 30 / 255, 60 / 255, 80 / 255 * (128 / 255)],
        [80 / 255, 50 / 255, 100 / 255, 40 / 255],
    ]);
});

test('modern Cogl colors and opaque light/dark fallbacks match the updater', () => {
    const panel = {...actor('panel', {get_red: () => .1, get_green: () => .2, get_blue: () => .3, get_alpha: () => .4}),
        get_children: () => []};
    assert.deepEqual(dockSurfaceLayers(panel, false, true), [[.1, .2, .3, .4]]);
    assert.deepEqual(dockSurfaceLayers(panel, false, false), [[24 / 255, 22 / 255, 36 / 255, 1]]);
    assert.deepEqual(dockSurfaceLayers(panel, true, false), [[250 / 255, 247 / 255, 1, 1]]);
});

for (const scale of [1, 1.25, 2]) {
    test(`surface fills the rounded pill before its outline at scale ${scale}`, () => {
        const calls = [];
        const cr = new Proxy({}, {get: (_, name) => (...args) => calls.push([name, ...args])});
        paintDockSurface(cr, 400 * scale, 64 * scale, 40,
            [[.1, .2, .3, .25], [0, 0, 0, 0], [.3, .2, .4, .2]], scale);
        assert.equal(calls.filter(call => call[0] === 'arc').length, 4);
        assert.equal(calls.filter(call => call[0] === 'paint').length, 2);
        assert(calls.findIndex(call => call[0] === 'clip') < calls.findIndex(call => call[0] === 'paint'));
        assert.equal(calls.find(call => call[0] === 'arc')[3], 32 * scale);
        assert.equal(calls.filter(call => call[0] === 'stroke').length, 0);
    });
}
