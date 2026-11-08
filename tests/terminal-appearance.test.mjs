import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const base = 'packages/infinity-terminal/root/usr/share/infinityos/ghostty/';

test('terminal delegates live theme switching to Ghostty without fixed color overrides', () => {
  const config = read(base + 'config');
  assert.match(config, /^window-theme = system$/m);
  assert.match(config, /^theme = light:\/usr\/share\/infinityos\/ghostty\/themes\/infinity-light,dark:\/usr\/share\/infinityos\/ghostty\/themes\/infinity-dark$/m);
  assert.doesNotMatch(config, /^(background|foreground|palette|cursor-color|selection-background|selection-foreground)\s*=/m);
  for (const mode of ['light', 'dark']) {
    const theme = read(base + 'themes/infinity-' + mode);
    assert.equal([...theme.matchAll(/^palette = /gm)].length, 16);
    for (const key of ['background', 'foreground', 'cursor-color', 'selection-background', 'selection-foreground']) {
      assert.match(theme, new RegExp(`^${key} = #[0-9a-f]{6}$`, 'm'));
    }
  }
  const colors = read(base + 'themes/infinity-light');
  const rgb = key => colors.match(new RegExp(`^${key} = #([0-9a-f]{6})$`, 'm'))[1].match(/../g).map(c => parseInt(c, 16) / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4);
  const luminance = key => rgb(key).reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i], 0);
  assert.ok((luminance('background') + .05) / (luminance('foreground') + .05) > 7);
  assert.match(read(base + 'style.css'), /@media \(prefers-color-scheme: light\)/);
});
