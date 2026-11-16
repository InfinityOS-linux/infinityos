import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import {isUserIndicator, readPreferences, topItems} from './trayLayout.js';
import {trayText} from './trayStrings.js';

// Move the actual actors, preserving app menus, icons, badges and scroll actions.
export default class UserTray {
    constructor() {
        this._entries = new Map();
        this._signals = [];
        this._idle = 0;
        this._destroyed = false;
        this._file = Gio.File.new_for_path(GLib.build_filenamev([
            GLib.get_user_config_dir(), 'infinityos', 'tray.json',
        ]));
        this._preferences = {};
        try {
            const [ok, bytes] = this._file.load_contents(null);
            if (ok)
                this._preferences = readPreferences(new TextDecoder().decode(bytes));
        } catch (error) {
            if (!error.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.NOT_FOUND))
                console.warn(`InfinityOS tray preferences: ${error}`);
        }
        this._quick = Main.panel.statusArea.quickSettings;
        this._grid = this._quick.menu._grid;
        this._originalOrder = this._grid.get_children();
        this._section = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true});
        // Inherit the theme's neutral separators, including in light mode.
        this._separators = [new PopupMenu.PopupSeparatorMenuItem(),
            new PopupMenu.PopupSeparatorMenuItem()];
        this._section.add_child(this._separators[0]);
        this._icons = new St.Widget({layout_manager: new Clutter.GridLayout({column_spacing: 8, row_spacing: 6}),
            style_class: 'infinity-user-tray-icons',
            x_align: Clutter.ActorAlign.START, x_expand: false, style: 'margin: 2px 0;'});
        this._section.add_child(this._icons);
        this._section.add_child(this._separators[1]);
        this._manage = new St.Button({style_class: 'button', can_focus: true,
            style: 'width: 32px; height: 32px; min-width: 0; min-height: 0; padding: 0; margin: 0;',
            accessible_name: trayText('manage'),
            child: new St.Icon({icon_name: 'view-more-symbolic', icon_size: 18})});
        this._manage.connect('clicked', () => this._openMenu(this._manage));
        this._menus = new PopupMenu.PopupMenuManager(this._manage);
        this._quick.menu.addItem(this._section, 2);
        this._watch(this._quick.menu, 'open-state-changed', (_menu, open) => {
            if (open)
                this._sync();
            else {
                this._menus.activeMenu?.close();
                this._context?.close();
            }
        });
        this._watch(Main.sessionMode, 'updated', () => this._sync());
        this._watch(Main.panel._rightBox, 'child-added', () => this._queueSync());
        this._watch(this._grid, 'child-added', () => this._queueSync());
        // addToStatusArea completes registration after child-added is emitted.
        this._injections = new InjectionManager();
        const tray = this;
        this._injections.overrideMethod(Main.panel, 'addToStatusArea', original =>
            function (...args) {
                const result = original.apply(this, args);
                tray._queueSync();
                return result;
            });
        this._sync();
    }

    _watch(object, signal, callback) {
        this._signals.push([object, object.connect(signal, callback)]);
    }

    _queueSync() {
        if (this._idle || this._destroyed)
            return;
        this._idle = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._idle = 0;
            this._sync();
            return GLib.SOURCE_REMOVE;
        });
    }

    _sync() {
        if (this._destroyed)
            return;
        for (const [role, indicator] of Object.entries(Main.panel.statusArea)) {
            const actor = indicator.container;
            if (!actor || this._entries.has(indicator) ||
                !isUserIndicator(role, actor.get_parent(), Main.panel))
                continue;
            const parent = actor.get_parent();
            const key = String(indicator._indicator?.id ?? role);
            const entry = {indicator, actor, parent, key,
                index: parent.get_children().indexOf(actor),
                style: actor.get_style(), menu: null,
                wrapper: new St.Bin({y_align: Clutter.ActorAlign.CENTER})};
            this._entries.set(indicator, entry);
            // Capture before the app's right-click handler or click gesture.
            entry.event = indicator.connect('captured-event', (_actor, event) => {
                if ((event.type() === Clutter.EventType.BUTTON_PRESS ||
                     event.type() === Clutter.EventType.BUTTON_RELEASE) && event.get_button() === 3) {
                    if (event.type() === Clutter.EventType.BUTTON_PRESS)
                        this._openMenu(indicator, entry);
                    return Clutter.EVENT_STOP;
                }
                if (event.type() === Clutter.EventType.KEY_PRESS &&
                    (event.get_key_symbol() === Clutter.KEY_Menu ||
                    (event.get_key_symbol() === Clutter.KEY_F10 &&
                    (event.get_state() & Clutter.ModifierType.SHIFT_MASK)))) {
                    this._openMenu(indicator, entry);
                    return Clutter.EVENT_STOP;
                }
                return Clutter.EVENT_PROPAGATE;
            });
            entry.destroy = indicator.connect('destroy', () => {
                if (entry.menu)
                    this._menus.removeMenu(entry.menu);
                this._entries.delete(indicator);
                entry.wrapper.set_child(null);
                entry.wrapper.destroy();
                this._queueSync();
            });
            parent.remove_child(actor);
            entry.wrapper.set_child(actor);
        }
        const unlocked = Main.sessionMode.currentMode === 'user' && !Main.sessionMode.isLocked;
        let position = 0;
        for (const entry of this._entries.values()) {
            const location = this._preferences[entry.key] ?? 'menu';
            const pinned = location === 'panel';
            const parent = pinned ? entry.parent : this._icons;
            if (entry.wrapper.get_parent() !== parent) {
                entry.wrapper.get_parent()?.remove_child(entry.wrapper);
                if (pinned)
                    parent.insert_child_at_index(entry.wrapper, entry.index);
            }
            if (!pinned) {
                // Reattach only when necessary, to update row/column after hiding.
                entry.wrapper.get_parent()?.remove_child(entry.wrapper);
                this._icons.layout_manager.attach(entry.wrapper, position % 6,
                    Math.floor(position / 6), 1, 1);
                if (location !== 'hidden')
                    position++;
            }
            entry.wrapper.visible = unlocked && location !== 'hidden';
            entry.actor.set_style(pinned ? entry.style : 'width: 32px; height: 32px; min-width: 0; min-height: 0; padding: 0;');
            // Use a separate manager for nested menus so opening an app does
            // not close Quick Settings and unmap the menu's source actor.
            const menu = entry.indicator.menu;
            if (entry.menu !== menu) {
                if (entry.menu)
                    this._menus.removeMenu(entry.menu);
                entry.menu = menu;
            }
            if (menu) {
                if (pinned) {
                    this._menus.removeMenu(menu);
                    Main.panel.menuManager.addMenu(menu);
                } else {
                    Main.panel.menuManager.removeMenu(menu);
                    this._menus.addMenu(menu);
                }
            }
        }
        this._manage.get_parent()?.remove_child(this._manage);
        this._icons.layout_manager.attach(this._manage, position % 6,
            Math.floor(position / 6), 1, 1);
        this._section.visible = unlocked && this._entries.size > 0;
        if (!unlocked) {
            this._menus.activeMenu?.close();
            this._context?.close();
        }
        let order = 0;
        for (const item of topItems(this._quick, this._section)) {
            if (item.get_parent() !== this._grid)
                continue;
            this._grid.set_child_at_index(item, order++);
        }
    }

    _setLocation(entry, location) {
        const next = {...this._preferences, [entry.key]: location};
        try {
            GLib.mkdir_with_parents(this._file.get_parent().get_path(), 0o700);
            this._file.replace_contents(new TextEncoder().encode(JSON.stringify(next)),
                null, false, Gio.FileCreateFlags.PRIVATE, null);
            this._preferences = next;
            entry.menu?.close();
            this._sync();
        } catch (error) {
            Main.notifyError(trayText('manage'), String(error));
        }
    }

    _openMenu(source, selected = null) {
        this._context?.destroy();
        const menu = new PopupMenu.PopupMenu(source, 0.5, St.Side.TOP);
        this._context = menu;
        Main.uiGroup.add_child(menu.actor);
        menu.actor.hide();
        // A separate grab also works when the source is pinned to the panel.
        this._contextManager ??= new PopupMenu.PopupMenuManager(this._manage);
        this._contextManager.addMenu(menu);
        const entries = selected ? [selected] : [...this._entries.values()];
        for (const entry of entries) {
            const location = this._preferences[entry.key] ?? 'menu';
            const label = entry.indicator.accessible_name || entry.key;
            const target = selected ? menu : new PopupMenu.PopupSubMenuMenuItem(label);
            if (!selected)
                menu.addMenuItem(target);
            const actions = selected ? target : target.menu;
            actions.addAction(trayText(location === 'hidden' ? 'show' : 'hide'), () =>
                this._setLocation(entry, location === 'hidden' ? 'menu' : 'hidden'));
            actions.addAction(trayText(location === 'panel' ? 'menu' : 'panel'), () =>
                this._setLocation(entry, location === 'panel' ? 'menu' : 'panel'));
        }
        menu.open();
    }

    destroy() {
        this._destroyed = true;
        if (this._idle)
            GLib.source_remove(this._idle);
        this._injections.clear();
        this._signals.forEach(([object, id]) => object.disconnect(id));
        this._context?.destroy();
        this._menus.activeMenu?.close();
        for (const entry of this._entries.values()) {
            entry.indicator.disconnect(entry.event);
            entry.indicator.disconnect(entry.destroy);
            if (entry.menu) {
                this._menus.removeMenu(entry.menu);
                Main.panel.menuManager.addMenu(entry.menu);
            }
            entry.wrapper.set_child(null);
            entry.actor.set_style(entry.style);
            entry.parent.insert_child_at_index(entry.actor, entry.index);
            entry.wrapper.destroy();
        }
        this._entries.clear();
        this._section.destroy();
        // The original order may contain indicators destroyed in the meantime.
        const children = this._grid.get_children();
        let order = 0;
        for (const item of this._originalOrder) {
            if (!children.includes(item))
                continue;
            this._grid.set_child_at_index(item, order++);
        }
    }
}
