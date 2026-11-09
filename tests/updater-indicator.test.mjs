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
