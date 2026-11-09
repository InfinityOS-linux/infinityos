import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';
const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/warpButton.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export function', 'function');
function setup(installed = true) {
    const state = {activations: 0, errors: 0};
    class Button {
        add_child(icon) {this.icon = icon;}
        add_action(action) {this.action = action;}
        connect(_signal, callback) {this.key = callback;}
    }
    const context = {
        Atk: {Role: {PUSH_BUTTON: 1}},
        PanelMenu: {Button}, St: {Icon: class {constructor(props) {Object.assign(this, props);}}},
        Gio: {icon_new_for_string: path => path},
        Clutter: {KEY_Return: 13, KEY_KP_Enter: 14, KEY_space: 32, EVENT_PROPAGATE: false, EVENT_STOP: true,
            ClickGesture: class {set_recognize_on_press() {} connect(_signal, callback) {this.click = callback;}}},
        Shell: {AppSystem: {get_default: () => ({lookup_app(id) {
            assert.equal(id, 'app.drey.Warp.desktop');
            return installed ? {activate() {state.activations++;}} : null;
        }})}},
        Main: {notifyError() {state.errors++;}},
    };
    return {state, button: vm.runInNewContext(`${source}\ncreateWarpButton('/extension')`, context)};
}
test('Warp panel opens the app on click and keyboard activation', () => {
    const {state, button} = setup();
    assert.equal(state.activations, 0);
    assert.equal(button.icon.gicon, '/extension/icons/warp-symbolic.svg');
    button.action.click();
    for (const key of [13, 14, 32]) assert.equal(button.key(null, {get_key_symbol: () => key}), true);
    assert.equal(button.key(null, {get_key_symbol: () => 27}), false);
    assert.equal(state.activations, 4);
});
test('missing Warp reports an error without crashing the panel', () => {
    const {state, button} = setup(false);
    button.action.click();
    assert.equal(state.errors, 1);
});
