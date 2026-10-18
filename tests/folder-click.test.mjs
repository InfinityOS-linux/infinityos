import assert from 'node:assert/strict';
import { test } from 'node:test';
import { folderItemsOrOpen } from '../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/folderClick.js';

test('empty Downloads opens the folder', async () => {
  let files;
  let opened = 0;
  const result = await folderItemsOrOpen({
    items: () => files,
    prepare: () => { files = []; },
    refresh: async () => {},
    open: () => { opened++; },
  });
  assert.equal(result, null);
  assert.equal(opened, 1);
});

test('a download arriving before refresh keeps the popup', async () => {
  let files = [];
  let opened = 0;
  const result = await folderItemsOrOpen({
    items: () => files,
    prepare: () => {},
    refresh: () => { files = [{ name: 'new.txt' }]; },
    open: () => { opened++; },
  });
  assert.deepEqual(result, [{ name: 'new.txt' }]);
  assert.equal(opened, 0);
});

test('an empty virtual folder also opens in the file manager', async () => {
  let opened = 0;
  const result = await folderItemsOrOpen({
    items: () => [],
    prepare: () => {},
    refresh: null,
    open: () => { opened++; },
  });
  assert.equal(result, null);
  assert.equal(opened, 1);
});
