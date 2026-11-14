import Gio from 'gi://Gio';

// Keyword-triggered web searches. Type a prefix, a space, then your query.
const ENGINES = {
    g: {name: 'Google', url: 'https://www.google.com/search?q='},
    ddg: {name: 'DuckDuckGo', url: 'https://duckduckgo.com/?q='},
    yt: {name: 'YouTube', url: 'https://www.youtube.com/results?search_query='},
    wiki: {name: 'Wikipedia', url: 'https://en.wikipedia.org/w/index.php?search='},
    gh: {name: 'GitHub', url: 'https://github.com/search?q='},
};

export class WebProvider {
    query(text) {
        const spaceIdx = text.indexOf(' ');
        if (spaceIdx === -1)
            return [];

        const key = text.slice(0, spaceIdx).toLowerCase();
        const term = text.slice(spaceIdx + 1).trim();
        const engine = ENGINES[key];
        if (!engine || !term)
            return [];

        const url = engine.url + encodeURIComponent(term);
        return [{
            id: `web-${key}`,
            name: `Search ${engine.name} for \u201c${term}\u201d`,
            description: url,
            iconName: 'web-browser-symbolic',
            score: 1500,
            activate: () => {
                Gio.AppInfo.launch_default_for_uri(url, null);
            },
        }];
    }
}

