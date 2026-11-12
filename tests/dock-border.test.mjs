import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/extension.js', import.meta.url), 'utf8');
const start = source.indexOf('  _updateBorderStyle() {');
const end = source.indexOf('\n  _updateLayout(', start);
const update = new Function(`return ({${source.slice(start, end)}})._updateBorderStyle`)();
function border(overrides = {}) {
  const dock = { border_thickness: 1, adaptive_background: true, panel_mode: false,
    border_color: [1, 0, 0, 1], _getPreferredColorScheme: () => 'dark',
    _style: { rgba: color => color.join(',') }, ...overrides };
  update.call(dock);
  return dock._backgroundStyle;
}
test('adaptive dock highlights only its top edge in both themes', () => {
  assert.match(border(), /border-color: rgba\(0.87,0.8,1,0.32\) transparent transparent transparent/);
  assert.match(border({ _getPreferredColorScheme: () => 'light' }), /border-color: rgba\(1,1,1,0.65\) transparent transparent transparent/);
});
test('disabled and custom borders retain their settings', () => {
  assert.equal(border({ border_thickness: 0 }).trim(), '');
  assert.match(border({ adaptive_background: false }), /border: 1px solid rgba\(1,0,0,1\)/);
  assert.doesNotMatch(border({ adaptive_background: false }), /transparent/);
});
test('side panels keep their existing edge selection', () => {
  const style = border({ panel_mode: true, _position: 'left' });
  assert.match(style, /border-left: 0px; border-top: 0px; border-bottom: 0px/);
  assert.doesNotMatch(style, /transparent/);
});
