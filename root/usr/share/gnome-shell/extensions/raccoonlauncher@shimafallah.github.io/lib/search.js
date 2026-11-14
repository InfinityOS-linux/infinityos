import {AppsProvider} from './providers/apps.js';
import {CalcProvider} from './providers/calc.js';
import {WebProvider} from './providers/web.js';
import {SystemProvider} from './providers/system.js';

// Routes a query to every enabled provider, merges the results,
// and returns them ranked by score (highest first).
export class SearchEngine {
    constructor(settings) {
        this._settings = settings;
        this._providers = [
            {key: 'enable-calc', provider: new CalcProvider()},
            {key: 'enable-web', provider: new WebProvider()},
            {key: 'enable-system', provider: new SystemProvider()},
            {key: 'enable-apps', provider: new AppsProvider()},
        ];
    }

    query(text) {
        text = (text || '').trim();
        if (!text)
            return [];

        let results = [];
        for (const {key, provider} of this._providers) {
            if (!this._settings.get_boolean(key))
                continue;
            try {
                results.push(...provider.query(text));
            } catch (e) {
                logError(e, `RaccoonLauncher: provider "${key}" failed`);
            }
        }

        results.sort((a, b) => b.score - a.score);
        return results.slice(0, this._settings.get_int('max-results'));
    }

    destroy() {
        for (const {provider} of this._providers)
            provider.destroy?.();
        this._providers = [];
    }
}

