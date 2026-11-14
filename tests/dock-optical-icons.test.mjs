import assert from 'node:assert/strict';
import test from 'node:test';
import {artworkBounds, opticalMetrics} from '../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/optical-icons.mjs';

function icon(top, bottom) {
    const pixels = new Uint8Array(12 * 10 * 4); // padded rowstride
    for (let y = 0; y < 10; y++) for (let x = 2; x < 8; x++)
        pixels[y * 48 + x * 4 + 3] = y >= top && y <= bottom ? 255 : 40;
    return pixels;
}
test('visible artwork ignores transparent margins, shadows and padded rowstrides', () => {
    const setup = artworkBounds(icon(2, 7), 10, 10, 48, 4, true);
    const firefox = artworkBounds(icon(0, 9), 10, 10, 48, 4, true);
    const tall = artworkBounds(icon(1, 8), 10, 10, 48, 4, true);
    assert.deepEqual(setup, {height: 0.6, x: 0.5, y: 0.5});
    for (const artwork of [firefox, tall])
        assert.equal(artwork.height * (setup.height / artwork.height), setup.height);
});
test('off-center artwork is centered and RGB/empty icons remain safe', () => {
    assert.equal(artworkBounds(icon(0, 5), 10, 10, 48, 4, true).y, 0.3);
    assert.equal(artworkBounds(new Uint8Array(400), 10, 10, 40, 4, true).height, 1);
    assert.equal(artworkBounds(new Uint8Array(300), 10, 10, 30, 3, false).height, 1);
});
test('icon decoding is asynchronous, cached per theme and refreshed on theme change', () => {
    let loads = 0, changed = 0, done;
    const info = {load_icon_async(_cancel, callback) { loads++; done = callback; },
        load_icon_finish() { return {get_pixels: () => icon(2, 7), width: 10, height: 10,
            rowstride: 48, n_channels: 4, has_alpha: true}; }};
    const theme = {lookup_icon: () => info};
    const refresh = () => changed++;
    opticalMetrics(theme, null, 'setup', refresh);
    opticalMetrics(theme, null, 'setup', refresh);
    assert.equal(loads, 1);
    done(info, {});
    assert.equal(changed, 1);
    assert.equal(opticalMetrics(theme, null, 'setup', refresh).height, 0.6);
    opticalMetrics({...theme}, null, 'setup', refresh);
    assert.equal(loads, 2);
});
