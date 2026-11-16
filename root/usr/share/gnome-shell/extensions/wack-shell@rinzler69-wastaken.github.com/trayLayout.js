// Shell-owned indicators stay in their existing panel positions.
const SYSTEM_ROLES = new Set([
    'activities', 'appMenu', 'dateMenu', 'quickSettings', 'a11y', 'keyboard',
    'dwellClick', 'screenRecording', 'screenSharing',
]);

export function isUserIndicator(role, parent, panel) {
    return !SYSTEM_ROLES.has(role) && parent === panel._rightBox;
}

export function readPreferences(text) {
    try {
        const data = JSON.parse(text);
        return Object.fromEntries(Object.entries(data).filter(([key, value]) =>
            key && ['menu', 'panel', 'hidden'].includes(value)));
    } catch {
        return {};
    }
}

export function topItems(quickSettings, section) {
    return [
        ...(quickSettings._system?.quickSettingsItems ?? []),
        ...(quickSettings._volumeOutput?.quickSettingsItems ?? []),
        ...(quickSettings._volumeInput?.quickSettingsItems ?? []),
        section,
    ];
}
