import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/userTray.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replaceAll('export const ', 'const ').replace('export default class', 'class');
class Actor {
    constructor(props = {}) {Object.assign(this, {children: [], opacity: 255}, props);}
    get_parent() {return this.parent;}
    get_children() {return this.children;}
    add_child(actor) {assert.ok(!actor.parent); this.children.push(actor); actor.parent = this;}
    insert_child_at_index(actor, index) {assert.ok(!actor.parent); this.children.splice(index, 0, actor); actor.parent = this;}
    remove_child(actor) {this.children.splice(this.children.indexOf(actor), 1); actor.parent = null;}
    destroy_all_children() {for (const child of [...this.children]) child.destroy();}
    destroy() {this.destroy_all_children(); this.parent?.remove_child(this); this.destroyed = true;}
    add_style_class_name() {}
    remove_style_class_name() {}
    get_style() {return this.style;}
    set_style(s) {this.style = s;}
    connectObject() {}
    disconnectObject() {}
    connect() {}
}
let preferences = {};
const panel = new Actor();
const Main = {panel: {_rightBox: panel, statusArea: {}, menuManager: {addMenu() {}, removeMenu() {}}},
    sessionMode: {isLocked: false, currentMode: 'user'}};
const {UserTray, trayRows, trayPlacement} = runInNewContext(`${source}\n({UserTray, trayRows, trayPlacement})`, {
    St: {BoxLayout: Actor, Button: Actor}, Main, Clutter: {ActorAlign: {CENTER: 0}, Orientation: {VERTICAL: 1}},
});

test('tray wraps at six icons and never grows a seventh column', () => {
    for (let count = 0; count < 30; count++) {
        const items = Array.from({length: count}, (_, i) => i);
        const rows = trayRows(items);
        assert.equal(rows.length, Math.ceil(count / 6));
        assert.ok(rows.every(row => row.length <= 6));
        assert.equal(JSON.stringify(rows.flat()), JSON.stringify(items));
    }
    assert.equal(trayPlacement({app: 'invalid'}, 'app'), 'menu');
});

test('rebuilding, hiding and pinning preserve app actors and restore their original style', () => {
    const tray = Object.create(UserTray.prototype);
    Object.assign(tray, {_section: new Actor(), _parking: new Actor(), _body: new Actor(),
        _entries: new Map(), _manager: {addMenu() {}, removeMenu() {}}, _: text => text,
        _settings: {get_value: () => ({deep_unpack: () => preferences})}});
    const icon = new Actor({style: 'custom: style;', opacity: 210});
    panel.add_child(icon);
    Main.panel.statusArea.app = {container: icon};
    const system = new Actor(); panel.add_child(system);
    Main.panel.statusArea.quickSettings = {container: system};
    tray._sync();
    assert.equal(system.parent, panel);
    assert.equal(icon.parent.parent, tray._body);
    tray._sync();
    assert.equal(icon.destroyed, undefined);
    preferences = {app: 'hidden'};
    tray._sync();
    assert.equal(icon.parent, tray._parking);
    tray._showHidden = true;
    tray._sync();
    assert.equal(icon.parent.parent, tray._body);
    assert.equal(icon.opacity, 120);
    preferences = {app: 'panel'};
    tray._sync();
    assert.equal(icon.parent, panel);
    assert.equal(icon.style, 'custom: style;');
    assert.equal(icon.opacity, 210);
    preferences = {};
    tray._sync();
    Main.sessionMode.isLocked = true;
    tray._sync();
    assert.equal(tray._section.visible, false);
    assert.equal(icon.destroyed, undefined);
});
