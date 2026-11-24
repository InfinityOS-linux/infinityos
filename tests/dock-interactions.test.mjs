import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js', import.meta.url), 'utf8');
const get = (name, next) => {
  const start = source.indexOf(`    ${name}(`);
  const end = source.indexOf(next, start);
  return source.slice(start, end);
};
const workspace = {};
const modifier = {SHIFT_MASK: 1, CONTROL_MASK: 4};
const env = {workspace_manager: {get_active_workspace: () => workspace}};
const shell = {AppState: {RUNNING: 2}};
let state;
const click = new Function('Clutter', 'Shell', 'Meta', 'global', `return ({${get('_maybeMinimizeOrMaximize', '    _pauseAllBounce(')}})._maybeMinimizeOrMaximize`)(
  {ModifierType: modifier, get_current_event: () => ({get_state: () => state})}, shell, {MaximizeFlags: {BOTH: 3}}, env,
);

test('dock click uses the native maximize signature and acts only on current, open workspace windows', () => {
  const events = [];
  const makeWindow = (name, {focused = false, local = true} = {}) => ({
    has_focus: () => focused, located_on_workspace: value => local && value === workspace,
    can_minimize: () => true, minimize: () => events.push(name),
    get_maximize_flags: () => 3, is_maximized: () => true,
    unmaximize: (...args) => { assert.equal(args.length, 0); events.push('unmaximized'); },
  });
  const focused = makeWindow('focused', {focused: true});
  const closed = makeWindow('closed');
  const elsewhere = makeWindow('elsewhere', {local: false});
  const other = makeWindow('other');
  let windows = [focused, closed, elsewhere, other];
  const actions = [];
  const dock = {dash: {}, getAppWindowsFiltered: () => windows,
    extension: {_hiTimer: {runOnce: callback => actions.push(callback)}}};
  const app = {get_windows: () => windows, state: shell.AppState.RUNNING, can_open_new_window: () => true};
  state = modifier.SHIFT_MASK;
  click.call(dock, app);
  actions.shift()();
  state = 0;
  click.call(dock, app);
  windows = [focused, elsewhere, other];
  actions.shift()();
  assert.deepEqual(events, ['unmaximized', 'focused', 'other']);
  click.call(dock, app, 2);
  state = modifier.CONTROL_MASK;
  click.call(dock, app);
  assert.equal(actions.length, 0);
});

test('scrolling selects a single window, and Control limits selection to the active workspace', () => {
  const cycle = new Function('Clutter', 'global', `return ({${get('_cycleWindows', '\n  }\n);')}})._cycleWindows`)(
    {ModifierType: modifier}, env);
  const windows = [3, 2, 1].map(id => ({
    get_id: () => id, has_focus: () => id === 3,
    located_on_workspace: ws => ws === workspace && id !== 2,
    unminimize() { assert.fail('scrolling must not unminimize all windows'); },
  }));
  const activated = [];
  const dock = {getAppWindowsFiltered: () => [...windows], _scrollCounter: 1.2,
    _lockCycle() {}, _raiseAndFocus: window => activated.push(window.get_id())};
  cycle.call(dock, {}, {get_state: () => 0});
  dock._scrollCounter = 1.2;
  cycle.call(dock, {}, {get_state: () => modifier.CONTROL_MASK});
  assert.deepEqual(activated, [2, 1]);
});

test('unmounting a drive destroys the icon and its open popup', () => {
  const remove = new Function(`return ({${get('_removeExtraIcon', '    _orderExtraIcons(')}})._removeExtraIcon`)();
  const closed = [];
  const drive = {destroy() { closed.push('icon'); }};
  const dock = {_list: {_target: drive}, _icons: [drive], _destroyList() { closed.push('popup'); }};
  remove.call(dock, drive);
  assert.deepEqual(closed, ['popup', 'icon']);
  assert.equal(dock._icons, null);
});
