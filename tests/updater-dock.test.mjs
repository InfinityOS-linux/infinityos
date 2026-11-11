import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js', import.meta.url), 'utf8');
// Exercise the complete method, stopping at the following method declaration.
const start = source.indexOf('    _inspectIcon(c) {');
const end = source.indexOf('\n    }', start) + 6;
const inspect = new Function(`return ({${source.slice(start, end)}})._inspectIcon`)();
test('Updater is excluded from dock layout and animation icons', () => {
    const icon = {visible: true, child: {app: {get_id: () => 'org.infinityos.Updater.desktop'}},
        hide() { this.visible = false; }};
    assert.equal(inspect.call({}, icon), false);
    assert.equal(icon.visible, false);
});
