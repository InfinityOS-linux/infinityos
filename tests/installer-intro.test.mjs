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
  const delays = [];
  let completed;
  const done = new Promise(resolve => { completed = resolve; });
  const window = { dispatchEvent: event => { if (event.type === 'infinityos-installer-intro-complete') completed(); } };
  const document = { querySelector: selector => selector === '#infinityos-installer-intro'
    ? intro : selector === '#app' ? app : {} };
  vm.runInNewContext(source, {
    document, window, matchMedia: () => ({ matches: false }),
    setTimeout: (callback, delay) => { delays.push(delay); queueMicrotask(callback); return 1; },
    Event: class { constructor(type) { this.type = type; } },
  });
  await done;
  assert.deepEqual(shown, [0, 1, 2]);
  assert.ok(delays.filter(delay => delay >= 2000).length >= 3);
  assert.ok(delays.reduce((sum, delay) => sum + delay, 0) >= 9000);
  assert.equal(intro.removed, true);
  assert.equal(app.inert, false);
  assert.equal(window.infinityosInstallerIntroComplete, true);
});

test('intro waits for the wizard before showing the first card', async () => {
  const shown = [];
  const frames = Array.from({ length: 3 }, (_, index) => ({
    classList: { add(name) { if (name === 'is-visible') shown.push(index); }, remove() {} },
    setAttribute() {},
  }));
  const intro = { classList: { add() {} }, querySelectorAll: () => frames, remove() {} };
  const app = { inert: false };
  let wizardReady = false;
  let onMutation;
  let complete;
  const done = new Promise(resolve => { complete = resolve; });
  const document = { querySelector: selector => selector === '#infinityos-installer-intro'
    ? intro : selector === '#app' ? app : wizardReady ? {} : null };
  vm.runInNewContext(source, {
    document, window: { dispatchEvent: event => { if (event.type === 'infinityos-installer-intro-complete') complete(); } }, matchMedia: () => ({ matches: false }),
    MutationObserver: class { constructor(callback) { onMutation = callback; } observe() {} disconnect() {} },
    setTimeout: (callback, delay) => { if (delay !== 20000) queueMicrotask(callback); return 1; },
    clearTimeout() {},
    Event: class { constructor(type) { this.type = type; } },
  });
  await Promise.resolve();
  assert.deepEqual(shown, []);
  wizardReady = true;
  onMutation();
  await done;
  assert.deepEqual(shown, [0, 1, 2]);
});

test('preloader holds the first card until the wizard survives startup', async () => {
  const shown = [];
  const pending = [];
  let wizardReady = true;
  let onMutation;
  const frames = Array.from({length: 3}, (_, index) => ({
    classList: {add(name) { if (name === 'is-visible') shown.push(index); }, remove() {}},
    setAttribute() {},
  }));
  const intro = {classList: {add() {}}, querySelectorAll: () => frames, remove() {}};
  let finished = false;
  let complete;
  const done = new Promise(resolve => { complete = () => { finished = true; resolve(); }; });
  vm.runInNewContext(source, {
    document: {querySelector: selector => selector === '#infinityos-installer-intro'
      ? intro : selector === '#app' ? {inert: false} : wizardReady ? {} : null},
    window: {dispatchEvent: event => { if (event.type === 'infinityos-installer-intro-complete') complete(); }},
    matchMedia: () => ({matches: false}),
    MutationObserver: class {constructor(callback) { onMutation = callback; } observe() {} disconnect() {}},
    setTimeout: callback => { pending.push(callback); return pending.length; },
    Event: class {constructor(type) { this.type = type; }},
  });
  await Promise.resolve();
  assert.deepEqual(shown, []);
  wizardReady = false;
  pending.shift()();
  await Promise.resolve();
  assert.deepEqual(shown, []);
  wizardReady = true;
  onMutation();
  for (let tries = 0; !finished && tries < 20; tries++) {
    if (pending.length) pending.shift()();
    await Promise.resolve();
  }
  await done;
  assert.deepEqual(shown, [0, 1, 2]);
});

test('intro continues across a new page context instead of starting over', async () => {
  const saved = new Map();
  const localStorage = {
    getItem: key => saved.get(key),
    setItem: (key, value) => saved.set(key, value),
  };
  let now = 100000;
  const run = (shown, setTimeout, done) => {
    const frames = Array.from({length: 3}, (_, index) => ({
      classList: {add(name) { if (name === 'is-visible') shown.push(index); }, remove() {}},
      setAttribute() {},
    }));
    const intro = {classList: {add() {}}, querySelectorAll: () => frames, remove() {}};
    const app = {inert: false};
    vm.runInNewContext(source, {
      document: {querySelector: selector => selector === '#infinityos-installer-intro'
        ? intro : selector === '#app' ? app : {}},
      window: {localStorage, sessionStorage: {getItem: () => null},
        dispatchEvent: event => { if (event.type === 'infinityos-installer-intro-complete') done(); }},
      Date: {now: () => now},
      matchMedia: () => ({matches: false}),
      setTimeout,
      Event: class {constructor(type) { this.type = type; }},
    });
  };
  const first = [];
  run(first, (callback, delay) => { if (delay <= 1500) queueMicrotask(callback); return 1; }, () => {});
  for (let i = 0; i < 8; i++) await Promise.resolve();
  assert.deepEqual(first, [0]);
  now += 3500;
  const second = [];
  let complete;
  const done = new Promise(resolve => { complete = resolve; });
  run(second, (callback, delay) => { now += delay; queueMicrotask(callback); return 1; }, complete);
  await done;
  assert.deepEqual(second, [1, 2]);
  const completed = [];
  await new Promise(resolve => run(completed, (callback, delay) => {
    now += delay;
    queueMicrotask(callback);
    return 1;
  }, resolve));
  assert.deepEqual(completed, []);
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
  const window = { dispatchEvent: event => { if (event.type === 'infinityos-installer-intro-complete') completed(); } };
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
