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
  let redraws = 0;
  const dock = {visible: true, _beginAnimation: () => { redraws++; }};
  const autohider = {_installerOpen: () => false, _launcherOpen: () => true, dock};
  checkHide.call(autohider);
  assert.equal(dock.visible, false);
  autohider._launcherOpen = () => false;
  autohider._enabled = false;
  autohider.show = () => {};
  checkHide.call(autohider);
  assert.equal(dock.visible, true);
  assert.equal(redraws, 1);
});

test('returning to the Live desktop redraws the dock even while the installer actor remains', () => {
  const installerWindow = {
    minimized: false, showing_on_its_workspace: () => true, get_wm_class: () => 'liveinst',
  };
  const guest = {
    display: {focus_window: installerWindow},
    get_window_actors: () => [{visible: true, get_meta_window: () => installerWindow}],
  };
  const installerOpen = new Function('IS_LIVE_SESSION', 'Shell', 'global', `return ({${installerMethod}})._installerOpen`)(true, {
    WindowTracker: {get_default: () => ({get_window_app: () => ({get_id: () => 'liveinst.desktop'})})},
  }, guest);
  let redraws = 0;
  const dock = {visible: true, _beginAnimation: () => { redraws++; }};
  let shown = false;
  const autohider = {_installerOpen: installerOpen, _launcherOpen: () => false, _enabled: true,
    _checkOverlap: () => false, dock, show: () => { shown = true; }};
  checkHide.call(autohider);
  assert.equal(dock.visible, false);
  guest.display.focus_window = null;
  checkHide.call(autohider);
  assert.equal(dock.visible, true);
  assert.equal(shown, true);
  assert.equal(redraws, 1);
});
