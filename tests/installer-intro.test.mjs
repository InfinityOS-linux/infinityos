import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/cockpit/anaconda-webui/infinityos-installer-intro.js', import.meta.url), 'utf8');

test('intro shows all three cards and releases the ready installer', async () => {
  const shown = [];
  const frames = Array.from({ length: 3 }, (_, index) => ({
    classList: { add(name) { if (name === 'is-visible') shown.push(index); }, remove() {} },
    setAttribute() {},
  }));
  const intro = {
    classList: { add() {} },
    querySelectorAll: () => frames,
    remove() { this.removed = true; },
  };
  const app = { inert: false };
  let completed;
  const done = new Promise(resolve => { completed = resolve; });
  const window = { dispatchEvent: completed };
  const document = { querySelector: selector => selector === '#infinityos-installer-intro'
    ? intro : selector === '#app' ? app : {} };
  vm.runInNewContext(source, {
    document, window, matchMedia: () => ({ matches: true }),
    setTimeout: callback => { queueMicrotask(callback); return 1; },
    Event: class { constructor(type) { this.type = type; } },
  });
  await done;
  assert.deepEqual(shown, [0, 1, 2]);
  assert.equal(intro.removed, true);
  assert.equal(app.inert, false);
  assert.equal(window.infinityosInstallerIntroComplete, true);
});

test('intro releases the installer if the animation fails', async () => {
  const frames = Array.from({ length: 3 }, () => ({
    classList: { add() {}, remove() {} }, setAttribute() {},
  }));
  const intro = {
    querySelectorAll: () => frames,
    remove() { this.removed = true; },
  };
  const app = { inert: false };
  let completed;
  const done = new Promise(resolve => { completed = resolve; });
  const window = { dispatchEvent: completed };
  const document = { querySelector: selector => {
    if (selector === '#infinityos-installer-intro') return intro;
    if (selector === '#app') return app;
    throw new Error('wizard unavailable');
  } };
  vm.runInNewContext(source, {
    document, window, matchMedia: () => ({ matches: true }),
    setTimeout: callback => { queueMicrotask(callback); return 1; },
    Event: class { constructor(type) { this.type = type; } },
    console: { error() {} },
  });
  await done;
  assert.equal(intro.removed, true);
  assert.equal(app.inert, false);
});
