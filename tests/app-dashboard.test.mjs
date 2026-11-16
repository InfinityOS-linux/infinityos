import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/appDashboard.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export function', 'function')
    .replace('export default class', 'class');
class Button {}
class Entry {}
const Clutter = {ShaderEffect: class {}, EventType: {BUTTON_PRESS: 1, BUTTON_RELEASE: 2},
    EVENT_PROPAGATE: 0, EVENT_STOP: 1, PickMode: {REACTIVE: 1}};
let hidden = 0;
let picked;
const Main = {overview: {visible: true, hide: () => hidden++}};
const {isEmptyDashboardTarget, AppDashboard} = runInNewContext(`${source}\n({isEmptyDashboardTarget, AppDashboard})`, {
    Clutter, St: {Button, Entry}, GObject: {registerClass: c => c}, Main,
    global: {stage: {get_actor_at_pos: () => picked}},
});
const controls = {get_parent: () => null, dash: {showAppsButton: {checked: true}},
    _appDisplay: {get_parent: () => controls}, _thumbnailsBox: {get_parent: () => controls}};
const background = {get_parent: () => controls._appDisplay};

test('empty app-grid space dismisses but interactive descendants are excluded', () => {
    assert.equal(isEmptyDashboardTarget(background, controls), true);
    for (const parent of [Object.assign(new Button(), {get_parent: () => controls._appDisplay}),
        Object.assign(new Entry(), {get_parent: () => controls}), controls._thumbnailsBox,
        {can_focus: true, get_parent: () => controls}]) {
        assert.equal(isEmptyDashboardTarget({get_parent: () => parent}, controls), false);
    }
    assert.equal(isEmptyDashboardTarget({get_parent: () => null}, controls), false);
});

test('only a stationary left background click closes the app grid', () => {
    const dashboard = Object.create(AppDashboard.prototype);
    dashboard._controls = controls;
    const event = (type, x = 10, button = 1) => ({type: () => type,
        get_coords: () => [x, 10], get_button: () => button});
    picked = background;
    dashboard._onEvent(event(1));
    assert.equal(dashboard._onEvent(event(2)), 1);
    assert.equal(hidden, 1);
    dashboard._onEvent(event(1));
    dashboard._onEvent(event(2, 80));
    dashboard._onEvent(event(1, 10, 3));
    dashboard._onEvent(event(2, 10, 3));
    controls._appDisplay._displayingDialog = true;
    dashboard._onEvent(event(1));
    dashboard._onEvent(event(2));
    controls._appDisplay._displayingDialog = false;
    controls.dash.showAppsButton.checked = false;
    dashboard._onEvent(event(1));
    dashboard._onEvent(event(2));
    assert.equal(hidden, 1);
});
