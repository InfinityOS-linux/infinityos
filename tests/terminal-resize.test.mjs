import assert from 'node:assert/strict';
import test from 'node:test';

import {clampTerminalHeight, isFullHeight} from
    '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/resize.mjs';

test('terminal height stays between half the screen and the bottom edge', () => {
    assert.equal(clampTerminalHeight(1000, 40, 200), 500);
    assert.equal(clampTerminalHeight(1000, 40, 720), 720);
    assert.equal(clampTerminalHeight(1000, 40, 1200), 960);
    assert.equal(clampTerminalHeight(600, 320, 100), 280);
});

test('dragging to the bottom snaps to the full-height state', () => {
    assert.equal(isFullHeight(1000, 40, 951), false);
    assert.equal(isFullHeight(1000, 40, 952), true);
});
