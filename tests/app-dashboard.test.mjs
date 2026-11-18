import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/appDashboard.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export function', 'function')
    .replace('export default class', 'class');
class Button {}
class Entry {}
const Clutter = {ShaderEffect: class {
    constructor() {
        this.uniforms = new Map();
        this._init();
        this.snippet = this.vfunc_get_static_snippet();
    }
    _init(...args) { assert.equal(args.length, 0); }
    set_uniform_value(name, value) { this.uniforms.set(name, value); }
}, EventType: {BUTTON_PRESS: 1, BUTTON_RELEASE: 2},
    EVENT_PROPAGATE: 0, EVENT_STOP: 1, PickMode: {REACTIVE: 1}};
let hidden = 0;
let picked;
const Main = {overview: {visible: true, hide: () => hidden++}};
const {isEmptyDashboardTarget, AppDashboard} = runInNewContext(`${source}\n({isEmptyDashboardTarget, AppDashboard})`, {
    Clutter, Cogl: {SnippetHook: {FRAGMENT: 1}, Snippet: {
        new(hook, declarations, post) { return {hook, declarations, post}; },
    }},
    St: {Button, Entry, ThemeContext: {get_for_stage: () => ({scale_factor: 2})}},
    GObject: {registerClass: c => c}, Main,
    global: {stage: {get_actor_at_pos: () => picked}},
});

test('preview construction works without legacy shader API and keeps mask uniforms current', () => {
    const callbacks = new Map();
    let additions = 0;
    const actor = {width: 240, height: 150,
        add_effect_with_name(name, effect) {
            assert.equal(name, 'infinity-rounded-preview');
            this.effect = effect; additions++;
        },
        connectObject(...args) {
            for (let i = 0; i < args.length - 1; i += 2)
                callbacks.set(args[i], args[i + 1]);
        },
    };
    const dashboard = Object.create(AppDashboard.prototype);
    dashboard._previews = new Map();
    dashboard._box = {_thumbnails: [actor]};
    dashboard._syncPreviews();
    const {snippet, uniforms} = actor.effect;
    assert.equal(snippet.hook, 1);
    assert.match(snippet.declarations, /uniform float radius/);
    assert.match(snippet.post, /cogl_color_out \*= alpha/);
    assert.equal(uniforms.get('width'), 240.0001);
    assert.equal(uniforms.get('height'), 150.0001);
    assert.equal(uniforms.get('radius'), 24.0001);
    actor.width = 0; actor.height = 300;
    callbacks.get('notify::width')();
    callbacks.get('notify::height')();
    assert.equal(uniforms.get('width'), 1.0001);
    assert.equal(uniforms.get('height'), 300.0001);
    dashboard._syncPreviews();
    assert.equal(additions, 1);
    callbacks.get('destroy')();
    assert.equal(dashboard._previews.size, 0);
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
