import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {excludeFromDock} from '../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock-apps.mjs';
const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js', import.meta.url), 'utf8');
// Exercise the complete method, stopping at the following method declaration.
const start = source.indexOf('    _inspectIcon(c) {');
const end = source.indexOf('\n    }', start) + 6;
const inspect = new Function('excludeFromDock', `return ({${source.slice(start, end)}})._inspectIcon`)(excludeFromDock);
test('Updater is excluded from dock layout and animation icons', () => {
    const icon = {visible: true, child: {app: {get_id: () => 'org.infinityos.Updater.desktop'}},
        hide() { this.visible = false; }};
    assert.equal(inspect.call({}, icon), false);
    assert.equal(icon.visible, false);
});

test('window identity filters the drawer and dialogs behind a generic launcher', () => {
    const drawer = {get_gtk_application_id: () => 'org.infinityos.Updater'};
    const history = {get_transient_for: () => drawer};
    for (const window of [drawer, history, {get_wm_class: () => 'org.infinityos.Updater'}]) {
        const app = {get_id: () => 'window:7', get_windows: () => [window]};
        assert.equal(excludeFromDock(app), true);
        const icon = {child: {app, reactive: true}, hide() { this.visible = false; }};
        assert.equal(inspect.call({}, icon), false);
        assert.equal(icon.child.reactive, false);
    }
});

test('window-backed helpers stay out while real unregistered windows remain usable', () => {
    let windows = [];
    const app = {is_window_backed: () => true, get_windows: () => windows};
    assert.equal(excludeFromDock(app), true);
    windows = [{skip_taskbar: true}, {is_override_redirect: () => true}];
    assert.equal(excludeFromDock(app), true);
    windows.push({minimized: true});
    assert.equal(excludeFromDock(app), false);
    assert.equal(excludeFromDock({get_windows: () => []}), false);
});
