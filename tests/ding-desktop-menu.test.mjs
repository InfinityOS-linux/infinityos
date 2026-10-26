import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/ding@rastersoft.com/app/desktopMenu.js', import.meta.url), 'utf8')
  .replace(/^import .*;\n/gm, '')
  .replace('export var DesktopMenu = class', 'var DesktopMenu = class');
const managerSource = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/ding@rastersoft.com/app/desktopManager.js', import.meta.url), 'utf8')
  .replace(/^import .*;\n/gm, '')
  .replace('export var DesktopManager = class', 'var DesktopManager = class');

test('desktop menu closes immediately and reopens cleanly', async () => {
  let now = 1_000_000;
  const popovers = [];
  const GLib = {
    get_monotonic_time: () => now,
    PRIORITY_DEFAULT: 0,
    SOURCE_REMOVE: false,
    timeout_add: () => { throw new Error('menu must not schedule animation timers'); },
    source_remove() {},
  };
  const Gtk = {
    Settings: { get_default: () => ({ gtk_enable_animations: true }) },
    PopoverMenuFlags: { NESTED: 1 },
    PopoverMenu: { new_from_model_full: () => {
      const classes = new Set();
      const handlers = {};
      const popover = {
        classes,
        visible: false,
        popdowns: 0,
        add_css_class: name => classes.add(name),
        remove_css_class: name => classes.delete(name),
        get_visible() { return this.visible; },
        connect(signal, handler) { handlers[signal] = handler; },
        popup() { this.visible = true; },
        popdown() {
          this.popdowns++;
          this.visible = false;
          handlers.closed?.();
        },
        set_pointing_to() {},
        set_menu_model() {},
      };
      popovers.push(popover);
      return popover;
    } },
  };
  const context = {
    GLib, Gtk,
    Gdk: { Rectangle: class {} },
    DBusUtils: {}, Gio: {}, GioUnix: {}, Prefs: {}, Enums: {},
    TemplatesScriptsManager: { TemplatesScriptsManager: class {
      entriesRevision = 0;
    }, TemplatesScriptsManagerFlags: { HIDE_EXTENSIONS: 1 } },
    DesktopIconsUtil: { getTemplatesDir: () => null, getDesktopDir: () => null },
    MenuHelper: { MenuHelper: class {
      constructor(desktopManager) { this._desktopManager = desktopManager; }
    } },
    imports: { gettext: { domain: () => ({ gettext: text => text }) } },
    console,
  };
  vm.runInNewContext(source, context);
  vm.runInNewContext(`DesktopMenu.prototype._addActions = function () {
    this._pasteAction = { enabled: false };
  };`, context);
  const Menu = vm.runInNewContext('DesktopMenu', context);
  const menu = new Menu({ updateClipboard: () => Promise.resolve(false) }, {}, {});
  menu._syncUndoRedo = () => ({ undo: false, redo: false });
  menu._createDesktopBackgroundMenu = () => ({});
  const grid = { put() {}, move() {} };

  menu.showDesktopMenu(20, 30, grid);
  const popover = popovers[0];
  assert.equal(popover.visible, true);
  assert.equal(popover.classes.has('menu-enter'), true);

  menu.hideDesktopMenu();
  assert.equal(popover.visible, false, 'closing must release the GTK popover before the next click');
  assert.equal(popover.popdowns, 1);
  assert.equal(menu._lastBgMenu, null);
  assert.equal(popover.classes.has('menu-enter'), false);

  now += 200_000;
  menu.showDesktopMenu(40, 50, grid);
  assert.equal(popovers.length, 1, 'reuse the menu for the same desktop grid');
  assert.equal(popover.visible, true);
  assert.equal(popover.classes.has('menu-enter'), true);
  popover.popdown();
  assert.equal(menu._lastBgMenu, null, 'GTK outside-click dismissal clears menu state');
  assert.equal(popover.classes.has('menu-enter'), false);
  await Promise.resolve();
});

test('clicking a desktop icon dismisses the background menu', () => {
  const context = {
    imports: { gettext: { domain: () => ({ gettext: text => text }) } },
  };
  vm.runInNewContext(managerSource, context);
  const Manager = vm.runInNewContext('DesktopManager', context);
  let closed = 0;
  let fileMenuShown = 0;
  const manager = {
    _desktopMenu: { hideDesktopMenu: () => closed++ },
    _fileItemMenu: { showMenu: () => fileMenuShown++ },
  };

  Manager.prototype.clickCaptured.call(manager);
  assert.equal(manager._clickCaptured, true);
  assert.equal(closed, 1);

  Manager.prototype.showFileMenu.call(manager, {}, 0, 0);
  assert.equal(fileMenuShown, 1);
  assert.equal(closed, 2);

  Manager.prototype.onDesktopWindowDeactivated.call(manager);
  assert.equal(closed, 3);
});

test('rubberband does not redraw when pointer stays within the same pixels', () => {
  const context = {
    imports: { gettext: { domain: () => ({ gettext: text => text }) } },
    Gdk: { Rectangle: class { constructor(values) { Object.assign(this, values); } } },
  };
  vm.runInNewContext(managerSource, context);
  const Manager = vm.runInNewContext('DesktopManager', context);
  let redraws = 0;
  let intersectionChecks = 0;
  const manager = {
    rubberBand: true,
    rubberBandInitX: 0,
    rubberBandInitY: 0,
    selectionRectangle: null,
    _desktops: [{ queue_draw: () => redraws++ }],
    _fileList: [{ checkIntersects: () => { intersectionChecks++; return false; } }],
  };

  Manager.prototype.onMotion.call(manager, 10.2, 11.2);
  Manager.prototype.onMotion.call(manager, 10.8, 11.9);
  assert.equal(redraws, 1);
  assert.equal(intersectionChecks, 1);
});
