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
