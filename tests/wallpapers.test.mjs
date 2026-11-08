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

test('SVG pairs lead the GNOME 51 sorted wallpaper list', () => {
  const catalog = read('root/usr/share/infinityos/background-catalog.xml');
  const entries = [...catalog.matchAll(/<wallpaper deleted="false">([\s\S]*?)<\/wallpaper>/g)]
    .map(([, xml]) => ({
      name: xml.match(/<name>(.*?)<\/name>/)[1],
      file: xml.match(/<filename>(.*?)<\/filename>/)[1],
      dark: xml.match(/<filename-dark>(.*?)<\/filename-dark>/)[1],
    }));
  assert.equal(entries.filter(item => item.name === 'Default Background').length, 1);
  // GNOME 51 bg-wallpapers-source.c: Default Background first, then strcmp.
  entries.push({ name: 'Adwaita', file: 'stock.svg' }, { name: 'Blobs', file: 'stock.svg' });
  entries.sort((a, b) => a.name === 'Default Background' ? -1 :
    b.name === 'Default Background' ? 1 : Buffer.compare(Buffer.from(a.name), Buffer.from(b.name)));
  for (const [index, [, stem]] of pairs.entries()) {
    assert.equal(entries[index].file, `/usr/share/backgrounds/infinityos/light-${stem}.svg`);
    assert.equal(entries[index].dark, `/usr/share/backgrounds/infinityos/dark-${stem}.svg`);
    assert.ok(existsSync(join(repo, folder, `light-${stem}.svg`)));
    assert.ok(existsSync(join(repo, folder, `dark-${stem}.svg`)));
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
