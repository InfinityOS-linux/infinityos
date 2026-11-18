import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../vendor/gnome-shell/fedora-45/usr/share/gnome-shell/extensions/blur-my-shell@aunetx/components/panel.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export const PanelBlur =', 'const PanelBlur =');

function fixture(staticBlur) {
    const resources = [];
    class Pipeline {
        constructor(effects, manager, preset) { this.effects = effects; this.manager = manager; this.preset = preset; }
        create_background_with_effects(index, managers, container, name, absolute) {
            const widget = {y: .01, destroyed: 0, destroy() {this.destroyed++;}};
            const manager = {destroyed: 0, destroy() {this.destroyed++;}};
            resources.push({pipeline: this, widget, manager, index, container, name, absolute});
            managers.push(manager); return widget;
        }
        destroy() { this.destroyed = (this.destroyed ?? 0) + 1; }
    }
    class DummyPipeline extends Pipeline {
        constructor(effects, settings, actor, options) { super(effects); Object.assign(this, {settings, options}); }
        create_background_with_effect(container, name) {
            const managers = [];
            return [this.create_background_with_effects(null, managers, container, name), managers[0]];
        }
    }
    const manager = {}, effects = {}, settings = {DEBUG: false,
        panel: {STATIC_BLUR: staticBlur, PIPELINE: 'same-as-panel', SIGMA: 28, BRIGHTNESS: .64}};
    const Controller = vm.runInNewContext(`${source}\nPanelBlur`, {
        Pipeline, DummyPipeline, global: {blur_my_shell: {_pipelines_manager: manager}}, console,
    });
    const blur = new Controller({disconnect_all() {}}, settings, effects);
    blur.enabled = true;
    blur.disconnect_from_windows_and_overview = () => {};
    blur.update_light_text_classname = () => {};
    return {blur, settings, resources, manager, effects};
}

test('static backdrop shares the panel preset, not effect instances, and releases all resources', () => {
    const f = fixture(true);
    const first = f.blur.createMatchingBackdrop({}, 1);
    const second = f.blur.createMatchingBackdrop({}, 0);
    assert.equal(f.resources[0].pipeline.preset, 'same-as-panel');
    assert.equal(f.resources[0].pipeline.manager, f.manager);
    assert.equal(f.resources[0].pipeline.effects, f.effects);
    assert.equal(f.resources[0].absolute, false);
    assert.equal(f.resources[0].index, 1);
    assert.notEqual(first.background, second.background);
    first.destroy(); first.destroy();
    assert.equal(f.resources[0].widget.destroyed, 1);
    assert.equal(f.resources[0].manager.destroyed, 1);
    assert.equal(f.resources[0].pipeline.destroyed, 1);
    f.blur.disable();
    assert(second.destroyed);
    assert.equal(f.blur._matchingBackdrops.size, 0);
    assert.equal(f.blur.createMatchingBackdrop({}, 0), null);
});

test('dynamic backdrop follows the panel sigma and brightness with square drawer corners', () => {
    const f = fixture(false);
    const backdrop = f.blur.createMatchingBackdrop({}, 0);
    assert.equal(backdrop.staticBlur, false);
    assert.equal(f.resources[0].pipeline.settings, f.settings.panel);
    assert.equal(f.resources[0].pipeline.options.corner_radius_getter(), 0);
    backdrop.destroy(); assert.equal(f.blur._matchingBackdrops.size, 0);
});
