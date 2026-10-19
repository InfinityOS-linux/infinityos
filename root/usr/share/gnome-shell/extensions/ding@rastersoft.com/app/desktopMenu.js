/* DING: Desktop Icons New Generation for GNOME Shell
 *
 * Copyright (C) 2025 Sergio Costas (rastersoft@gmail.com)
 *
 * Some code from Gtk4 DING version by (C) Sundeep Mediratta (smedius@gmail.com)
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
// SPDX-License-Identifier: GPL-3.0-only
'use strict';
import * as DBusUtils from './dbusUtils.js';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GioUnix from 'gi://GioUnix';
import Gtk from 'gi://Gtk?version=4.0';
import Gdk from 'gi://Gdk?version=4.0';
import * as Prefs from './preferences.js';

import * as TemplatesScriptsManager from './templatesScriptsManager.js';
import * as DesktopIconsUtil from './desktopIconsUtil.js';
import * as MenuHelper from './menuHelper.js';
import * as Enums from './enums.js';

const Gettext = imports.gettext.domain('ding');

const _ = Gettext.gettext;

export var DesktopMenu = class extends MenuHelper.MenuHelper {
    constructor(desktopManager, mainApp, dbusManager) {
        super(desktopManager, mainApp);

        this._dbusManager = dbusManager;
        this._lastBgMenu = null;
        this._bgMenus = new WeakMap();
        this._bgMenuModels = new Map();
        this._menuRequest = 0;
        this._lastMenuClosedAt = 0;
        this._closingBgMenu = null;
        this._closeSourceId = 0;
        this.templatesMonitor = new TemplatesScriptsManager.TemplatesScriptsManager(
            DesktopIconsUtil.getTemplatesDir(),
            TemplatesScriptsManager.TemplatesScriptsManagerFlags.HIDE_EXTENSIONS
        );
        this._desktopDir = DesktopIconsUtil.getDesktopDir();
        this._addActions();
    }

    setClickCoordinates(x, y) {
        this._clickX = Math.floor(x);
        this._clickY = Math.floor(y);
    }

    _newDocument(menuItem, variantPath) {
        const file = Gio.File.new_for_path(variantPath.get_string()[0]);
        if ((file === null) || !file.query_exists(null))
            return;


        const fullName = file.get_basename();
        const finalName = this._desktopManager.getDesktopUniqueFileName(fullName);

        const destination = Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP), finalName]));

        try {
            file.copy(destination, Gio.FileCopyFlags.NONE, null, null);
            const info = new Gio.FileInfo();
            info.set_attribute_string('metadata::nautilus-drop-position', `${this._clickX},${this._clickY}`);
            info.set_attribute_string('metadata::nautilus-icon-position', '');
            destination.set_attributes_from_info(info, Gio.FileQueryInfoFlags.NONE, null);
        } catch (e) {
            console.error(e, `Failed to create template ${e.message}`);
            const header = _('Template Creation Failed');
            const text = _('Error while trying to create a Document');
            this._dbusManager.doNotify(header, text);
        }
    }

    _onOpenDesktopInFilesClicked() {
        const context = Gdk.Display.get_default().get_app_launch_context();
        // context.set_timestamp(Gtk.get_current_event_time());
        Gio.AppInfo.launch_default_for_uri_async(this._desktopDir.get_uri(),
            context, null,
            (source, result) => {
                try {
                    Gio.AppInfo.launch_default_for_uri_finish(result);
                } catch (e) {
                    console.log(`Error opening Desktop in Files: ${e.message}`);
                }
            }
        );
    }

    _addActions() {
        this._addNewAction('changeDesktopIconSettings', null, Prefs.showPreferences);
        this._addNewAction('new-folder', ['<Control><Shift>n'], () => this._desktopManager.doNewFolder());
        this._addNewAction('create-template', null, this._newDocument.bind(this), 's');
        this._pasteAction = this._addNewAction('paste', null, () => this._desktopManager.doPaste(false));
        this._addNewAction('undo', ['<Control>z'], () => {
            DBusUtils.RemoteFileOperations.UndoRemote();
        });
        this._addNewAction('redo', ['<Control><Shift>z'], () => {
            DBusUtils.RemoteFileOperations.RedoRemote();
        });
        this._addNewAction('select-all', null, () => this._desktopManager.selectAll());
        this._addNewAction('arrange-icons', null, () => this._desktopManager.sortAllFilesFromGridsByPosition());
        this._addNewActionBoolean('keep-arranged');
        this._addNewActionBoolean('keep-stacked');
        this._addNewActionBoolean('sort-special-folders');
        this._addNewActionSelection('arrangeorder');
        this._addNewAction('show-in-files', null, () => this._onOpenDesktopInFilesClicked());
        this._addNewAction('open-in-terminal-desktop', null, () => {
            DesktopIconsUtil.launchTerminal(this._desktopDir.get_path(), null);
        });
        this._addNewAction('change-background', null, () => {
            const desktopFile = GioUnix.DesktopAppInfo.new('gnome-background-panel.desktop');
            const context = Gdk.Display.get_default().get_app_launch_context();
            context.set_timestamp(Gdk.CURRENT_TIME);
            desktopFile.launch([], context);
        });
        this._addNewAction('show-settings', null, () => {
            if (GLib.getenv('XDG_CURRENT_DESKTOP').split(':').includes('ubuntu')) {
                const desktopFile = GioUnix.DesktopAppInfo.new('gnome-ubuntu-panel.desktop');
                const context = Gdk.Display.get_default().get_app_launch_context();
                // context.set_timestamp(Gtk.get_current_event_time());
                desktopFile.launch([], context);
            } else {
                Prefs.showPreferences();
            }
        });
        this._addNewAction('display-settings', null, () => {
            const desktopFile = GioUnix.DesktopAppInfo.new('gnome-display-panel.desktop');
            const context = Gdk.Display.get_default().get_app_launch_context();
            context.set_timestamp(Gdk.CURRENT_TIME);
            desktopFile.launch([], context);
        });
    }

    hideDesktopMenu(animate = true) {
        if (!animate)
            this._finishClosingMenu();
        if (this._lastBgMenu === null)
            return;
        const bgMenu = this._lastBgMenu;
        this._menuRequest++;
        this._lastBgMenu = null;
        if (!bgMenu.menuPopover.get_visible())
            return;

        if (!animate || !Gtk.Settings.get_default()?.gtk_enable_animations) {
            bgMenu.menuPopover.popdown();
            return;
        }

        this._closingBgMenu = bgMenu;
        bgMenu.menuPopover.add_css_class('menu-exit');
        this._closeSourceId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 110, () => {
            this._closeSourceId = 0;
            if (this._closingBgMenu === bgMenu)
                this._closingBgMenu = null;
            bgMenu.menuPopover.popdown();
            bgMenu.menuPopover.remove_css_class('menu-exit');
            return GLib.SOURCE_REMOVE;
        });
    }

    _finishClosingMenu() {
        if (this._closeSourceId) {
            GLib.source_remove(this._closeSourceId);
            this._closeSourceId = 0;
        }
        if (this._closingBgMenu) {
            const bgMenu = this._closingBgMenu;
            this._closingBgMenu = null;
            bgMenu.menuPopover.popdown();
            bgMenu.menuPopover.remove_css_class('menu-exit');
        }
    }

    showDesktopMenu(x, y, grid) {
        if (this._closingBgMenu) {
            this._finishClosingMenu();
            this._lastMenuClosedAt = 0;
        }
        // An outside right click can close the popover and reach the desktop
        // gesture in the same event. Do not immediately reopen it.
        if (GLib.get_monotonic_time() - this._lastMenuClosedAt < 100000)
            return;

        if (this._lastBgMenu !== null) {
            this.hideDesktopMenu();
            return;
        }

        this._pasteAction.enabled = false;

        const undoredo = this._syncUndoRedo();
        const menuKey = `${undoredo.undo}:${undoredo.redo}:${this.templatesMonitor.entriesRevision}`;
        if (this._bgMenuRevision !== this.templatesMonitor.entriesRevision) {
            this._bgMenuModels.clear();
            this._bgMenuRevision = this.templatesMonitor.entriesRevision;
        }
        let menu = this._bgMenuModels.get(menuKey);
        if (!menu) {
            menu = this._createDesktopBackgroundMenu(undoredo);
            this._bgMenuModels.set(menuKey, menu);
        }

        let bgMenu = this._bgMenus.get(grid);
        if (!bgMenu) {
            const menuPopover = Gtk.PopoverMenu.new_from_model_full(menu, Gtk.PopoverMenuFlags.NESTED);
            menuPopover.add_css_class('desktopmenu');
            grid.put(menuPopover, x, y);
            bgMenu = {menuPopover, menuKey, enterSourceId: 0};
            this._bgMenus.set(grid, bgMenu);
            menuPopover.connect('closed', () => {
                if (bgMenu.enterSourceId) {
                    GLib.source_remove(bgMenu.enterSourceId);
                    bgMenu.enterSourceId = 0;
                    menuPopover.remove_css_class('menu-enter');
                }
                this._lastMenuClosedAt = GLib.get_monotonic_time();
                if (this._closingBgMenu === bgMenu)
                    this._finishClosingMenu();
                if (this._lastBgMenu === bgMenu)
                    this._lastBgMenu = null;
                this._menuRequest++;
            });
        } else {
            grid.move(bgMenu.menuPopover, x, y);
            if (bgMenu.menuKey !== menuKey) {
                bgMenu.menuPopover.set_menu_model(menu);
                bgMenu.menuKey = menuKey;
            }
        }

        const rect = new Gdk.Rectangle();
        rect.x = x;
        rect.y = y;
        rect.width = 1;
        rect.height = 1;
        bgMenu.menuPopover.set_pointing_to(rect);
        if (Gtk.Settings.get_default()?.gtk_enable_animations) {
            bgMenu.menuPopover.add_css_class('menu-enter');
            bgMenu.enterSourceId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 20, () => {
                bgMenu.enterSourceId = 0;
                bgMenu.menuPopover.remove_css_class('menu-enter');
                return GLib.SOURCE_REMOVE;
            });
        }
        this._lastBgMenu = bgMenu;
        bgMenu.menuPopover.popup();
        const request = ++this._menuRequest;
        this._desktopManager.updateClipboard().then(enabled => {
            if (request === this._menuRequest && this._lastBgMenu === bgMenu)
                this._pasteAction.enabled = enabled;
        }).catch(e => console.log(`Error updating clipboard: ${e.message}`));
    }

    _syncUndoRedo() {
        if (!DBusUtils.RemoteFileOperations.isAvailable)
            return {undo: false, redo: false};

        switch (DBusUtils.RemoteFileOperations.UndoStatus()) {
        case Enums.UndoStatus.UNDO:
            return {undo: true, redo: false};
        case Enums.UndoStatus.REDO:
            return {undo: false, redo: true};
        default:
            return {undo: false, redo: false};
        }
    }

    _addSortingSubMenu() {
        const arrangeSubMenu = new Gio.Menu();

        const section = this._newSection(arrangeSubMenu);
        this._newMenuElement(_('Keep Arranged...'), 'keep-arranged', section);
        this._newMenuElement(_('Keep Stacked by type...'), 'keep-stacked', section);
        this._newMenuElement(_('Sort Home/Drives/Trash...'), 'sort-special-folders', section);

        this._newMenuElement(_('Sort by Name'), 'arrangeorder', section, GLib.Variant.new_string('NAME'));
        this._newMenuElement(_('Sort by Name Descending'), 'arrangeorder', section, GLib.Variant.new_string('DESCENDINGNAME'));
        this._newMenuElement(_('Sort by Modified Time'), 'arrangeorder', section, GLib.Variant.new_string('MODIFIEDTIME'));
        this._newMenuElement(_('Sort by Type'), 'arrangeorder', section, GLib.Variant.new_string('KIND'));
        this._newMenuElement(_('Sort by Size'), 'arrangeorder', section, GLib.Variant.new_string('SIZE'));

        return arrangeSubMenu;
    }

    _createDesktopBackgroundMenu(undoredo) {
        const menuContainer = new Gio.Menu();
        let section = this._newSection(menuContainer);
        this._newMenuElement(_('New Folder'), 'new-folder', section);

        const templates = this.templatesMonitor.createMenu();
        if (templates !== null)
            section.append_submenu(_('New Document'), templates);


        section = this._newSection(menuContainer);
        this._newMenuElement(_('Paste'), 'paste', section);
        if (undoredo.undo)
            this._newMenuElement(_('Undo'), 'undo', section);

        if (undoredo.redo)
            this._newMenuElement(_('Redo'), 'redo', section);


        section = this._newSection(menuContainer);
        this._newMenuElement(_('Select All'), 'select-all', section);

        section = this._newSection(menuContainer);
        this._newMenuElement(_('Arrange Icons'), 'arrange-icons', section);
        section.append_submenu(_('Arrange By...'), this._addSortingSubMenu());

        section = this._newSection(menuContainer);
        this._newMenuElement(_('Show Desktop in Files'), 'show-in-files', section);
        this._newMenuElement(_('Open in Terminal'), 'open-in-terminal-desktop', section);

        section = this._newSection(menuContainer);
        this._newMenuElement(_('Change Background…'), 'change-background', section);

        section = this._newSection(menuContainer);
        this._newMenuElement(_('Desktop Icons Settings'), 'show-settings', section);
        this._newMenuElement(_('Display Settings'), 'display-settings', section);

        return menuContainer;
    }
};
