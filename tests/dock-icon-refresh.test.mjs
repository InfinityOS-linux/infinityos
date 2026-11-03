import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const base = '../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/';
const extension = readFileSync(new URL(`${base}extension.js`, import.meta.url), 'utf8');
const method = extension.slice(extension.indexOf('  _onIconThemeChanged() {'), extension.indexOf('\n  _onFocusWindow()'));
const refresh = new Function('St', `return ({${method}})._onIconThemeChanged`)({IconTheme: {new: () => 'fresh'}});
test('an RPM icon-cache burst rebuilds once and preserves running services', () => {
  let pending, builds = 0, checks = 0;
  const renderer = {gicon: 'old', icon_name: 'old'};
  const state = {docks: [{animator: {_renderers: [renderer]}}], _loTimer: {runDebounced(value) { pending = typeof value === 'function' ? {run: value} : value; return pending; }},
    animate(options) { assert.equal(options.refresh, true); builds++; }, checkHide() { checks++; }};
  refresh.call(state);
  const first = pending;
  refresh.call(state);
  refresh.call(state);
  assert.equal(pending, first);
  assert.equal(builds, 0);
  pending.run();
  assert.equal(builds, 1);
  assert.equal(checks, 1);
  assert.equal(state.icon_theme, 'fresh');
  assert.equal(renderer.gicon, null);
  assert.equal(renderer.icon_name, null);
  assert.equal(state._iconThemeRefresh, null);
});
const dock = readFileSync(new URL(`${base}dock.js`, import.meta.url), 'utf8');
const rebuild = dock.slice(dock.indexOf('    recreateDash() {'), dock.indexOf('\n    createItem('));
const recreate = new Function(`return ({${rebuild}}).recreateDash`)();
test('rebuilding after a cache update keeps the dock visible', () => {
  const calls = [];
  const state = {opacity: 255, renderArea: {}, animator: {disable() { calls.push('clear'); }, enable() { calls.push('enable'); }},
    createDash() { return 'new dash'; }, add_child(child) { calls.push(child); }, _beginAnimation() { calls.push('animate'); }};
  recreate.call(state);
  assert.equal(state.opacity, 255);
  assert.deepEqual(calls, ['new dash', 'animate']);
});
