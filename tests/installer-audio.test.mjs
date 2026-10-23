import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/cockpit/anaconda-webui/infinityos-installer-audio.js', import.meta.url), 'utf8');

test('installer music starts once when Welcome appears and survives later steps', () => {
  let welcomeVisible = false;
  let playCount = 0;
  const observers = [];
  const appended = [];

  class Element {
    constructor(tag) {
      this.tag = tag;
      this.hidden = false;
      this.paused = true;
      this.currentTime = 0;
      this.listeners = {};
      this.classList = { toggle() {} };
    }
    addEventListener(type, callback) {
      (this.listeners[type] ??= []).push(callback);
    }
    setAttribute() {}
    contains() { return false; }
    querySelector() { return new Element('control'); }
    play() {
      playCount++;
      this.paused = false;
      return Promise.resolve();
    }
    pause() { this.paused = true; }
  }

  const document = {
    currentScript: { src: 'https://installer.test/infinityos-installer-audio.js' },
    body: { append: element => appended.push(element) },
    listeners: {},
    createElement: tag => new Element(tag),
    querySelector: () => welcomeVisible ? {} : null,
    addEventListener(type, callback) {
      (this.listeners[type] ??= []).push(callback);
    },
    removeEventListener() {},
    documentElement: { lang: 'pl' },
  };
  const window = { addEventListener() {} };
  class FakeObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() {}
    disconnect() { this.disconnected = true; }
  }
  const context = { document, window, navigator: { language: 'pl' },
    MutationObserver: FakeObserver, URL, setInterval: () => 1, clearInterval() {} };

  vm.runInNewContext(source, context);
  const audio = appended.find(element => element.tag === 'audio');
  const controls = appended.find(element => element.tag === 'div');
  assert.equal(playCount, 0);
  assert.equal(audio.preload, 'none');
  assert.equal(controls.hidden, true);

  document.listeners.pointerdown.at(-1)();
  assert.equal(playCount, 0);

  welcomeVisible = true;
  observers[0].callback();
  assert.equal(playCount, 1);
  assert.equal(audio.preload, 'auto');
  assert.equal(controls.hidden, false);
  assert.equal(observers[0].disconnected, true);

  welcomeVisible = false;
  document.listeners.pointerdown.at(-1)();
  vm.runInNewContext(source, context);
  assert.equal(playCount, 1);
  assert.equal(audio.paused, false);
  assert.equal(appended.length, 2);
});
