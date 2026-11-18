import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';

const directory = process.env.TRAY_SOURCE_DIR ?? path.resolve(
    'root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com');
function source(file) {
    return fs.readFileSync(path.join(directory, file), 'utf8')
        .replace(/^import .*;\n/gm, '').replace(/export default /g, '')
        .replace(/export /g, '');
}
function setup() {
    let id = 0;
    class Actor {
        constructor(props = {}) {
            this.children = []; this.signals = new Map(); this.visible = true;
            Object.assign(this, props);
            if (this.layout_manager) this.layout_manager.owner = this;
        }
        connect(name, callback) { this.signals.set(++id, [name, callback]); return id; }
        disconnect(key) { this.signals.delete(key); }
        emit(name, ...args) {
            for (const [signal, callback] of [...this.signals.values()])
                if (signal === name) callback(this, ...args);
        }
        get_parent() { return this.parent ?? null; }
        get_children() { return [...this.children]; }
        add_child(child) { this.insert_child_at_index(child, this.children.length); }
        insert_child_at_index(child, index) {
            assert.equal(child.get_parent(), null, 'actor has only one parent');
            this.children.splice(Math.min(index, this.children.length), 0, child);
            child.parent = this; this.emit('child-added', child);
        }
        remove_child(child) {
            assert.equal(child.parent, this);
            this.children.splice(this.children.indexOf(child), 1); child.parent = null;
        }
        set_child(child) {
            for (const old of [...this.children]) this.remove_child(old);
            if (child) this.add_child(child);
        }
        set_child_at_index(child, index) {
            this.children.splice(this.children.indexOf(child), 1);
            this.children.splice(index, 0, child);
        }
        set_style(style) { this.style = style; }
        get_style() { return this.style ?? null; }
        destroy() {
            this.emit('destroy');
            for (const child of [...this.children]) child.destroy();
            this.parent?.remove_child(this); this.destroyed = true;
        }
        hide() { this.visible = false; }
    }
    class Icon extends Actor {}
    class Menu extends Actor {
        constructor() { super(); this.actor = new Actor(); this.actions = []; }
        addAction(label, callback) { this.actions.push({label, callback}); }
        addMenuItem(item) { this.actions.push(item); }
        open() { this.isOpen = true; this.emit('open-state-changed', true); }
        close() { this.isOpen = false; this.emit('open-state-changed', false); }
        destroy() { this.close(); super.destroy(); this.actor.destroy(); }
    }
    class Manager {
        constructor() { this.menus = new Set(); }
        addMenu(menu) { this.menus.add(menu); }
        removeMenu(menu) { this.menus.delete(menu); }
    }
    const pending = new Map();
    let saved = '{}';
    let failWrite = false;
    const file = {
        load_contents: () => [true, new TextEncoder().encode(saved)],
        get_parent: () => ({get_path: () => '/test'}),
        replace_contents(bytes) {
            if (failWrite) throw new Error('disk full');
            saved = new TextDecoder().decode(bytes);
        },
    };
    const panel = {statusArea: {}, _rightBox: new Actor(), menuManager: new Manager(),
        addToStatusArea(role, indicator) {
            this.statusArea[role] = indicator; this._rightBox.add_child(indicator.container);
            this.menuManager.addMenu(indicator.menu); return indicator;
        }};
    const system = new Actor(), volume = new Actor(), microphone = new Actor(),
        brightness = new Actor(), wifi = new Actor();
    const grid = new Actor();
    [system, volume, microphone, brightness, wifi].forEach(item => grid.add_child(item));
    const quick = {menu: new Menu(), _system: {quickSettingsItems: [system]},
        _volumeOutput: {quickSettingsItems: [volume]},
        _volumeInput: {quickSettingsItems: [microphone]}};
    quick.menu._grid = grid;
    quick.menu.addItem = item => grid.add_child(item);
    panel.statusArea.quickSettings = quick;
    const Main = {panel, sessionMode: new Actor({currentMode: 'user', isLocked: false}),
        uiGroup: new Actor(), notifyError() {}};
    const context = vm.createContext({console, TextEncoder, TextDecoder,
        Main, Gio: {File: {new_for_path: () => file}, FileCreateFlags: {PRIVATE: 1}},
        GLib: {get_user_config_dir: () => '/test', build_filenamev: parts => parts.join('/'),
            get_language_names: () => ['pl_PL.UTF-8', 'pl'], mkdir_with_parents() {},
            idle_add: (_priority, callback) => { pending.set(++id, callback); return id; },
            source_remove: key => pending.delete(key)},
        St: {BoxLayout: Actor, Widget: Actor, Button: Actor, Icon, Bin: Actor, Side: {TOP: 0}},
        Clutter: {Orientation: {VERTICAL: 1}, ActorAlign: {CENTER: 0}, GridLayout: class {
            attach(actor) { this.owner.add_child(actor); }
        }, EventType: {BUTTON_PRESS: 1, BUTTON_RELEASE: 2, KEY_PRESS: 3},
        ModifierType: {SHIFT_MASK: 1}, EVENT_STOP: 1, EVENT_PROPAGATE: 0},
        PopupMenu: {PopupSeparatorMenuItem: Actor, PopupMenu: Menu, PopupMenuManager: Manager,
            PopupSubMenuMenuItem: class extends Actor { constructor() { super(); this.menu = new Menu(); } }},
        InjectionManager: class {
            overrideMethod(object, key, factory) {
                this.restore = () => { object[key] = this.original; };
                this.original = object[key]; object[key] = factory(this.original);
            }
            clear() { this.restore(); }
        },
    });
    vm.runInContext(source('trayLayout.js') + source('trayStrings.js') + source('userTray.js') +
        '\nglobalThis.UserTray = UserTray; globalThis.trayText = trayText; globalThis.labels = labels;', context);
    const add = role => {
        const indicator = new Actor({container: new Actor(), menu: new Menu(), accessible_name: role});
        panel.addToStatusArea(role, indicator); return indicator;
    };
    const flush = () => {
        for (const [key, callback] of [...pending]) { pending.delete(key); callback(); }
    };
    return {context, panel, Main, grid, system, volume, microphone, brightness, wifi, add, flush,
        Actor, Icon,
        create: () => new context.UserTray(), saved: () => JSON.parse(saved),
        failWrite: () => { failWrite = true; }};
}

