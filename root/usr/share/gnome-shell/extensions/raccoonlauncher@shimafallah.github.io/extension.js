import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {SearchEngine} from './lib/search.js';
import {LauncherOverlay} from './lib/overlay.js';

const TOGGLE_KEY = 'toggle-launcher';

export default class RaccoonLauncherExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._engine = new SearchEngine(this._settings);
        this._overlay = new LauncherOverlay(
            this._engine,
            this._settings,
            () => this.openPreferences());

        Main.wm.addKeybinding(
            TOGGLE_KEY,
            this._settings,
            Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW,
            () => this._overlay.toggle()
        );
    }

    disable() {
        // disable() must tear down everything we created in enable().
        Main.wm.removeKeybinding(TOGGLE_KEY);

        this._overlay?.destroy();
        this._overlay = null;

        this._engine?.destroy();
        this._engine = null;

        this._settings = null;
    }
}

