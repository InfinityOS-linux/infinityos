import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

import {fuzzyScore} from '../util.js';

const ACTIONS = [
    {
        name: 'Lock Screen',
        icon: 'system-lock-screen-symbolic',
        keywords: ['lock', 'lock screen'],
        method: 'activateLockScreen',
    },
    {
        name: 'Log Out',
        icon: 'system-log-out-symbolic',
        keywords: ['log out', 'logout', 'sign out'],
        method: 'activateLogout',
    },
    {
        name: 'Suspend',
        icon: 'weather-clear-night-symbolic',
        keywords: ['suspend', 'sleep'],
        method: 'activateSuspend',
    },
    {
        name: 'Restart',
        icon: 'system-reboot-symbolic',
        keywords: ['restart', 'reboot'],
        method: 'activateRestart',
    },
    {
        name: 'Power Off',
        icon: 'system-shutdown-symbolic',
        keywords: ['power off', 'poweroff', 'shutdown'],
        method: 'activatePowerOff',
    },
];

// Quick system actions, dispatched through GNOME Shell's own SystemActions
// (which show the appropriate confirmation dialogs).
export class SystemProvider {
    query(text) {
        const out = [];
        for (const action of ACTIONS) {
            let best = -1;
            for (const kw of action.keywords)
                best = Math.max(best, fuzzyScore(text, kw));
            if (best < 0)
                continue;

            out.push({
                id: `sys-${action.name}`,
                name: action.name,
                description: 'System action',
                iconName: action.icon,
                score: 900 + best * 0.01,
                activate: () => SystemActions.getDefault()[action.method](),
            });
        }
        return out;
    }
}

