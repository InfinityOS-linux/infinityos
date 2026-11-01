import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { test } from 'node:test';

const path = new URL('../root/usr/share/gnome-shell/extensions/wack-lockscreen-clock@rinzler69-wastaken.github.com/src/main/layoutManager.js', import.meta.url);
const source = readFileSync(path, 'utf8')
    .replace(/^import .*;\n/gm, '')
    .replace('export const WackLayout', 'const WackLayout');
const WackLayout = runInNewContext(`${source}\nWackLayout`, {
    Clutter: { LayoutManager: class { _init() {} }, ActorBox: class {} },
    GObject: { registerClass: cls => cls },
    CUPERTINO_PROMPT_VERTICAL_FRACTION: 0.9575,
});

function stackPosition(stackHeight) {
    let allocated;
    const stack = {
        get_preferred_size: () => [0, 0, 300, stackHeight],
        allocate: box => { allocated = box; },
    };
    const notifications = {
        get_preferred_size: () => [0, 0, 0, 0],
        allocate: () => {},
    };
    const layout = new WackLayout();
    layout._init({
        _lockscreenMode: 'cupertino',
        _cupertinoRestPrompt: { _userWell: { get_height: () => 180 } },
    }, stack, notifications, null);
    layout.vfunc_allocate(null, { get_size: () => [1000, 1080] });
    return allocated.y1;
}

test('Cupertino prompt keeps its anchor until a multi-line error needs space', () => {
    assert.equal(stackPosition(200), 800);
    assert.equal(stackPosition(400), 656);
    assert.equal(stackPosition(400) + 400, 1080 - 24);
});

const stylesheet = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-lockscreen-clock@rinzler69-wastaken.github.com/stylesheet.css', import.meta.url), 'utf8');

test('Cupertino password entry remains tall enough with the compact Orchis theme', () => {
    const rule = stylesheet.match(/\.unlock-dialog \.login-dialog-prompt-entry \{([^}]+)\}/)?.[1];
    const minHeight = Number(rule?.match(/\bmin-height:\s*(\d+)px\s*!important/)?.[1]);
    assert.ok(minHeight >= 36, `password entry minimum height must be at least 36px (got ${minHeight || 'unset'})`);
});
