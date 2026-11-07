import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const MARKER = /^infinityos-liveinst-dim-(\d+)$/;

export default class InstallerDim {
    constructor() {
        this._runtime = Gio.File.new_for_path(GLib.get_user_runtime_dir());
        this._monitor = this._runtime.monitor_directory(Gio.FileMonitorFlags.NONE, null);
        this._monitor.connectObject('changed', (_monitor, file) => {
            if (MARKER.test(file.get_basename()))
                this._sync();
        }, this);
        Main.sessionMode.connectObject('updated', () => this._sync(), this);
        global.display.connectObject('notify::focus-window', () => this._place(), this);
        global.stage.connectObject('notify::size', () => this._resize(), this);
        this._sync();
    }

    _hasInstaller() {
        const entries = this._runtime.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
        try {
            for (let entry; (entry = entries.next_file(null));) {
                const match = MARKER.exec(entry.get_name());
                if (!match)
                    continue;
                if (GLib.file_test(`/proc/${match[1]}`, GLib.FileTest.EXISTS))
                    return true;
                try {
                    this._runtime.get_child(entry.get_name()).delete(null);
                } catch {
                    // Another cleanup may have removed the stale marker.
                }
            }
            return false;
        } finally {
            entries.close(null);
        }
    }

    _sync() {
        const active = Main.sessionMode.currentMode === 'user' && this._hasInstaller();
        if (active && !this._dim) {
            this._dim = new St.Widget({
                reactive: false,
                opacity: 0,
                style: 'background-color: rgba(0, 0, 0, 0.65);',
            });
            this._resize();
            global.window_group.add_child(this._dim);
            global.window_group.set_child_above_sibling(this._dim, null);
            this._dim.ease({ opacity: 255, duration: 280, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
        } else if (!active && this._dim) {
            const dim = this._dim;
            this._dim = null;
            dim.ease({ opacity: 0, duration: 220, mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onComplete: () => dim.destroy() });
        }
        if (active && !this._pollId) {
            this._pollId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
                this._sync();
                if (this._dim)
                    return GLib.SOURCE_CONTINUE;
                this._pollId = 0;
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    _place() {
        if (!this._dim)
            return;
        // shortcut: follow focus until Anaconda exposes a stable window identity across sessions.
        const actor = global.display.focus_window?.get_compositor_private();
        if (actor?.get_parent() === global.window_group && actor !== this._dim)
            global.window_group.set_child_below_sibling(this._dim, actor);
    }

    _resize() {
        this._dim?.set_size(global.stage.width, global.stage.height);
    }

    destroy() {
        this._monitor.cancel();
        this._monitor.disconnectObject(this);
        Main.sessionMode.disconnectObject(this);
        global.display.disconnectObject(this);
        global.stage.disconnectObject(this);
        if (this._pollId)
            GLib.source_remove(this._pollId);
        this._dim?.destroy();
        this._dim = null;
    }
}
