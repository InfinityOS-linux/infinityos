import assert from 'node:assert/strict';
import { test } from 'node:test';

import { PopupBlurTargets } from '../vendor/gnome-shell/fedora-45/usr/share/gnome-shell/extensions/blur-my-shell@aunetx/components/popup/targets.js';

test('popup blur skips Snap Assistant without affecting other menus', () => {
    const finder = new PopupBlurTargets({
        is_internal_actor: () => false,
        watch_actor: () => true,
    });
    const targets = finder.create_targets();
    finder.add(targets, { has_style_class_name: name => name === 'snap-assistant' });
    assert.equal(targets.actors.length, 0);

    const menu = { has_style_class_name: name => name === 'popup-menu-content' };
    finder.add(targets, menu);
    assert.deepEqual(targets.actors, [menu]);
});
