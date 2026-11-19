import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/ramdriveRestart.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');

function fixture(type = 2, occupied = true, run = async () => {}) {
    const signals = new Map(), confirmations = [], actions = [];
    let id = 0;
    const layout = {x_align: 1, y_align: 1, margin_top: 0, margin_left: 0, margin_right: 0, width: -1,
        translation_x: 0, translation_y: 0,
        get_transformed_position() {return [420 + this.translation_x, 295 + this.translation_y];},
        get_transformed_size: () => [440, 210], connect: () => 99, disconnect() {},
        add_style_class_name() {}, remove_style_class_name() {}, add_action() {}, remove_action() {}};
    const dialog = {_type: type, dialogLayout: {...layout, _dialog: layout}, _altCapture: {}, _messageDialogContent: {},
        _updateButtons() {actions.push('normal buttons');}, _sync() {},
        _startTimer() {actions.push('timer');}, _stopTimer() {actions.push('stopped');},
        _stopAltCapture() {}, clearButtons() {},
        addButton(info) {return {reactive: true, can_focus: true, ...info};},
        setInitialKeyFocus(button) {this.focus = button;},
        async _confirm(signal) {confirmations.push(signal);},
        open() {}, cancel() {this.emit('closed');},
        connect(signal, callback) {signals.set(++id, [signal, callback]); return id;},
        disconnect(key) {signals.delete(key);},
        emit(signal) {for (const [name, callback] of signals.values()) if (name === signal) callback();},
    };
    const original = dialog._confirm;
    class InjectionManager {
        changes = [];
        overrideMethod(object, name, create) {const method = object[name]; this.changes.push([object, name, method]); object[name] = create(method);}
        clear() {for (const [object, name, method] of this.changes.reverse()) object[name] = method;}
    }
    const Class = vm.runInNewContext(`${source}\nRamdriveRestart`, {
        InjectionManager, GLib: {get_language_names: () => ['en_US']},
        Clutter: {ActorAlign: {END: 2, START: 0}, KEY_Escape: 27, EVENT_PROPAGATE: 0, EVENT_STOP: 1,
            KeyController: class {connect() {return 1;} disconnect() {} }},
        Main: {panel: {height: 32}, layoutManager: {monitors: [{x: 0, y: 0, width: 1280}]}},
        global: {display: {get_current_monitor: () => 0}},
    });
    const controller = new Class(dialog, () => occupied, run);
    return {dialog, controller, confirmations, actions, signals, original,
        empty: () => {occupied = false;}};
}

test('restart has two choices at upper right and no countdown or automatic confirm', async () => {
    const f = fixture();
    f.dialog._updateButtons(); f.dialog._sync(); f.dialog._startTimer();
    assert.equal(f.controller.buttons.map(button => button.label).join('|'), 'Remove & Restart|Save files');
    assert.equal(f.dialog.dialogLayout.x_align, 2);
    assert.equal(f.dialog.dialogLayout.y_align, 0);
    assert.equal(f.dialog.dialogLayout.margin_top, 48);
    assert.equal(f.dialog._messageDialogContent.title, 'There are files in your RAMDrive.');
    assert.deepEqual(f.dialog.dialogLayout._dialog.get_transformed_position(), [824, 48]);
    assert.equal(f.dialog.focus.label, 'Save files');
    assert.equal(f.actions.includes('timer'), false);
    await f.dialog._confirm('ConfirmedReboot');
    assert.deepEqual(f.confirmations, []);
});

for (const action of ['clear', 'save']) {
    test(`${action} finishes successfully before GNOME receives the reboot signal`, async () => {
        let release;
        const calls = [];
        const f = fixture(3, true, command => {calls.push(command); return new Promise(resolve => {release = resolve;});});
        f.dialog._updateButtons();
        const work = f.controller.prepare(action);
        await f.controller.prepare(action);
        assert.deepEqual(calls, [action]);
        assert.equal(f.controller.buttons.every(button => !button.reactive), true);
        assert.deepEqual(f.confirmations, []);
        f.empty(); release(); await work;
        assert.deepEqual(f.confirmations, ['ConfirmedReboot']);
    });
}

test('save failure or remaining files stops restart and leaves choices usable', async () => {
    for (const run of [async () => {throw new Error('disk full');}, async () => {}]) {
        const f = fixture(2, true, run);
        f.dialog._updateButtons();
        await f.controller.prepare('save');
        assert.deepEqual(f.confirmations, []);
        assert.equal(f.controller.buttons.every(button => button.reactive), true);
        assert.match(f.dialog._messageDialogContent.description, /^Restart stopped\./);
    }
});

test('cancel or extension disable during saving cannot later restart the system', async () => {
    for (const destroy of [false, true]) {
        let release;
        const f = fixture(2, true, () => new Promise(resolve => {release = resolve;}));
        f.dialog._updateButtons();
        const work = f.controller.prepare('save');
        if (destroy) f.controller.destroy(); else f.dialog.cancel();
        f.empty(); release(); await work;
        assert.deepEqual(f.confirmations, []);
        assert.equal(f.dialog.dialogLayout.width, -1);
        if (destroy) {assert.equal(f.signals.size, 0); assert.equal(f.dialog._confirm, f.original);}
    }
});

test('empty RAMDrive and other shutdown types retain the normal dialog', async () => {
    for (const [type, occupied] of [[2, false], [0, true], [1, true]]) {
        const f = fixture(type, occupied);
        f.dialog._updateButtons(); f.dialog._startTimer();
        assert.equal(f.controller.active, false);
        assert.equal(f.actions.includes('normal buttons'), true);
        assert.equal(f.actions.includes('timer'), true);
    }
});
