import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-updater/root/usr/share/gnome-shell/extensions/infinity-updater@infinityos.org/panel-backdrop.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export class', 'class');

function fixture(options) {
    let next = 1, theme = 'prefer-dark';
    const timers = new Map(), records = [], properties = [];
    const bus = {export() {}, unexport() {this.unexported = true;},
        emit_property_changed(name, value) {properties.push([name, value.value]);}};
    class Actor {
        constructor(props = {}) { Object.assign(this, {children: [], signals: new Map(), visible: true, opacity: 255}, props); }
        connect(name, callback) { const id = next++; this.signals.set(id, {name, callback}); return id; }
        disconnect(id) { this.signals.delete(id); }
        insert_child_at_index(child, i) { this.children.splice(i, 0, child); child.parent = this; }
        add_child(child) { this.insert_child_at_index(child, this.children.length); }
        get_children() { return this.children; }
        set_position(x, y) { Object.assign(this, {x, y}); }
        set_size(width, height) { Object.assign(this, {width, height}); }
        set_style(style) { this.style = style; }
        get_theme_node() { return {get_background_color: () => ({red: 24, green: 22, blue: 36, alpha: 64})}; }
        destroy() { this.destroyed = true; this.parent?.children.splice(this.parent.children.indexOf(this), 1); }
    }
    const panel = new Actor(), manager = new Actor();
    const settings = new Actor(); settings.get_string = () => theme;
    const frame = {x: 1420, y: 32, width: 460, height: 1000};
    const buffer = {x: 1400, y: 16, width: 480, height: 1016};
    const actor = new Actor();
    const window = new Actor(); Object.assign(window, {
        get_compositor_private: () => actor, get_frame_rect: () => frame,
        get_buffer_rect: () => buffer, get_monitor: () => 1,
    });
    const blur = {enabled: true, settings: {panel: {STATIC_BLUR: true, PIPELINE: 'panel-preset'}},
        createMatchingBackdrop(container, index) {
            const background = new Actor(); container.insert_child_at_index(background, 0);
            const record = {background, index, staticBlur: this.settings.panel.STATIC_BLUR,
                offsetY: .01, destroyed: false, destroy() { this.destroyed = true; background.destroy(); }};
            records.push(record); return record;
        }};
    const global = {blur_my_shell: {_panel_blur: blur}};
    const Helper = vm.runInNewContext(`${source}\nPanelBackdrop`, {
        Gio: {Settings: class {constructor() {return settings;}},
            DBusExportedObject: {wrapJSObject: () => bus}, DBus: {session: {}}},
        GLib: {PRIORITY_DEFAULT: 0, SOURCE_CONTINUE: true,
            Variant: class {constructor(_type, value) {this.value = value;}},
            timeout_add(_priority, _ms, callback) { const id = next++; timers.set(id, callback); return id; },
            Source: {remove: id => timers.delete(id)}},
        St: {Widget: Actor}, Main: {panel, extensionManager: manager,
            layoutManager: {primaryIndex: 0, monitors: [{x: 0, y: 0}, {x: 1280, y: 0}]}}, global, console,
    });
    return {helper: new Helper(options), actor, window, frame, buffer, panel, blur, global, timers, records, properties, bus,
        Actor, theme(value) {theme = value;}};
}

test('wallpaper follows monitor coordinates behind sharp GTK contents and excludes window shadow', () => {
    const f = fixture(); const contents = new f.Actor(); f.actor.add_child(contents);
    f.helper.attach(f.window);
    const e = f.helper._entries.get(f.window);
    assert.equal(f.actor.children[0], e.container);
    assert.equal(f.actor.children[1], contents);
    assert.equal(f.actor.opacity, 255);
    assert.equal(e.container.clip_to_allocation, true);
    assert.deepEqual([e.container.x, e.container.y, e.container.width, e.container.height], [20, 16, 460, 1000]);
    assert.equal(e.backdrop.background.x, -140);
    assert.equal(e.backdrop.background.y, -31.99);
    f.frame.x += 20; f.helper.sync(f.window);
    assert.equal(e.backdrop.background.x, -160);
    f.helper.destroy(); assert.equal(f.timers.size, 0);
    assert.equal(f.actor.children.length, 1);
});

test('GTK becomes transparent only after a backdrop exists, and returns opaque on teardown', () => {
    const f = fixture(); f.blur.enabled = false;
    f.helper.attach(f.window);
    assert.equal(f.helper.Ready, false);
    assert.deepEqual(f.properties, []);
    f.blur.enabled = true; f.helper.syncAll();
    assert.equal(f.helper.Ready, true);
    assert.deepEqual(f.properties, [['Ready', true]]);
    f.helper.syncAll(); assert.equal(f.properties.length, 1);
    f.helper.detach(f.window);
    assert.equal(f.helper.Ready, false);
    assert.deepEqual(f.properties, [['Ready', true], ['Ready', false]]);
    f.helper.destroy(); assert(f.bus.unexported);
});

