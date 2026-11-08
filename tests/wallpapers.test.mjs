import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';

const repo = new URL('../', import.meta.url).pathname;
const read = path => readFileSync(join(repo, path), 'utf8');
const folder = 'root/usr/share/backgrounds/infinityos/';
const pairs = [
  ['Horyzont', '02-horyzont'],
  ['Pętla', '01-petla'],
  ['Portal', '03-portal'],
  ['Wstęga', '04-wstega'],
  ['Przepływ', '05-przeplyw'],
];

test('new SVG pairs lead the wallpaper catalog', () => {
  const catalog = read('root/usr/share/infinityos/background-catalog.xml');
  let previous = 0;
  for (const [name, stem] of pairs) {
    const entry = catalog.indexOf(`<name>Infinity OS — ${name}</name>`);
    assert.ok(entry > previous && entry < catalog.indexOf('<name>Default Background</name>'));
    assert.ok(catalog.includes(`<filename>/usr/share/backgrounds/infinityos/light-${stem}.svg</filename>`));
    assert.ok(catalog.includes(`<filename-dark>/usr/share/backgrounds/infinityos/dark-${stem}.svg</filename-dark>`));
    assert.ok(existsSync(join(repo, folder, `light-${stem}.svg`)));
    assert.ok(existsSync(join(repo, folder, `dark-${stem}.svg`)));
    previous = entry;
  }
});

test('Horyzont is the desktop and live initial setup default', () => {
  for (const source of [
    'root/usr/share/infinityos/gnome-defaults',
    'root/etc/dconf/db/infinityos-initial-setup.d/00-infinityos',
  ]) {
    const defaults = read(source);
    assert.ok(defaults.includes("picture-uri-dark='file:///usr/share/backgrounds/infinityos/dark-02-horyzont.svg'"));
  }
  assert.ok(read('root/usr/share/infinityos/gnome-defaults')
    .includes("picture-uri='file:///usr/share/backgrounds/infinityos/light-02-horyzont.svg'"));
});
