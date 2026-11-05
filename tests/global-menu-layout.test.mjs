import assert from 'node:assert/strict';
import {test} from 'node:test';

import {needsRightSide} from '../root/usr/share/gnome-shell/extensions/globalmenu@ShiroOSL.github.io/panelLayout.mjs';

test('moves the clock and terminal only when the app menu reaches them', () => {
    assert.equal(needsRightSide(1416, 500, 300), false);
    assert.equal(needsRightSide(1416, 600, 300), true);
    assert.equal(needsRightSide(1416, 546, 300), false);
    assert.equal(needsRightSide(1416, 547, 300), true);
});
