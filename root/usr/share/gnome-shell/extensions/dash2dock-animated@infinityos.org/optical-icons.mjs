// Measure the solid artwork, excluding transparent padding and soft shadows.
export function artworkBounds(pixels, width, height, stride, channels, alpha) {
    let left = width, right = -1, top = height, bottom = -1;
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (alpha && pixels[y * stride + x * channels + channels - 1] < 128) continue;
            left = Math.min(left, x); right = Math.max(right, x);
            top = Math.min(top, y); bottom = Math.max(bottom, y);
        }
    }
    if (bottom < top) return {height: 1, x: 0.5, y: 0.5};
    return {height: (bottom - top + 1) / height,
        x: (left + right + 1) / (2 * width), y: (top + bottom + 1) / (2 * height)};
}

// One cache per icon theme, discarded automatically on theme/cache changes.
const themes = new WeakMap();
export function opticalMetrics(theme, gicon, name, changed) {
    if (!theme) return {height: 1, x: 0.5, y: 0.5};
    let cache = themes.get(theme);
    if (!cache) { cache = new Map(); themes.set(theme, cache); }
    const key = gicon?.to_string() ?? name;
    if (cache.has(key)) return cache.get(key);
    const fallback = {height: 1, x: 0.5, y: 0.5};
    cache.set(key, fallback);
    try {
        const info = gicon ? theme.lookup_by_gicon(gicon, 96, 0) : theme.lookup_icon(name, 96, 0);
        info?.load_icon_async(null, (source, result) => {
            try {
                const pixbuf = source.load_icon_finish(result);
                cache.set(key, artworkBounds(pixbuf.get_pixels(), pixbuf.width, pixbuf.height,
                    pixbuf.rowstride, pixbuf.n_channels, pixbuf.has_alpha));
                changed();
            } catch (_) { /* Keep the standard size for unavailable icons. */ }
        });
    } catch (_) { /* An unavailable theme icon must not interrupt the dock. */ }
    return fallback;
}
