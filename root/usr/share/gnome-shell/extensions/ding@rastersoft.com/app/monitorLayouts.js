// SPDX-License-Identifier: GPL-3.0-only
// Keep independent icon positions for each logical desktop configuration.
export const ATTRIBUTE = 'metadata::infinityos-monitor-positions';
const MAX_LAYOUTS = 16;

export function layoutKey(desktops) {
    if (!desktops?.length)
        return null;
    // Enumeration, primary-screen selection and panel/dock margins can change
    // without changing the layout. Negative origins and scaling are significant.
    const areas = desktops.map(area => [area.x, area.y, area.width, area.height,
        area.scaleFactor ?? 1]);
    if (areas.some(area => !area.every(Number.isFinite)))
        return null;
    areas.sort((a, b) => {
        for (let i = 0; i < a.length; i++) {
            if (a[i] !== b[i])
                return a[i] - b[i];
        }
        return 0;
    });
    return `v1:${JSON.stringify(areas)}`;
}

function validPosition(position) {
    return position === null || (Array.isArray(position) &&
        position.length === 2 && position.every(Number.isFinite));
}

export function readLayouts(text) {
    try {
        const value = JSON.parse(text);
        if (!value || Array.isArray(value) || typeof value !== 'object')
            return {};
        return Object.fromEntries(Object.entries(value)
            .filter(([key, position]) => key.startsWith('v1:') &&
                key.length <= 4096 && validPosition(position))
            .slice(-MAX_LAYOUTS));
    } catch {
        return {};
    }
}

export function positionForLayout(layouts, key, legacy) {
    const position = key && Object.hasOwn(layouts, key) ? layouts[key] : legacy;
    return validPosition(position) && position !== null ? [...position] : null;
}

export function rememberPosition(layouts, key, position) {
    if (!key || !validPosition(position))
        return layouts;
    // Reinsert the active layout last so bounded history retains recent setups.
    const entries = Object.entries(layouts).filter(([name]) => name !== key);
    entries.push([key, position === null ? null : [...position]]);
    return Object.fromEntries(entries.slice(-MAX_LAYOUTS));
}
