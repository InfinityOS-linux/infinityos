import assert from 'node:assert/strict';
import test from 'node:test';
import {defaults, readPreferences, writePreferences} from '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/preferences-config.mjs';
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
