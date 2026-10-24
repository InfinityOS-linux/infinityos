import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';

const source = readFileSync(process.env.APP_FOLDER_DIALOG_SOURCE ?? new URL('../vendor/gnome-shell/fedora-44/usr/share/gnome-shell/extensions/vertical-workspaces@G-dH.github.com/lib/appDisplay.js', import.meta.url), 'utf8');
const dialogSource = source.match(/^const AppFolderDialog = (\{[\s\S]*?^\});/m)?.[1];

test('a destroyed app folder ignores later GNOME name changes', () => {
    assert.ok(dialogSource);
    const dialogOverride = Function('Main', `return (${dialogSource})`)({
        overview: {disconnectObject() {}},
    });
    const dialog = {
        _syncFolderName() {
            throw new Error('GNOME Shell accessed a disposed folder label');
        },
    };

    dialogOverride.after__onDestroy.call(dialog);
    assert.doesNotThrow(() => dialog._syncFolderName());
});
