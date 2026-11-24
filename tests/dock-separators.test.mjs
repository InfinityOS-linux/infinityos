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

test('a filtered running app leaves one divider and reappearing icons restore both', () => {
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
  assert.deepEqual(dock._dashItems, [pinned, appDivider, drive]);
  collect([running]);
  assert.equal(extraDivider.visible, true);
  assert.deepEqual(dock._dashItems, [pinned, appDivider, running, extraDivider, drive]);
  collect([], true);
  assert.equal(appDivider.visible, false);
  assert.deepEqual(dock._separators, [extraDivider]);
  assert.deepEqual(dock._dashItems, [pinned, extraDivider, drive]);
});

const orderStart = source.indexOf('    _orderExtraIcons() {');
const orderEnd = source.indexOf('    _snapToContainerEdge(', orderStart);
const orderExtras = new Function(`return ({${source.slice(orderStart, orderEnd)}})._orderExtraIcons`)();

test('mounted drives follow Downloads and share a single divider across mount changes', () => {
  const items = [];
  const separator = {};
  const mounts = {};
  const trash = {};
  const downloads = {};
  const disk1 = {_mountType: true};
  const disk2 = {_mountType: true};
  items.push(separator, mounts, disk1, trash, downloads, disk2);
  for (const actor of items)
    actor.get_previous_sibling = () => items[items.indexOf(actor) - 1];
  const dock = {
    _separator: separator, _mountSeparator: mounts, _downloadsIcon: downloads, _trashIcon: trash,
    _extraIcons: {get_children: () => items.slice(), set_child_above_sibling(actor, anchor) {
      items.splice(items.indexOf(actor), 1);
      items.splice(items.indexOf(anchor) + 1, 0, actor);
    }},
  };
  orderExtras.call(dock);
  assert.deepEqual(items, [separator, downloads, mounts, disk1, disk2, trash]);
  assert.equal(mounts.visible, true);

  items.splice(items.indexOf(disk1), 2);
  orderExtras.call(dock);
  assert.deepEqual(items, [separator, downloads, mounts, trash]);
  assert.equal(mounts.visible, false);
});

const animator = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/animator.js', import.meta.url), 'utf8');
const drawStart = animator.indexOf('  _drawDividers(');
const drawEnd = animator.indexOf('  //! begin optimization', drawStart);
const draw = new Function('St', `return ({${animator.slice(drawStart, drawEnd)}})._drawDividers`)({
  Widget: class {
    constructor(props) { this.props = props; }
    set_size(...size) { this.size = size; }
    set_position(...position) { this.position = position; }
    show() { this.visible = true; }
    hide() { this.visible = false; }
  },
});

test('displayed dividers share a pixel grid through fractional offsets and mount changes', () => {
  const item = (x, y) => ({_icon: {}, _renderer: {_dockCenter: [x, y]}});
  const divider = (prev, next) => ({_prev: prev, _next: next, set_size() {}});
  const appDivider = divider(item(10.25, 17), item(47.3, 32));
  const mountDivider = divider(item(94.81, 100), item(131.6, 135));
  const dock = {
    _separators: [appDivider, mountDivider],
    extension: {separator_thickness: 1},
    dash: {_box: {width: 54, height: 58, get_transformed_position: () => [0.75, 20.25]}},
    renderArea: {add_child() {}},
  };
  const state = {_dividerRenderers: []};
  const origin = [0.75, 20.25];
  for (const vertical of [false, true]) {
    draw.call(state, dock, vertical, 37, 1.25, origin);
    const [first, second] = state._dividerRenderers;
    for (const line of [first, second]) {
      assert.equal(line.visible, true);
      assert.deepEqual(line.size, vertical ? [23, 1] : [1, 35]);
      assert.ok(line.position.every((value, index) => Number.isInteger(value + origin[index])));
      assert.equal(line.props.reactive, false);
    }
    assert.equal(first.position[vertical ? 0 : 1], second.position[vertical ? 0 : 1]);
    assert.ok(second.position[vertical ? 1 : 0] > first.position[vertical ? 1 : 0]);
  }
  dock._separators = [appDivider];
  draw.call(state, dock, false, 37, 1, origin);
  assert.equal(state._dividerRenderers[1].visible, false);
  dock._separators = [appDivider, mountDivider];
  draw.call(state, dock, false, 37, 1, origin);
  assert.equal(state._dividerRenderers[1].visible, true);
  dock.extension.separator_thickness = 0;
  draw.call(state, dock, false, 37, 1, origin);
  assert.ok(state._dividerRenderers.every(line => !line.visible));
});