test('a failed backdrop creation is retried without requiring a settings change', () => {
    const f = fixture(), create = f.blur.createMatchingBackdrop;
    f.blur.createMatchingBackdrop = () => null;
    f.helper.attach(f.window);
    assert.equal(f.helper.Ready, false);
    f.blur.createMatchingBackdrop = create;
    f.helper.syncAll();
    assert.equal(f.helper.Ready, true);
    f.helper.destroy();
});

test('Setup and Config only make their own surface transparent', () => {
    const f = fixture();
    const config = new f.Actor();
    Object.assign(config, {
        get_compositor_private: () => new f.Actor(),
        get_frame_rect: () => f.frame, get_buffer_rect: () => f.buffer,
        get_monitor: () => 1,
    });
    f.helper.attach(f.window, 'SetupReady');
    assert.equal(f.helper.SetupReady, true);
    assert.equal(f.helper.ConfigReady, false);
    assert.equal(f.helper.Ready, false);
    f.helper.attach(config, 'ConfigReady');
    f.helper.detach(f.window);
    assert.equal(f.helper.SetupReady, false);
    assert.equal(f.helper.ConfigReady, true);
    assert.deepEqual(f.properties, [['SetupReady', true], ['ConfigReady', true], ['SetupReady', false]]);
    f.helper.destroy();
    assert.equal(f.helper.ConfigReady, false);
});

test('dynamic blur fills the drawer and reconnects after preset changes and panel resets', () => {
    const f = fixture(); f.blur.settings.panel.STATIC_BLUR = false;
    f.helper.attach(f.window);
    const e = f.helper._entries.get(f.window);
    assert.equal(e.backdrop.background.width, 460);
    assert.equal(e.backdrop.background.height, 1000);
    const first = e.backdrop;
    f.blur.settings.panel.PIPELINE = 'new-preset'; f.helper.syncAll();
    assert(first.destroyed);
    const second = e.backdrop; second.destroy(); f.helper.syncAll();
    assert.notEqual(e.backdrop, second);
    f.helper.detach(f.window); assert.equal(f.timers.size, 0);
    f.helper.attach(f.window); assert.equal(f.timers.size, 1);
    f.helper.destroy();
});

test('disabled blur uses an opaque fallback and restores matching tint when reenabled', () => {
    const f = fixture(); f.helper.attach(f.window);
    const e = f.helper._entries.get(f.window);
    const layer = new f.Actor({name: 'wackPanelBackdropOverlay', opacity: 128});
    f.panel.add_child(layer); f.helper.syncAll();
    assert.equal(e.layers.length, 1); assert.equal(e.layers[0].opacity, 128);
    f.blur.enabled = false; f.helper.syncAll();
    assert.match(e.tint.style, /#181624/); assert.equal(e.layers.length, 0);
    f.theme('prefer-light'); f.helper.syncAll(); assert.match(e.tint.style, /#faf7ff/);
    f.blur.enabled = true; f.helper.syncAll();
    assert.equal(e.tint.style, 'background-color: rgba(226,222,233,0.82);');
    assert.equal(e.layers.length, 0);
    f.theme('prefer-dark'); f.helper.syncAll();
    assert.equal(e.layers.length, 1);
    f.helper.destroy();
});

test('terminal and widget strip share the panel pipeline without claiming updater readiness', () => {
    const f = fixture({exportReadiness: false});
    const strip = new f.Actor({x: f.frame.x, y: f.frame.y - 72, width: f.frame.width, height: 72});
    const widgets = new f.Actor();
    strip.add_child(widgets);
    f.helper.attach(f.window, null, strip);
    const entry = f.helper._entries.get(f.window);
    assert.deepEqual(strip.children, [entry.stripSurface.container, widgets]);
    assert.ok(Math.abs(entry.stripSurface.backdrop.background.y - entry.backdrop.background.y - strip.height) < .001);
    assert.deepEqual(f.properties, []);
    f.blur.enabled = false;
    f.theme('prefer-light');
    f.helper.syncAll();
    assert.equal(entry.stripSurface.tint.style, entry.tint.style);
    assert.match(entry.tint.style, /#faf7ff/);
    f.blur.enabled = true;
    f.blur.settings.panel.STATIC_BLUR = false;
    f.helper.syncAll();
    assert.equal(entry.stripSurface.tint.style, entry.tint.style);
    assert.equal(entry.tint.style, 'background-color: rgba(226,222,233,0.82);');
    assert.equal(entry.stripSurface.backdrop.background.height, strip.height);
    const stripBlur = entry.stripSurface.backdrop;
    strip.visible = false;
    f.helper.syncAll();
    assert(stripBlur.destroyed);
    assert(!entry.backdrop.destroyed);
    f.helper.destroy();
    assert.equal(f.timers.size, 0);
    assert.deepEqual(strip.children, [widgets]);
});
