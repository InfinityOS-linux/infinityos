// System indicators, including the updater, always stay in the top panel.
const SYSTEM_ROLES = new Set([
    'activities', 'appMenu', 'dateMenu', 'quickSettings', 'a11y', 'keyboard',
    'dwellClick', 'screenRecording', 'screenSharing', 'infinity-updater', 'media-controls',
]);

export function isUserIndicator(role, parent, panel) {
    return !SYSTEM_ROLES.has(role) && parent === panel._rightBox;
}

function legacyPreferenceKey(role) {
    const wmClass = /^appindicator-legacy:(.+):\d+$/.exec(role)?.[1].toLowerCase();
    return wmClass && wmClass !== 'null' && wmClass !== 'undefined'
        ? `appindicator-legacy:${wmClass}` : null;
}

export function trayPreferenceKey(role, indicator) {
    const notifier = indicator._indicator;
    const id = notifier?.id;
    if (!id)
        return legacyPreferenceKey(role) ?? role;
    // Some Electron versions use the same ID in every application.
    if (/^chrome_status_icon(?:_\d+)?$/.test(id)) {
        const app = notifier.preferenceAppId;
        return app ? `appindicator:${app}:${id}` : role;
    }
    return id;
}

export function trayLocation(preferences, {key, role}) {
    if (Object.hasOwn(preferences, key))
        return preferences[key];
    if (Object.hasOwn(preferences, role))
        return preferences[role];

    // Older versions saved XEmbed choices under a role containing the PID.
    if (legacyPreferenceKey(role)) {
        const previous = Object.keys(preferences).findLast(saved => legacyPreferenceKey(saved) === key);
        if (previous)
            return preferences[previous];
    }
    return 'menu';
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
