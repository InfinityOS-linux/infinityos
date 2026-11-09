import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const base = '../vendor/gnome-shell/fedora-45/usr/share/gnome-shell/extensions/vertical-workspaces@G-dH.github.com/';
const source = readFileSync(new URL(`${base}extension.js`, import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '')
    .replace('export default class VShell', 'class VShell');

function startup(failActivation = false) {
    const idle = [];
    const signals = new Map();
    const settings = {slow_down_factor: 1};
    let ready;
    class Actor {
        constructor(props) { Object.assign(this, props); }
        add_constraint(constraint) { this.constraint = constraint; }
        ease(options) { this.animation = options; }
        destroy() { this.destroyed = true; }
    }
    const stage = {add_child(actor) { this.cover = actor; }};
    const context = {
        Extension: {Extension: class {}},
        Clutter: {Actor, Color: class {}, BindConstraint: class {
            constructor(props) { Object.assign(this, props); }
        }, BindCoordinate: {ALL: 1}, AnimationMode: {EASE_OUT_QUAD: 1}},
        St: {Settings: {get: () => settings}},
        GLib: {PRIORITY_LOW: 1, SOURCE_REMOVE: false, idle_add(_priority, callback) {
            idle.push(callback); return idle.length;
        }},
        global: {stage, screen_width: 1920, screen_height: 1080},
        Main: {
            layoutManager: {uiGroup: {opacity: 0}, connect(name, callback) {
                signals.set(name, callback); return 1;
            }, disconnect() {}},
            overview: {_overview: {controls: {realizeAppDisplayAndFinishStartup(callback) { ready = callback; }}}},
            extensionManager: {_extensionOrder: ['vshell', 'other']},
        },
        logError() {},
    };
    const extension = vm.runInNewContext(`${source}\nMe = {run: {timeouts: {}}}; new VShell()`, context);
    extension.metadata = {uuid: 'vshell'};
    extension._activateVShell = () => {
        settings.slow_down_factor = 1;
        if (failActivation) throw new Error('Activation failed');
    };
    extension._activateVShellOnStartup();
    return {extension, stage, idle, signals, ready: () => ready()};
}

test('startup cover stays above the fading UI until V-Shell is ready, then fades once', () => {
    const s = startup();
    const cover = s.stage.cover;
    assert.equal(cover, s.extension._screenCover);
    assert.equal(cover.constraint.source, s.stage);
    s.signals.get('startup-complete')();
    s.idle.shift()();
    s.idle.shift()();
    assert.equal(cover.destroyed, undefined);
    assert.equal(cover.animation, undefined);
    s.ready();
    assert.equal(cover.animation.opacity, 0);
    assert.equal(cover.animation.duration, 600);
    cover.animation.onComplete();
    assert.equal(cover.destroyed, true);
    assert.equal(s.extension._screenCover, null);
});

test('activation failure releases the black cover instead of trapping the user', () => {
    const s = startup(true);
    s.signals.get('startup-complete')();
    s.idle.shift()();
    assert.equal(s.stage.cover.animation.opacity, 0);
    s.stage.cover.animation.onComplete();
    assert.equal(s.extension._screenCover, null);
});

const controls = readFileSync(new URL(`${base}lib/overviewControls.js`, import.meta.url), 'utf8');
const method = controls.slice(controls.indexOf('    realizeAppDisplayAndFinishStartup('), controls.indexOf('    _finishStartupSequence() {'));
for (const enabled of [false, true]) {
    test(`ready callback follows app-grid preparation (enabled=${enabled})`, () => {
        let populate;
        const order = [];
        const obj = vm.runInNewContext(`({${method}})`, {
            Me: {Modules: {appDisplayModule: {enabled, _repopulateAppDisplay(_reset, callback) { populate = callback; }}}},
        });
        obj._finishStartupSequence = () => order.push('finish');
        obj.realizeAppDisplayAndFinishStartup(() => order.push('reveal'));
        if (enabled) {
            assert.deepEqual(order, []);
            populate();
        }
        assert.deepEqual(order, ['finish', 'reveal']);
    });
}
