import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js', import.meta.url), 'utf8');
const start = source.indexOf('const dashSeparators = this._separators.filter(');
const end = source.indexOf('// hide separator between running apps and favorites', start);
assert.ok(start > 0 && end > start);
const deduplicate = new Function(source.slice(start, end));

test('Dash keeps the divider before Downloads', () => {
  const box = { remove_child(actor) { actor.removed = true; } };
  const dash = { get_parent: () => box };
  const downloads = { get_parent: () => ({}) };
  const dock = { dash: { _box: box }, _separators: [dash, downloads], _dashItems: [dash, downloads] };
  deduplicate.call(dock);
  assert.deepEqual(dock._separators, [dash, downloads]);
  assert.equal(downloads.removed, undefined);
});

test('Dash removes only duplicate built-in dividers', () => {
  const box = { remove_child(actor) { actor.removed = true; } };
  const first = { get_parent: () => box };
  const duplicate = { get_parent: () => box };
  const downloads = { get_parent: () => ({}) };
  const dock = { dash: { _box: box }, _separators: [first, duplicate, downloads], _dashItems: [first, duplicate, downloads] };
  deduplicate.call(dock);
  assert.deepEqual(dock._separators, [first, downloads]);
  assert.deepEqual(dock._dashItems, [first, downloads]);
  assert.equal(duplicate.removed, true);
});
