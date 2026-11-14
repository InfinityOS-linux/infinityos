import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');

function startup(username, initial = 0, fail = false) {
    const callbacks = new Map();
    const values = new Map([['toggle-request', initial], ['show-request', initial]]);
    const settings = {set_boolean() {}, get_int64: key => values.get(key),
        connect(signal, callback) { callbacks.set(signal, callback); return signal; }};
    class Widget { connect() {} add_child() {} add_action() {} set_recognize_on_press() {} }
    class AppSystem { get_running() { return []; } }
    class Workspace { _isOverviewWindow() { return true; } }
    let starts = 0, errors = 0;
    const context = vm.createContext({
        Extension: class {getSettings() { return settings; }},
        HardwareMonitor: class {},
        Atk: {Role: {}}, St: {Icon: Widget, Widget}, PanelMenu: {Button: Widget},
        Clutter: {ClickGesture: Widget}, Meta: {KeyBindingFlags: {}},
        GLib: {get_user_name: () => username},
        Gio: {icon_new_for_string: path => ({path}), Settings: class {}, Subprocess: {new() { starts++; return {wait_check_async(_cancel, done) {done({wait_check_finish() {if (fail) throw new Error("service failed");}}, {});}}; }}, SubprocessFlags: {}},
        Shell: {AppSystem, ActionMode: {}}, Workspace: {Workspace},
        Main: {notifyError() {errors++;}, layoutManager: {addChrome() {}}, overview: new Widget(), panel: {addToStatusArea() {}}, wm: {addKeybinding() {}}},
        global: {stage: new Widget(), display: new Widget(), get_window_actors: () => []},
    });
    vm.runInContext(source + '\nglobalThis.controller = new InfinityTerminal(); controller.enable();', context);
    return {get errors() {return errors;}, get starts() { return starts; }, request(key, value) {
        values.set(key, value);
        callbacks.get('changed::' + key)();
    }};
}

test('enabling the terminal never launches it for live or installed accounts', () => {
    for (const user of ['liveuser', 'guest', 'owner'])
        assert.equal(startup(user).starts, 0, user);
});

test('initial, repeated and reset request values cannot open the terminal', () => {
    for (const key of ['toggle-request', 'show-request']) {
        for (const initial of [0, 123]) {
            const f = startup('liveuser', initial);
            f.request(key, initial);
            f.request(key, 0);
            assert.equal(f.starts, 0);
            f.request(key, 456);
            assert.equal(f.starts, 1);
            f.request(key, 456);
            assert.equal(f.starts, 1);
        }
    }
});

test('service launch failure is reported to the user', () => {
    const f = startup('owner', 0, true);
    f.request('toggle-request', 10);
    assert.equal(f.starts, 1);
    assert.equal(f.errors, 1);
});
