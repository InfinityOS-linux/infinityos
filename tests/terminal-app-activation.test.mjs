import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');
function fixture() {
    const calls = [], signals = new Map(); let id = 0;
    class App {
        constructor(name) { this.name = name; }
        get_id() { return this.name; }
        activate(...args) { calls.push(['activate', ...args]); return 'native'; }
        activate_full(...args) { calls.push(['activate_full', ...args]); return 'native'; }
        open_new_window(...args) { calls.push(['open_new_window', ...args]); return 'native'; }
    }
    class InjectionManager {
        constructor() { this.restore = []; }
        overrideMethod(object, key, factory) { const original = object[key]; this.restore.push(() => { object[key] = original; }); object[key] = factory(original); }
        clear() { this.restore.reverse().forEach(restore => restore()); }
    }
    const overview = {visible: false, hide() { this.visible = false; },
        connect(name, callback) { signals.set(++id, {name, callback}); return id; },
        disconnect(id) { signals.delete(id); }};
    const Controller = vm.runInNewContext(`${source}\nInfinityTerminal`, {
        Extension: class {}, InjectionManager, Shell: {App}, Main: {overview},
    });
    const controller = new Controller(); let shown = 0;
    controller._showTerminal = () => { shown++; };
    const original = App.prototype.activate;
    controller._installAppActivation();
    return {controller, overview, App, calls, original, shown: () => shown,
        hidden() { overview.visible = false; for (const {callback} of [...signals.values()]) callback(); }};
}
for (const method of ['activate', 'activate_full', 'open_new_window']) {
    test(`terminal Shell.App.${method} uses the drawer and other apps retain native activation`, () => {
        const f = fixture();
        new f.App('com.infinityos.GhosTTY.desktop')[method](-1, 123);
        assert.equal(f.shown(), 1);
        assert.equal(f.calls.length, 0);
        assert.equal(new f.App('org.example.Other.desktop')[method](-1, 123), 'native');
        assert.deepEqual(f.calls[0], [method, -1, 123]);
        f.controller._removeAppActivation();
        assert.equal(f.App.prototype.activate, f.original);
    });
}
test('app-grid launch waits until overview is hidden and repeated activation only opens once', () => {
    const f = fixture(); f.overview.visible = true;
    const app = new f.App('com.infinityos.GhosTTY.desktop');
    app.activate(); app.activate();
    assert.equal(f.shown(), 0);
    f.hidden();
    assert.equal(f.shown(), 1);
    f.controller._removeAppActivation();
});
test('extension teardown cancels a pending overview launch', () => {
    const f = fixture(); f.overview.visible = true;
    new f.App('com.infinityos.GhosTTY.desktop').activate();
    f.controller._removeAppActivation(); f.hidden();
    assert.equal(f.shown(), 0);
});
