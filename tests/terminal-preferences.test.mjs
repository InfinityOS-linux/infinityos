import assert from 'node:assert/strict';
import test from 'node:test';
import {defaults, readPreferences, writePreferences} from '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/preferences-config.mjs';
test('appearance changes preserve custom settings and repeated key bindings', () => {
    const previous = '# My settings\nscrollback-limit = 100000000\nkeybind = ctrl+a=first\nkeybind = ctrl+b=second\n  font-size = 12\nwindow-padding-y = 4\n';
    const text = writePreferences({...defaults, 'font-size': 16}, previous);
    for (const line of previous.split('\n').slice(0, 4)) assert.ok(text.includes(line));
    assert.equal((text.match(/font-size\s*=/g) ?? []).length, 1);
    assert.equal((text.match(/window-padding-y\s*=/g) ?? []).length, 1);
    assert.equal(writePreferences(readPreferences(text), text), text);
});
test('settings round trip, and system theme stays in control by default', () => {
    const text = writePreferences(defaults);
    assert.deepEqual(readPreferences(text), defaults);
    assert.equal(/^background =/m.test(text), false);
    assert.equal(/^foreground =/m.test(text), false);
});
test('custom colors and font settings persist', () => {
    const values = {...defaults, 'font-family': 'DejaVu Sans Mono', 'font-size': 16,
        background: '#102030', foreground: '#ffffff', 'copy-on-select': true};
    assert.deepEqual(readPreferences(writePreferences(values)), values);
});
test('invalid values cannot inject additional Ghostty configuration', () => {
    for (const values of [{'font-family': 'Mono\ncommand = bad'}, {'font-size': NaN},
        {'background-opacity': 3}, {background: '#fff\ncommand=x'}, {'cursor-style': 'invalid'}])
        assert.throws(() => writePreferences(values));
});
