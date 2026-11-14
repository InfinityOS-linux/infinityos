import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const BOX_WIDTH = 640;

// A centered search box that lives inside a fullscreen, invisible, reactive
// backdrop. Clicking the backdrop (anywhere outside the box) closes the
// launcher; the input grab is best-effort, so a failed grab never freezes the
// session (Escape and the toggle hotkey always close too).
export const LauncherOverlay = GObject.registerClass(
class LauncherOverlay extends St.BoxLayout {
    _init(engine, settings, openPrefs) {
        super._init({
            style_class: 'raccoon-box',
            orientation: Clutter.Orientation.VERTICAL,
            reactive: true,
            can_focus: true,
        });

        this._engine = engine;
        this._settings = settings;
        this._openPrefs = openPrefs;
        this._results = [];
        this._selected = -1;
        this._isOpen = false;
        this._grab = null;

        // Fullscreen invisible click-catcher: reactive, sized to the whole
        // stage, with a fixed layout so the box uses absolute coordinates.
        this._backdrop = new St.Widget({
            style_class: 'raccoon-backdrop',
            reactive: true,
            layout_manager: new Clutter.FixedLayout(),
        });
        this._backdrop.add_constraint(new Clutter.BindConstraint({
            source: global.stage,
            coordinate: Clutter.BindCoordinate.ALL,
        }));
        Main.uiGroup.add_child(this._backdrop);

        this._backdrop.add_child(this);
        this._backdrop.hide();

        this._backdrop.connectObject('button-press-event',
            (_a, event) => this._onBackdropPress(event), this);

        // Header row: search entry, plus a gear button that opens preferences.
        const header = new St.BoxLayout({
            style_class: 'raccoon-header',
            x_expand: true,
        });
        this.add_child(header);

        this._entry = new St.Entry({
            style_class: 'raccoon-entry',
            hint_text: 'Search apps, do math, "g something", lock\u2026',
            can_focus: true,
            x_expand: true,
        });
        header.add_child(this._entry);

        this._settingsButton = new St.Button({
            style_class: 'raccoon-settings-button',
            can_focus: false,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._settingsButton.set_child(new St.Icon({
            icon_name: 'emblem-system-symbolic',
            style_class: 'raccoon-settings-icon',
        }));
        this._settingsButton.connectObject('clicked',
            () => this._openPreferences(), this);
        header.add_child(this._settingsButton);

        this._scroll = new St.ScrollView({style_class: 'raccoon-scroll'});
        this._scroll.set_policy(St.PolicyType.NEVER, St.PolicyType.AUTOMATIC);
        this._resultsBox = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'raccoon-results',
        });
        this._scroll.set_child(this._resultsBox);
        this.add_child(this._scroll);

        this._entry.clutter_text.connectObject(
            'text-changed', () => this._onTextChanged(),
            'key-press-event', (_a, event) => this._onKeyPress(event),
            'activate', () => this._activate(this._selected),
            this);

        // Apply the configurable box color now and on change.
        this._applyColor();
        this._settings.connectObject('changed::box-color',
            () => this._applyColor(), this);
    }

    _applyColor() {
        const color = this._settings.get_string('box-color');
        // Inline style overrides only the background; other box styling stays
        // in the .raccoon-box class.
        this.set_style(color ? `background-color: ${color};` : null);
    }

    _openPreferences() {
        // Release the grab before opening the prefs window.
        this.close();
        try {
            this._openPrefs?.();
        } catch (e) {
            logError(e, 'RaccoonLauncher: failed to open preferences');
        }
    }

    toggle() {
        if (this._isOpen)
            this.close();
        else
            this.open();
    }

    open() {
        if (this._isOpen)
            return;
        this._isOpen = true;

        const monitor = Main.layoutManager.primaryMonitor;
        this.set_width(BOX_WIDTH);
        // Coordinates are relative to the backdrop, whose origin is the stage.
        this.set_position(
            monitor.x + Math.floor((monitor.width - BOX_WIDTH) / 2),
            monitor.y + Math.floor(monitor.height * 0.18));

        this._backdrop.show();
        Main.uiGroup.set_child_above_sibling(this._backdrop, null);

        this._entry.set_text('');
        this._renderResults([]);

        // Catch Escape globally; connected before the grab so a close path
        // always exists.
        global.stage.connectObject('captured-event',
            (_a, event) => this._onCapturedEvent(event), this);

        // Best-effort input grab so keystrokes reach the entry. Never required
        // for closing, and never left dangling.
        try {
            this._grab = Main.pushModal(this._backdrop,
                {actionMode: Shell.ActionMode.NORMAL});
        } catch (e) {
            logError(e, 'RaccoonLauncher: pushModal failed; running without grab');
            this._grab = null;
        }

        // Focus the entry AFTER the grab: pushModal moves key focus to the
        // backdrop, so focusing earlier would be undone.
        this._entry.grab_key_focus();
    }

    close() {
        if (!this._isOpen)
            return;
        this._isOpen = false;

        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        global.stage.disconnectObject(this);
        this._backdrop.hide();
        this._resultsBox.destroy_all_children();
        this._results = [];
        this._selected = -1;
    }

    _onBackdropPress(event) {
        const [bx, by] = this.get_transformed_position();
        const [bw, bh] = this.get_transformed_size();
        // Not laid out yet: ignore so we don't close on the opening click.
        if (bw === 0 || bh === 0)
            return Clutter.EVENT_PROPAGATE;
        const [x, y] = event.get_coords();
        const inside = x >= bx && x < bx + bw && y >= by && y < by + bh;
        if (inside)
            return Clutter.EVENT_PROPAGATE;
        this.close();
        return Clutter.EVENT_STOP;
    }

    _onCapturedEvent(event) {
        if (event.type() === Clutter.EventType.KEY_PRESS &&
            event.get_key_symbol() === Clutter.KEY_Escape) {
            this.close();
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _onTextChanged() {
        this._renderResults(this._engine.query(this._entry.get_text()));
    }

    _onKeyPress(event) {
        const symbol = event.get_key_symbol();
        switch (symbol) {
        case Clutter.KEY_Escape:
            this.close();
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Down:
            this._move(1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Up:
            this._move(-1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Return:
        case Clutter.KEY_KP_Enter:
            this._activate(this._selected);
            return Clutter.EVENT_STOP;
        default:
            return Clutter.EVENT_PROPAGATE;
        }
    }

    _move(delta) {
        const n = this._results.length;
        if (n === 0)
            return;
        this._selected = (this._selected + delta + n) % n;
        this._updateSelection();
    }

    _renderResults(results) {
        this._resultsBox.destroy_all_children();
        this._results = results;
        this._selected = results.length > 0 ? 0 : -1;

        results.forEach((result, index) => {
            const row = new St.Button({
                style_class: 'raccoon-result',
                x_expand: true,
                can_focus: false,
            });

            const box = new St.BoxLayout({style_class: 'raccoon-result-box'});

            const icon = result.gicon
                ? new St.Icon({gicon: result.gicon, style_class: 'raccoon-result-icon'})
                : new St.Icon({
                    icon_name: result.iconName || 'application-x-executable-symbolic',
                    style_class: 'raccoon-result-icon',
                });
            box.add_child(icon);

            const textBox = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true});
            textBox.add_child(new St.Label({
                text: result.name,
                style_class: 'raccoon-result-name',
            }));
            if (result.description) {
                textBox.add_child(new St.Label({
                    text: result.description,
                    style_class: 'raccoon-result-desc',
                }));
            }
            box.add_child(textBox);

            row.set_child(box);
            row.connect('clicked', () => this._activate(index));
            this._resultsBox.add_child(row);
        });

        this._updateSelection();
    }

    _updateSelection() {
        const rows = this._resultsBox.get_children();
        rows.forEach((row, index) => {
            if (index === this._selected)
                row.add_style_class_name('selected');
            else
                row.remove_style_class_name('selected');
        });
    }

    _activate(index) {
        const result = this._results[index];
        if (!result)
            return;
        this.close();
        try {
            result.activate();
        } catch (e) {
            logError(e, 'RaccoonLauncher: failed to activate result');
        }
    }

    destroy() {
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        global.stage.disconnectObject(this);
        this._settings.disconnectObject(this);
        // Detach the box before destroying the backdrop, then chain up.
        if (this._backdrop) {
            this._backdrop.remove_child(this);
            this._backdrop.destroy();
            this._backdrop = null;
        }
        super.destroy();
    }
});