test('moves live app actors below system/audio, keeps native controls and late arrivals', () => {
    const s = setup();
    const app = s.add('warp'); const keyboard = s.add('keyboard');
    const tray = s.create();
    assert.deepEqual(s.grid.children, [s.system, s.volume, s.microphone, tray._section, s.brightness, s.wifi]);
    assert.equal(app.container.get_parent().get_parent(), tray._icons);
    assert.equal(keyboard.container.get_parent(), s.panel._rightBox);
    assert.ok(tray._menus.menus.has(app.menu));
    const late = s.add('clipboard'); s.flush();
    assert.equal(late.container.get_parent().get_parent(), tray._icons);
    tray.destroy();
    assert.equal(app.container.get_parent(), s.panel._rightBox);
    assert.equal(late.container.get_parent(), s.panel._rightBox);
    assert.equal(app.destroyed, undefined);
    assert.ok(s.panel.menuManager.menus.has(app.menu));
    assert.deepEqual(s.grid.children, [s.system, s.volume, s.microphone, s.brightness, s.wifi]);
});

test('oversized and late nested icons fit their cells and restore on pin/disable', () => {
    const s = setup();
    const app = s.add('clipboard');
    const box = new s.Actor();
    const icon = new s.Icon({icon_size: 48, style: 'icon-size: 48px; color: red;'});
    box.add_child(icon); app.container.add_child(box);
    const tray = s.create();
    assert.equal(icon.icon_size, 18);
    assert.match(icon.style, /icon-size: 18px !important/);
    assert.equal(tray._entries.get(app).wrapper.clip_to_allocation, true);
    const late = new s.Icon({icon_size: 64});
    box.add_child(late); s.flush();
    assert.equal(late.icon_size, 18);
    const entry = tray._entries.get(app);
    tray._setLocation(entry, 'panel');
    assert.equal(icon.icon_size, 48);
    assert.equal(icon.style, 'icon-size: 48px; color: red;');
    assert.equal(late.icon_size, 64);
    tray._setLocation(entry, 'menu');
    assert.equal(icon.icon_size, 18);
    tray.destroy();
    assert.equal(icon.icon_size, 48);
    assert.equal(late.icon_size, 64);
});

