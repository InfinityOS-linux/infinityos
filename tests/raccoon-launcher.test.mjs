import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('GNOME 51 launcher constructs, toggles and releases modal focus on Escape', () => {
    class Actor {
        constructor(...args) { this.children = []; this._init(...args); }
        _init(props = {}) {
            if ('vertical' in props) throw Error('GNOME 51 removed vertical');
            Object.assign(this, props);
            this.children ??= [];
            this.clutter_text = {connectObject() {}};
        }
        add_child(child) { this.children.push(child); } remove_child() {}
        add_constraint() {} connectObject() {} connect() {} set_child() {}
        hide() { this.visible = false; } show() { this.visible = true; }
        set_policy() {} set_style() {} set_width() {} set_position() {}
        set_text(text) { this.text = text; } get_text() { return this.text; }
        grab_key_focus() { this.focused = true; }
        get_children() { return this.children; } destroy_all_children() { this.children = []; }
        add_style_class_name() {} remove_style_class_name() {} destroy() {}
    }
    let grabs = 0, releases = 0;
    const group = new Actor(); group.set_child_above_sibling = () => {};
    const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/raccoonlauncher@shimafallah.github.io/lib/overlay.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export const', 'const');
    const Launcher = vm.runInNewContext(`${source}\nLauncherOverlay`, {
        GObject: {registerClass: cls => cls},
        St: {BoxLayout: Actor, Widget: Actor, Button: Actor, Entry: Actor, Icon: Actor, ScrollView: Actor,
            Label: Actor, PolicyType: {NEVER: 0, AUTOMATIC: 1}},
        Clutter: {Orientation: {VERTICAL: 1}, ActorAlign: {CENTER: 1}, FixedLayout: class {},
            BindConstraint: class {}, BindCoordinate: {ALL: 1}, EventType: {KEY_PRESS: 1}, KEY_Escape: 27, EVENT_STOP: 1, EVENT_PROPAGATE: 0},
        Shell: {ActionMode: {NORMAL: 1}}, global: {stage: {connectObject() {}, disconnectObject() {}}},
        Main: {uiGroup: group, layoutManager: {primaryMonitor: {x: 0, y: 0, width: 1920, height: 1080}},
            pushModal() { grabs++; return {}; }, popModal() { releases++; }},
    });
    const overlay = new Launcher({query: () => []}, {get_string: () => '', connectObject() {}, disconnectObject() {}}, () => {});
    overlay.toggle();
    assert.equal(overlay._isOpen, true);
    assert.equal(overlay._entry.focused, true);
    overlay._onCapturedEvent({type: () => 1, get_key_symbol: () => 27});
    assert.equal(overlay._isOpen, false);
    assert.equal(grabs, releases);
    overlay.toggle(); overlay.toggle();
    assert.equal(grabs, releases);
    overlay.destroy();
});

test('calculator rejects malformed decimals and preserves tiny and huge finite results', () => {
    const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/raccoonlauncher@shimafallah.github.io/lib/providers/calc.js', import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export class', 'class');
    const Calc = vm.runInNewContext(`${source}\nCalcProvider`, {});
    const calc = new Calc();
    assert.equal(calc.query('1.2.3+4').length, 0);
    assert.equal(calc.query('..1+4').length, 0);
    assert.equal(calc.query('1/0').length, 0);
    assert.equal(calc.query('10^-12')[0].name, '1e-12');
    assert.equal(calc.query('10^308')[0].name, '1e+308');
    assert.equal(calc.query('0.1+0.2')[0].name, '0.3');
});
