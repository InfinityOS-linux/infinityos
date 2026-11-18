import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';
const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js', import.meta.url), 'utf8');
const start = source.indexOf('export function createDockBlurProxy(');
const end = source.indexOf('\nfunction toggleInfinityTerminal', start);
test('blur discovery proxy is allocated with the dock and points at its visible pill', () => {
    class Widget {
        constructor(props) { Object.assign(this, {visible: true}, props); }
        add_constraint(constraint) { this.constraint = constraint; }
    }
    const create = vm.runInNewContext(`${source.slice(start, end).replace('export ', '')}\ncreateDockBlurProxy`, {
        St: {Widget}, Clutter: {BindCoordinate: {SIZE: 7}, BindConstraint: class {constructor(props) {Object.assign(this, props);}}},
    });
    const background = {width: 420, height: 72};
    const dock = {_background: background, add_child(child) { this.child = child; }};
    const proxy = create(dock);
    assert.equal(proxy, dock.child);
    assert.equal(proxy.name, 'dash');
    assert.equal(proxy.visible, true);
    assert.equal(proxy.reactive, false);
    assert.equal(proxy._background, background);
    assert.equal(proxy.constraint.source, dock);
    assert.equal(proxy.constraint.coordinate, 7);
});
