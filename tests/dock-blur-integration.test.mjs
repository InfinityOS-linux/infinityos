import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/integrations.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export const Integrations', 'const Integrations');

function fixture() {
    const overview = {visible: false};
    const settings = {dash_to_dock: {UNBLUR_IN_OVERVIEW: false}};
    const bridge = {update_size() {}};
    const Class = vm.runInNewContext(`${source}\nIntegrations`, {
        Main: {overview, extensionManager: {lookup: () => ({metadata: {version: 75}, stateObj: {_dash_to_dock_blur: bridge}})}},
        global: {blur_my_shell: {_settings: settings}},
    });
    const integration = new Class();
    const background = {visible: false, get_name: () => 'bms-dash-backgroundgroup', _infinityPanelBackdrop: {destroyed: false}};
    const animator = {dock: {get_children: () => [background]}};
    integration.extension = {docks: [{animator}], blur_background: true};
    return {integration, background, animator, overview, settings, bridge};
}

test('animation keeps a valid matching blur visible and hides destroyed or fallback surfaces', () => {
    const f = fixture();
    f.integration.bms_update_size(f.animator);
    assert.equal(f.background.visible, true);
    assert.equal(f.animator._bms, f.background);
    f.background._infinityPanelBackdrop.destroyed = true;
    f.integration.bms_update_size(f.animator);
    assert.equal(f.background.visible, false);
    delete f.background._infinityPanelBackdrop;
    f.integration.bms_update_size(f.animator);
    assert.equal(f.background.visible, false);
});

test('animation preserves the user preference to hide blur in overview', () => {
    const f = fixture();
    f.overview.visible = true;
    f.settings.dash_to_dock.UNBLUR_IN_OVERVIEW = true;
    f.integration.bms_update_size(f.animator);
    assert.equal(f.background.visible, false);
    f.overview.visible = false;
    f.integration.bms_update_size(f.animator);
    assert.equal(f.background.visible, true);
});

test('integration restores an old geometry override and never disables BMS geometry updates', () => {
    const f = fixture();
    const original = () => {};
    f.bridge.update_size_orig = original;
    f.integration.hookBms();
    assert.equal(f.bridge.update_size, original);
    assert.equal('update_size_orig' in f.bridge, false);
    f.integration.hookBms();
    assert.equal(f.bridge.update_size, original);
    f.integration.releaseBms();
    assert.equal(f.bridge.update_size, original);
});
