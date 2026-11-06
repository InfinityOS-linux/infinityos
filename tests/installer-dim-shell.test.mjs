import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/installerDim.js', import.meta.url), 'utf8')
  .replace(/^import .*;\n/gm, '')
  .replace('export default class InstallerDim', 'class InstallerDim');

test('installer dim follows the live marker and is removed after exit', () => {
  let running = true;
  let deleted = false;
  let parent;
  const monitor = { connectObject() {}, disconnectObject() {}, cancel() {} };
  const runtime = {
    monitor_directory: () => monitor,
    enumerate_children: () => {
      let next = true;
      return { next_file: () => next ? (next = false, { get_name: () => 'infinityos-liveinst-dim-123' }) : null,
        close() {} };
    },
    get_child: () => ({ delete() { deleted = true; } }),
  };
  class Widget {
    set_size(width, height) { this.size = [width, height]; }
    get_parent() { return parent; }
    ease(options) { options.onComplete?.(); }
    destroy() { this.destroyed = true; }
  }
  const group = {
    add_child(actor) { parent = group; this.actor = actor; },
    set_child_above_sibling() {},
    set_child_below_sibling(_actor, sibling) { this.below = sibling; },
  };
  const focused = { get_parent: () => group };
  const global = {
    window_group: group,
    display: { focus_window: { get_compositor_private: () => focused }, connectObject() {}, disconnectObject() {} },
    stage: { width: 1200, height: 800, connectObject() {}, disconnectObject() {} },
  };
  const context = {
    Gio: { File: { new_for_path: () => runtime }, FileMonitorFlags: { NONE: 0 }, FileQueryInfoFlags: { NONE: 0 } },
    GLib: { get_user_runtime_dir: () => '/run/user/1000', file_test: () => running,
      FileTest: { EXISTS: 1 }, PRIORITY_DEFAULT: 0, timeout_add_seconds: () => 1,
      source_remove() {}, SOURCE_CONTINUE: true, SOURCE_REMOVE: false },
    St: { Widget }, Clutter: { AnimationMode: { EASE_OUT_QUAD: 1 } },
    Main: { sessionMode: { currentMode: 'user', connectObject() {}, disconnectObject() {} } },
    global,
  };
  const InstallerDim = vm.runInNewContext(`${source}\nInstallerDim`, context);
  const dim = new InstallerDim();
  assert.deepEqual(dim._dim.size, [1200, 800]);
  assert.equal(group.below, focused);
  const installer = { get_parent: () => group };
  global.display.focus_window = { get_compositor_private: () => installer };
  dim._sync();
  assert.equal(group.below, installer);
  running = false;
  dim._sync();
  assert.equal(dim._dim, null);
  assert.equal(group.actor.destroyed, true);
  assert.equal(deleted, true);
  dim.destroy();
});
