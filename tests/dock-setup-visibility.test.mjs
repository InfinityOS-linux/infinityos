import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/autohide.js', import.meta.url), 'utf8');
const launcherMethod = source.slice(source.indexOf('  _launcherOpen() {'), source.indexOf('\n\n  _installerOpen() {'));
const installerMethod = source.slice(source.indexOf('  _installerOpen() {'), source.indexOf('\n\n  _track(window) {'));
const checkMethod = source.slice(source.indexOf('  _checkHide() {'), source.lastIndexOf('\n};'));
const launcherOpen = new Function('Shell', 'LAUNCHER_APP_IDS', 'global', `return ({${launcherMethod}})._launcherOpen`)({
  WindowTracker: {get_default: () => ({get_window_app: () => ({get_id: () => 'org.infinityos.Setup.desktop'})})},
}, new Set(['org.infinityos.Setup.desktop']), {
  get_window_actors: () => [{visible: true, get_meta_window: () => ({
    minimized: false,
    showing_on_its_workspace: () => true,
    get_gtk_application_id: () => 'org.infinityos.Setup',
  })}],
});
const checkHide = new Function(`return ({${checkMethod}})._checkHide`)();

test('InfinitySetup is detected in a Live session and hides the dock until close', () => {
  assert.equal(launcherOpen(), true);
  const dock = {visible: true};
  const autohider = {_installerOpen: () => false, _launcherOpen: () => true, dock};
  checkHide.call(autohider);
  assert.equal(dock.visible, false);
  autohider._launcherOpen = () => false;
  autohider._enabled = false;
  autohider.show = () => {};
  checkHide.call(autohider);
  assert.equal(dock.visible, true);
});

test('closed installer window restores the Live dock', () => {
  let visible = true;
  const installerOpen = new Function('IS_LIVE_SESSION', 'Shell', 'global', `return ({${installerMethod}})._installerOpen`)(true, {
    WindowTracker: {get_default: () => ({get_window_app: () => ({get_id: () => 'liveinst.desktop'})})},
  }, {
    get_window_actors: () => [{get visible() { return visible; }, get_meta_window: () => ({
      minimized: false, showing_on_its_workspace: () => true, get_wm_class: () => 'liveinst',
    })}],
  });
  const dock = {visible: true};
  let shown = false;
  const autohider = {_installerOpen: installerOpen, _launcherOpen: () => false, _enabled: false,
    dock, show: () => { shown = true; }};
  checkHide.call(autohider);
  assert.equal(dock.visible, false);
  visible = false;
  checkHide.call(autohider);
  assert.equal(dock.visible, true);
  assert.equal(shown, true);
});
