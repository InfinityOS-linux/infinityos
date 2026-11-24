import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js', import.meta.url), 'utf8');
const start = source.indexOf('const dashSeparators = this._separators.filter(');
const end = source.indexOf('if (appDivider) {', start);
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

test('Dash hides outgoing dividers and leaves the native current divider attached', () => {
  const box = { remove_child(actor) { actor.removed = true; } };
  const first = { get_parent: () => box };
  const duplicate = { get_parent: () => box };
  const downloads = { get_parent: () => ({}) };
  const dock = { dash: { _box: box, _separator: first }, _separators: [duplicate, first, downloads], _dashItems: [first, duplicate, downloads] };
  deduplicate.call(dock);
  assert.deepEqual(dock._separators, [first, downloads]);
  assert.deepEqual(dock._dashItems, [first, downloads]);
  assert.equal(duplicate.visible, false);
  assert.equal(duplicate.removed, undefined);
});

const collectGroups = new Function('appDivider', source.slice(end, source.indexOf('// find the showAppsIcon', end)));

test('a filtered running app leaves one tall divider and reappearing icons restore both', () => {
  const pinned = {_icon: {}};
  const running = {_icon: {}};
  const drive = {_icon: {}};
  const appDivider = {};
  const extraDivider = {};
  const dock = {
    extension: {}, _separator: extraDivider,
    _extraIcons: {get_children: () => [extraDivider, drive]},
    _inspectIcon(actor) {
      this._dashItems.push(actor);
      (actor === extraDivider ? this._separators : this._icons).push(actor);
    },
  };
  function collect(apps, favoritesOnly = false) {
    dock.extension.favorites_only = favoritesOnly;
    dock._icons = [pinned, ...apps];
    dock._dashItems = [pinned, appDivider, ...apps];
    dock._separators = [appDivider];
    collectGroups.call(dock, appDivider);
  }
  collect([]);
  assert.equal(extraDivider.visible, false);
  assert.equal(dock._joinedSeparator, appDivider);
  assert.deepEqual(dock._dashItems, [pinned, appDivider, drive]);
  collect([running]);
  assert.equal(extraDivider.visible, true);
  assert.equal(dock._joinedSeparator, null);
  assert.deepEqual(dock._dashItems, [pinned, appDivider, running, extraDivider, drive]);
  collect([], true);
  assert.equal(appDivider.visible, false);
  assert.deepEqual(dock._separators, [extraDivider]);
  assert.deepEqual(dock._dashItems, [pinned, extraDivider, drive]);
});
