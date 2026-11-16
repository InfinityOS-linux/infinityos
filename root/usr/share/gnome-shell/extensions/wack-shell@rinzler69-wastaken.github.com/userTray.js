import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const CORE_ROLES = new Set(['quickSettings', 'aggregateMenu', 'dateMenu', 'activities',
    'a11y', 'keyboard', 'screenRecording', 'screenSharing', 'dwellClick', 'unsafeMode']);
export const trayPlacement = (preferences, role) =>
    ['hidden', 'panel'].includes(preferences[role]) ? preferences[role] : 'menu';
export const trayRows = (items, columns = 6) =>
    Array.from({length: Math.ceil(items.length / columns)}, (_, i) => items.slice(i * columns, (i + 1) * columns));

export default class UserTray {
    constructor(extension) {
        this._settings = extension._settings;
        this._ = extension.gettext.bind(extension);
        this._entries = new Map();
        this._showHidden = false;
        this._quick = Main.panel.statusArea.quickSettings;
        if (!this._quick?.menu?._grid)
            return;
        this._section = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'infinity-user-tray', reactive: true});
        this._parking = new St.BoxLayout({visible: false});
        this._section.add_child(this._parking);
        this._body = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'infinity-user-tray-body'});
        this._section.add_child(new St.Widget({style_class: 'infinity-tray-divider'}));
        this._section.add_child(this._body);
        this._section.add_child(new St.Widget({style_class: 'infinity-tray-divider'}));
        this._manager = new PopupMenu.PopupMenuManager(this._section);
        const grid = this._quick.menu._grid;
        const topItems = [this._quick._system, this._quick._volumeOutput, this._quick._volumeInput]
            .flatMap(indicator => indicator?.quickSettingsItems ?? []);
        const children = grid.get_children();
        const lastTop = Math.max(-1, ...topItems.map(item => children.indexOf(item)));
        this._quick.menu.insertItemBefore(this._section, children[lastTop + 1] ?? null, 2);
        this._panelBoxes = [Main.panel._leftBox, Main.panel._centerBox, Main.panel._rightBox];
        for (const box of this._panelBoxes)
            box.connectObject('child-added', () => this._queueSync(), this);
        this._quick.menu.connectObject('open-state-changed', (_menu, open) => {
            if (open) this._sync();
            else {
                this._context?.close();
                this._manager.activeMenu?.close();
            }
        }, this);
        Main.sessionMode.connectObject('updated', () => this._sync(), this);
        this._settings.connectObject('changed::user-tray-placements', () => this._sync(), this);
        global.stage.connectObject('captured-event', (_stage, event) => this._onEvent(event), this);
        this._sync();
    }

    _queueSync() {
        if (this._idle || this._syncing) return;
        this._idle = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._idle = 0;
            this._sync();
            return GLib.SOURCE_REMOVE;
        });
    }

    _preferences() {
        return this._settings.get_value('user-tray-placements').deep_unpack();
    }

    _setPlacement(role, placement) {
        this._context?.close();
        const preferences = this._preferences();
        if (placement === 'menu') delete preferences[role];
        else preferences[role] = placement;
        this._settings.set_value('user-tray-placements', new GLib.Variant('a{ss}', preferences));
    }

    _move(actor, parent, index = -1) {
        if (actor.get_parent() === parent) return;
        actor.get_parent()?.remove_child(actor);
        if (index >= 0) parent.insert_child_at_index(actor, index);
        else parent.add_child(actor);
    }

    _sync() {
        if (!this._section || this._syncing) return;
        this._syncing = true;
        try {
            for (const [role, indicator] of Object.entries(Main.panel.statusArea)) {
                const actor = indicator?.container;
                if (CORE_ROLES.has(role) || this._entries.has(role) ||
                    !actor || (actor.get_parent() !== Main.panel._rightBox &&
                        !(role.startsWith('appindicator-') && this._panelBoxes.includes(actor.get_parent()))))
                    continue;
                const key = indicator._indicator?.id ? `appindicator:${indicator._indicator.id}` : role;
                const entry = {role, key, indicator, actor, parent: actor.get_parent(),
                    index: actor.get_parent().get_children().indexOf(actor),
                    style: actor.get_style(), clip: actor.clip_to_allocation, opacity: actor.opacity};
                this._entries.set(role, entry);
                actor.connectObject('destroy', () => {
                    this._entries.delete(role);
                    this._queueSync();
                }, this);
            }
            const preferences = this._preferences();
            const active = !Main.sessionMode.isLocked && Main.sessionMode.currentMode === 'user';
            this._section.visible = active;
            const items = [];
            for (const entry of this._entries.values()) {
                const mode = trayPlacement(preferences, entry.key);
                const inMenu = mode !== 'panel';
                if (entry.indicator.menu && entry.inMenu !== inMenu) {
                    entry.indicator.menu.close({animate: false});
                    (inMenu ? Main.panel.menuManager : this._manager).removeMenu(entry.indicator.menu);
                    (inMenu ? this._manager : Main.panel.menuManager).addMenu(entry.indicator.menu);
                }
                entry.inMenu = inMenu;
                if (!inMenu) {
                    this._restoreActor(entry);
                } else {
                    this._move(entry.actor, this._parking);
                    entry.actor.add_style_class_name('infinity-tray-icon');
                    entry.actor.set_style(`${entry.style ?? ''}; width: 40px; min-width: 40px; max-width: 40px; height: 40px; padding: 0;`);
                    entry.actor.clip_to_allocation = true;
                    entry.actor.opacity = mode === 'hidden' ? 120 : 255;
                    if (mode !== 'hidden' || this._showHidden) items.push(entry.actor);
                }
            }
            this._body.destroy_all_children();
            for (const rowItems of trayRows(items)) {
                const row = new St.BoxLayout({style_class: 'infinity-tray-row', x_align: Clutter.ActorAlign.CENTER});
                this._body.add_child(row);
                for (const actor of rowItems) this._move(actor, row);
            }
            if (Object.values(preferences).includes('hidden')) {
                const toggle = new St.Button({label: this._(this._showHidden ? 'Hide hidden icons' : 'Show hidden'),
                    style_class: 'infinity-tray-hidden-toggle', can_focus: true});
                toggle.connect('clicked', () => { this._showHidden = !this._showHidden; this._sync(); });
                this._body.add_child(toggle);
            }
            this._section.visible = active && (items.length > 0 || Object.values(preferences).includes('hidden'));
        } finally {
            this._syncing = false;
        }
    }

    _restoreActor(entry) {
        entry.actor.remove_style_class_name('infinity-tray-icon');
        entry.actor.set_style(entry.style);
        entry.actor.clip_to_allocation = entry.clip;
        entry.actor.opacity = entry.opacity;
        this._move(entry.actor, entry.parent, entry.index);
    }

    _onEvent(event) {
        if (Main.sessionMode.isLocked) return Clutter.EVENT_PROPAGATE;
        const keyboard = event.type() === Clutter.EventType.KEY_PRESS &&
            (event.get_key_symbol() === Clutter.KEY_Menu ||
             (event.get_key_symbol() === Clutter.KEY_F10 && (event.get_state() & Clutter.ModifierType.SHIFT_MASK)));
        const pointer = event.type() === Clutter.EventType.BUTTON_PRESS && event.get_button() === 3;
        if (!keyboard && !pointer) return Clutter.EVENT_PROPAGATE;
        const [x, y] = event.get_coords();
        const target = keyboard ? global.stage.get_key_focus()
            : global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y);
        if (!target) return Clutter.EVENT_PROPAGATE;
        const entry = [...this._entries.values()].find(item => item.actor === target || item.actor.contains(target));
        if (!entry && !this._section?.contains(target)) return Clutter.EVENT_PROPAGATE;
        this._openContext(entry, entry?.indicator ?? this._section);
        return Clutter.EVENT_STOP;
    }

    _destroyContext() {
        const menu = this._context;
        this._context = null;
        if (!menu) return;
        menu.close({animate: false});
        menu.actor.remove_all_transitions();
        // Remove the popup from its parent before disposing its BoxPointer bin.
        // Otherwise a queued parent allocation can measure the disposed popup.
        menu.actor.hide();
        menu.actor.get_parent()?.remove_child(menu.actor);
        menu.destroy();
    }

    _openContext(entry, anchor) {
        this._destroyContext();
        const menu = new PopupMenu.PopupMenu(anchor, 0.5, St.Side.TOP);
        this._context = menu;
        Main.uiGroup.add_child(menu.actor);
        menu.actor.hide();
        this._manager.addMenu(menu);
        if (entry) {
            const hidden = trayPlacement(this._preferences(), entry.key) === 'hidden';
            menu.addAction(this._(hidden ? 'Show' : 'Hide'), () => this._setPlacement(entry.key, hidden ? 'menu' : 'hidden'));
        }
        menu.addAction(this._('Show hidden'), () => { this._showHidden = true; this._sync(); });
        if (entry) {
            const pinned = trayPlacement(this._preferences(), entry.key) === 'panel';
            menu.addAction(this._(pinned ? 'Move to menu' : 'Move to panel'), () =>
                this._setPlacement(entry.key, pinned ? 'menu' : 'panel'));
        }
        menu.open();
    }

    destroy() {
        if (this._idle) GLib.source_remove(this._idle);
        global.stage.disconnectObject(this);
        for (const box of this._panelBoxes ?? []) box.disconnectObject(this);
        Main.sessionMode.disconnectObject(this);
        this._settings.disconnectObject(this);
        this._quick?.menu.disconnectObject(this);
        this._destroyContext();
        for (const entry of this._entries.values()) {
            entry.actor.disconnectObject(this);
            if (entry.inMenu && entry.indicator.menu) {
                entry.indicator.menu.close({animate: false});
                this._manager.removeMenu(entry.indicator.menu);
                Main.panel.menuManager.addMenu(entry.indicator.menu);
            }
            this._restoreActor(entry);
        }
        this._entries.clear();
        this._section?.destroy();
    }
}
