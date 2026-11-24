import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';

const dir = new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/', import.meta.url);
const items = readFileSync(new URL('dockItems.js', dir), 'utf8');
const start = items.indexOf('    update(data) {', items.indexOf('class DockItemDotsOverlay'));
const end = items.indexOf('\n    }', start) + 6;
const update = new Function('DockPosition', `return ({${items.slice(start, end)}}).update`)({
  RIGHT: 'right', TOP: 'top',
});

test('the running indicator stays on the optical icon center in all dock orientations', () => {
  const icon = {x: 140.5, y: 21.75, size: 50};
  const overlay = {
    renderer: {_canvas: {width: 96, set_scale(x, y) { this.scale = [x, y]; }}, set_state() {}},
    set_size(...size) { this.size = size; },
    set_position(...position) { this.position = position; },
  };
  for (const position of ['top', 'bottom', 'left', 'right']) {
    const vertical = position === 'left' || position === 'right';
    update.call(overlay, {appCount: 1, position, vertical, centerX: icon.x, centerY: icon.y,
      size: icon.size, extension: {running_indicator_style_options: []}});
    assert.deepEqual(overlay.size, [50, 50]);
    assert.deepEqual(overlay.renderer._canvas.scale, [50 / 96, 50 / 96]);
    const axis = vertical ? 1 : 0;
    assert.equal(overlay.position[axis] + overlay.size[axis] / 2, vertical ? icon.y : icon.x);
  }
});

test('one to four painted dots are centered on their canvas', () => {
  const source = readFileSync(new URL('apps/dot.js', dir), 'utf8');
  const start = source.indexOf('    _draw_dots(ctx, state) {');
  const end = source.indexOf('    _draw_binary', start);
  const draw = new Function('Drawing', `return ({${source.slice(start, end)}})._draw_dots`)({set_color() {}});
  for (let count = 1; count <= 4; count++) {
    const dots = [];
    let offset = 0;
    draw.call({get_surface_size: () => [96, 96], dot_size: () => 4.8, _padding: 8}, {
      translate(x) { offset = x; }, newSubPath() {}, arc(x) { dots.push(x + offset); },
      strokePreserve() {}, fill() {},
    }, {count, color: [1, 1, 1, 1]});
    assert.equal(dots.length, count);
    assert.ok(Math.abs((dots[0] + dots.at(-1)) / 2 - 48) < 0.01);
  }
});
