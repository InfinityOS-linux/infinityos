export const defaults = {
    'font-family': 'Iosevka Term', 'font-size': 11, 'background-opacity': 0.93,
    background: '', foreground: '', 'cursor-style': 'block',
    'cursor-style-blink': true, 'copy-on-select': false, 'window-padding-x': 12,
};
export function readPreferences(text) {
    const values = {...defaults};
    for (const line of text.split('\n')) {
        const match = line.match(/^([\w-]+)\s*=\s*(.*?)\s*$/);
        if (!match || !(match[1] in defaults)) continue;
        const [_, key, value] = match;
        values[key] = typeof defaults[key] === 'number' ? Number(value)
            : typeof defaults[key] === 'boolean' ? value === 'true' : value;
    }
    return values;
}
export function writePreferences(values) {
    const v = {...defaults, ...values};
    if (!v['font-family'].trim() || /[\r\n\\"#=]/.test(v['font-family']))
        throw new Error('Invalid font family');
    for (const [key, min, max] of [['font-size', 6, 48], ['background-opacity', 0.2, 1], ['window-padding-x', 0, 40]]) {
        if (!Number.isFinite(v[key]) || v[key] < min || v[key] > max)
            throw new Error(`Invalid ${key}`);
    }
    for (const key of ['background', 'foreground'])
        if (v[key] !== '' && !/^#[0-9a-f]{6}$/i.test(v[key])) throw new Error(`Invalid ${key}`);
    if (!['block', 'bar', 'underline'].includes(v['cursor-style'])) throw new Error('Invalid cursor style');
    return '# Managed by InfinityTerminal preferences\n' + Object.keys(defaults)
        .filter(key => v[key] !== '')
        .map(key => `${key} = ${v[key]}`).join('\n') + `\nwindow-padding-y = ${v['window-padding-x']}\n`;
}