test('pin/hide/show are persisted per app and survive extension reload', () => {
    const s = setup(); const app = s.add('warp'); const other = s.add('clipboard');
    let tray = s.create(); let entry = tray._entries.get(app);
    tray._setLocation(entry, 'panel');
    assert.equal(entry.wrapper.get_parent(), s.panel._rightBox);
    assert.equal(s.saved().warp, 'panel');
    assert.equal(tray._entries.get(other).wrapper.get_parent(), tray._icons);
    tray.destroy(); tray = s.create(); entry = tray._entries.get(app);
    assert.equal(entry.wrapper.get_parent(), s.panel._rightBox);
    tray._setLocation(entry, 'hidden'); assert.equal(entry.wrapper.visible, false);
    tray._openMenu(tray._icons);
    assert.equal(tray._context.actions.length, 2, 'hidden apps remain recoverable');
    tray._setLocation(entry, 'menu'); assert.equal(entry.wrapper.visible, true);
    assert.equal(entry.wrapper.get_parent(), tray._icons);
    s.failWrite(); tray._setLocation(entry, 'panel');
    assert.equal(entry.wrapper.get_parent(), tray._icons, 'failed persistence does not change location');
    tray.destroy();
});

test('unchanged sync keeps equal cells attached without an overflow button', () => {
    const s = setup();
    ['warp', 'clipboard', 'layouts'].forEach(role => s.add(role));
    const tray = s.create();
    assert.equal(tray._icons.get_children().length, 3);
    let removed = 0;
    const remove = tray._icons.remove_child.bind(tray._icons);
    tray._icons.remove_child = actor => { removed++; remove(actor); };
    tray._sync();
    assert.equal(removed, 0);
    for (const entry of tray._entries.values())
        assert.match(entry.wrapper.get_style(), /width: 32px/);
    tray.destroy();
});

test('updater stays in panel despite saved tray preferences and late registration', () => {
    const s = setup();
    const app = s.add('warp');
    const updater = s.add('infinity-updater');
    const tray = s.create();
    tray._preferences['infinity-updater'] = 'hidden';
    tray._sync();
    assert.equal(updater.container.get_parent(), s.panel._rightBox);
    assert.equal(tray._entries.has(updater), false);
    assert.ok(s.panel.menuManager.menus.has(updater.menu));
    assert.equal(app.container.get_parent().get_parent(), tray._icons);
    delete s.panel.statusArea['infinity-updater'];
    updater.container.destroy();
    updater.destroy();
    const late = s.add('infinity-updater');
    s.flush();
    assert.equal(late.container.get_parent(), s.panel._rightBox);
    assert.equal(tray._entries.has(late), false);
    tray.destroy();
});

test('disable restores original icon order with pinned and late apps', () => {
    const s = setup();
    const a = s.add('warp'); const keyboard = s.add('keyboard');
    const b = s.add('clipboard'); const c = s.add('layouts');
    const original = s.panel._rightBox.get_children();
    const tray = s.create();
    tray._setLocation(tray._entries.get(c), 'panel');
    const late = s.add('late'); s.flush();
    tray.destroy();
    assert.deepEqual(s.panel._rightBox.get_children(), [...original, late.container]);
    const again = s.create(); again.destroy();
    assert.deepEqual(s.panel._rightBox.get_children(), [...original, late.container]);
});

test('lock hides pinned apps and menu, app removal cleans up, disable restores native visibility', () => {
    const s = setup(); const app = s.add('warp'); const tray = s.create();
    const entry = tray._entries.get(app); tray._setLocation(entry, 'panel');
    s.Main.sessionMode.currentMode = 'unlock-dialog'; s.Main.sessionMode.isLocked = true;
    s.Main.sessionMode.emit('updated');
    assert.equal(entry.wrapper.visible, false); assert.equal(tray._section.visible, false);
    s.Main.sessionMode.currentMode = 'user'; s.Main.sessionMode.isLocked = false;
    s.Main.sessionMode.emit('updated'); assert.equal(entry.wrapper.visible, true);
    delete s.panel.statusArea.warp; app.destroy(); s.flush();
    assert.equal(tray._entries.size, 0); assert.equal(tray._section.visible, false);
    tray.destroy();
});

test('locale variants and all bundled labels cover every action', () => {
    const s = setup(); const {trayText, labels} = s.context;
    assert.equal(trayText('panel', ['pl_PL.UTF-8']), 'Przenieś na górny pasek');
    assert.equal(trayText('manage', ['pt_BR.UTF-8']), 'Ícones de aplicativos');
    assert.equal(trayText('panel', ['zh_TW.UTF-8']), '移至頂端列');
    assert.equal(trayText('menu', ['sr_RS.UTF-8@latin', 'sr@latin']), 'Premesti u meni');
    assert.equal(trayText('panel', ['C']), 'Move to top bar');
    for (const values of Object.values(labels)) {
        assert.equal(values.length, 5);
        assert.ok(values.every(value => typeof value === 'string' && value.length > 0));
    }
});

