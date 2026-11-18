import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import UserTray from '../wack-shell@rinzler69-wastaken.github.com/userTray.js';
import AppDashboard from '../wack-shell@rinzler69-wastaken.github.com/appDashboard.js';
import {TerminalPullHandle} from '../ghostty@infinityos.org/pull-handle.js';
import {HardwareMonitor} from '../ghostty@infinityos.org/hardware-monitor.js';
import {widgetChoices} from '../ghostty@infinityos.org/monitor-widgets.js';
import NowPlay from '../nowplay@LalaloyXyz/extension.js';
import Raccoon from '../raccoonlauncher@shimafallah.github.io/extension.js';
import Updater from '../infinity-updater@infinityos.org/extension.js';
import {opticalMetrics} from '../dash2dock-animated@infinityos.org/optical-icons.mjs';
import {DockBackground} from '../dash2dock-animated@infinityos.org/dockItems.js';
import {PanelBlur} from '../blur-my-shell@aunetx/components/panel.js';

function check(ok, message) { if (!ok) throw new Error(message); }

export default class Smoke extends Extension {
    enable() {
        this._objects = [];
        GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 3, () => {
            this.run().catch(error => { console.error(`INFINITY_SMOKE_FAIL ${error.message} ${error.stack}`); });
            return GLib.SOURCE_REMOVE;
        });
    }

    async run() {
        const root = this.dir.get_parent();
        const metadata = uuid => {
            const dir = root.get_child(uuid);
            const [, bytes] = dir.get_child('metadata.json').load_contents(null);
            return {...JSON.parse(new TextDecoder().decode(bytes)), dir, path: dir.get_path()};
        };
        const theme = St.ThemeContext.get_for_stage(global.stage).get_theme();
        for (const uuid of ['ghostty@infinityos.org', 'nowplay@LalaloyXyz', 'raccoonlauncher@shimafallah.github.io', 'infinity-updater@infinityos.org', 'wack-shell@rinzler69-wastaken.github.com']) {
            const file = root.get_child(uuid).get_child('stylesheet.css');
            if (file.query_exists(null)) theme.load_stylesheet(file);
        }
        const iconTheme = St.IconTheme.new();
        let iconLoaded = false;
        opticalMetrics(iconTheme, null, 'folder', () => { iconLoaded = true; });
        const terminal = metadata('ghostty@infinityos.org');
        const source = Gio.SettingsSchemaSource.new_from_directory(`${terminal.path}/schemas`, Gio.SettingsSchemaSource.get_default(), false);
        const settings = new Gio.Settings({settings_schema: source.lookup('org.infinityos.GhosTTY', true)});
        settings.set_strv('monitor-metrics', ['memory:used', ...widgetChoices.map(choice => choice.id)]);
        const monitor = new HardwareMonitor({path: terminal.path, getSettings: () => settings, openPreferences() {}}, () => {});
        this._objects.push({disable: () => monitor.destroy()});
        monitor.sync({x: 0, y: 150, width: 1280}, true);
        const wait = () => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 750, () => { resolve(); return GLib.SOURCE_REMOVE; }));
        const dockOutline = new DockBackground({width: 420, height: 72});
        dockOutline._dock = {extension: {adaptive_background: true, panel_mode: false,
            computed_border_radius: 40, border_thickness: 1, _getPreferredColorScheme: () => 'dark'}};
        Main.layoutManager.addTopChrome(dockOutline);
        this._objects.push({disable: () => {
            Main.layoutManager.removeChrome(dockOutline); dockOutline.destroy();
        }});
        dockOutline.queue_repaint();
        const dashboard = new AppDashboard();
        this._objects.push({disable: () => dashboard.destroy()});
        const preview = new St.Widget({width: 240, height: 150,
            style: 'background-color: #604080;'});
        Main.layoutManager.addTopChrome(preview);
        this._objects.push({disable: () => {
            Main.layoutManager.removeChrome(preview); preview.destroy();
        }});
        const dashboardBox = dashboard._box;
        dashboard._box = {_thumbnails: [preview]};
        try { dashboard._syncPreviews(); }
        finally { dashboard._box = dashboardBox; }
        check(dashboard._previews.has(preview), 'rounded preview shader failed to attach');
        await wait();
        check(iconLoaded, 'native dock icon measurement failed');
        check(monitor._cells.length === 8, 'sensor/widget construction');
        for (const cell of monitor._cells.filter(cell => cell.actor.visible))
            check(cell.label.height > 0, `caption clipped: ${cell.id}`);
        const visibleCells = monitor._cells.filter(cell => cell.actor.visible);
        const [left] = visibleCells[0].actor.get_transformed_position();
        const last = visibleCells.at(-1).actor;
        const [lastX] = last.get_transformed_position();
        const [lastWidth] = last.get_transformed_size();
        check(Math.abs((left + lastX + lastWidth) / 2 - 640) < 2, 'monitor row is not centered');
        monitor._openMenu(-1); check(monitor.menuOpen, 'monitor menu failed'); monitor._menu.close();
        monitor._widgets.stopwatch.toggle(); monitor._widgets.toggleTimer('widget:timer');
        const iface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        Main.overview.hide();
        await wait();
        const terminalWindow = {minimized: true};
        const pull = new TerminalPullHandle({_indicator: new St.Widget(), _findWindow: () => terminalWindow});
        this._objects.push({disable: () => pull.destroy()});
        await wait();
        const primary = Main.layoutManager.primaryMonitor;
        check(Math.abs(pull.actor.x + pull.actor.width / 2 - primary.x - primary.width / 2) < 1, 'pull handle is not centered');
        check(pull.actor.visible, 'closed terminal has no pull handle');
        // Exercise the real BMS geometry and native GPU paint path. Mock-only
        // tests cannot detect a clipped-off handle or an invalid paint context.
        const {default: NativeBlur} = await import('gi://Blur');
        const blurGroup = new Meta.BackgroundGroup({width: 0, height: 0});
        const blurBackground = new St.Widget();
        blurBackground.add_effect(new NativeBlur.BlurEffect({
            mode: NativeBlur.BlurMode.BACKGROUND, radius: 56, brightness: .64,
        }));
        blurGroup.add_child(blurBackground);
        Main.panel.get_parent().insert_child_at_index(blurGroup, 0);
        const blurController = new PanelBlur(null, {DEBUG: false}, null);
        // Exercise the real matching-backdrop factory with native GPU effects.
        blurController.settings.panel = {STATIC_BLUR: false, PIPELINE: 'pipeline_default',
            SIGMA: 28, BRIGHTNESS: .64, CORNER_RADIUS: 0,
            settings: {connect: () => 0, disconnect() {}}};
        blurController.effects_manager = {
            new_native_dynamic_gaussian_blur_effect: params => new NativeBlur.BlurEffect({
                mode: NativeBlur.BlurMode.BACKGROUND,
                radius: params.unscaled_radius, brightness: params.brightness,
            }),
            remove: effect => effect.get_actor()?.remove_effect(effect),
        };
        const blurActors = {widgets: {panel: Main.panel, geometry_actor: Main.panel,
            panel_box: Main.panel.get_parent(), background: blurBackground,
            background_group: blurGroup}, static_blur: false, is_dtp_panel: false};
        blurController.actors_list.push(blurActors);
        blurController.enabled = true;
        const previousBlur = global.blur_my_shell;
        global.blur_my_shell = {_panel_blur: blurController};
        this._objects.push({disable: () => {
            global.blur_my_shell = previousBlur;
            blurController.enabled = false;
            blurGroup.destroy();
        }});
        blurController.update_size(blurActors);
        await wait();
        check(blurBackground.height > Main.panel.height, 'panel blur stops above pull handle');
        check(blurActors.terminalClip, 'native panel blur has no handle contour');
        terminalWindow.minimized = false; pull.sync();
        await wait();
        check(pull.actor.visible && pull.actor.scale_y === .5, 'open terminal did not compact handle');
        terminalWindow.minimized = true; pull.sync();

        iface.set_string('color-scheme', 'prefer-light'); await wait();
        check(monitor.actor.has_style_class_name('light'), 'light mode failed');
        check(pull.light, 'pull handle did not switch to light mode');
        iface.set_string('color-scheme', 'prefer-dark'); await wait();
        check(!monitor.actor.has_style_class_name('light'), 'dark mode failed');
        check(!pull.light, 'pull handle did not switch to dark mode');
        const target = monitor._cells[0].actor._delegate;
        target.acceptDrop({monitor, id: 'widget:clock'}, null, 0);
        await wait(); check(settings.get_strv('monitor-metrics')[0] === 'widget:clock', 'drag reorder failed');
        monitor.hide(); check(!monitor._widgetTimer && !monitor._timer, 'hidden strip still polling');

        const raccoon = new Raccoon(metadata('raccoonlauncher@shimafallah.github.io'));
        this._objects.push(raccoon); raccoon.enable();
        raccoon._overlay.open(); check(raccoon._overlay._isOpen, 'Raccoon did not open');
        raccoon._overlay._entry.set_text('2+3'); await wait();
        check(raccoon._overlay._results.some(result => result.name === '5'), 'Raccoon calculator failed');
        raccoon._overlay.close(); check(!raccoon._overlay._grab, 'Raccoon kept modal grab');

        const {default: Blur} = await import('gi://Blur');
        check(Blur.BlurEffect.list_properties().some(property => property.name === 'corner-radius'), 'native rounded blur unavailable');
        const nowplay = new NowPlay(metadata('nowplay@LalaloyXyz'));
        this._objects.push(nowplay); nowplay.enable();
        check(!nowplay._ui._createStatusPill.toString().includes('animateUp'), 'loaded obsolete NowPlay equalizer');
        console.log('INFINITY_NOWPLAY_TIMER_SOURCE_CONFIRMED');
        const player = {busName: 'org.mpris.MediaPlayer2.smoke', title: 'InfinityOS test', artist: 'CI',
            status: 'Playing', position: 30, trackLen: 180, canSeek: true, trackId: '/test', artUrl: '', appIconName: 'audio-x-generic'};
        nowplay._ui.showPopup(player, [player]); await wait();
        check(nowplay._ui.popupVisible, 'NowPlay did not open');
        nowplay._ui.destroyPopup();
        const trayApp = new PanelMenu.Button(0, 'Tray smoke');
        const trayIcon = new St.Icon({icon_name: 'edit-paste-symbolic', style_class: 'system-status-icon',
            icon_size: 48, style: 'icon-size: 48px;'});
        trayApp.add_child(trayIcon);
        trayApp.menu.addAction('Test action', () => {});
        Main.panel.addToStatusArea('infinity-tray-smoke', trayApp);
        const extraTrayApps = [1, 2].map(index => {
            const app = new PanelMenu.Button(0, `Tray spacing ${index}`);
            app.add_child(new St.Icon({icon_name: 'view-grid-symbolic', style_class: 'system-status-icon'}));
            Main.panel.addToStatusArea(`infinity-tray-spacing-${index}`, app);
            return app;
        });
        let tray = new UserTray();
        this._objects.push({disable: () => { tray?.destroy(); trayApp.destroy(); extraTrayApps.forEach(app => app.destroy()); }});
        await wait();
        const entry = tray._entries.get(trayApp);
        check(entry && entry.wrapper.get_parent() === tray._icons, 'tray app was not moved');
        const quick = Main.panel.statusArea.quickSettings;
        // Headless CI has no audio device, so the output slider is normally
        // invisible and has no meaningful allocation. Show it for layout checks.
        const output = quick._volumeOutput.quickSettingsItems[0];
        const outputVisible = output.visible;
        output.show();
        quick.menu.open(); await wait();
        const [iconWidth, iconHeight] = trayIcon.get_transformed_size();
        // StIcon is allocated the whole click target but paints its natural icon
        // centered inside it. Measure that natural size, not the target bounds.
        const [, naturalWidth] = trayIcon.get_preferred_width(-1);
        const [, naturalHeight] = trayIcon.get_preferred_height(-1);
        check(naturalWidth <= 20 && naturalHeight <= 20,
            `tray glyph is oversized: ${naturalWidth}x${naturalHeight}`);
        const [, iconY] = trayIcon.get_transformed_position();
        const [, cellY] = entry.wrapper.get_transformed_position();
        const [cellWidth, cellHeight] = entry.wrapper.get_transformed_size();
        check(Math.abs(cellWidth - cellHeight) <= 1, 'tray cell is not square');
        check(Math.abs(iconY + iconHeight / 2 - cellY - cellHeight / 2) <= 1,
            'tray icon is not vertically centered');
        check(tray._icons.get_children().length === tray._entries.size,
            'tray contains an extra overflow button');
        const cells = [trayApp, ...extraTrayApps].map(app => tray._entries.get(app).wrapper);
        const centers = cells.map(cell => cell.get_transformed_position()[0] + cell.get_transformed_size()[0] / 2);
        check(Math.abs((centers[1] - centers[0]) - (centers[2] - centers[1])) <= 1,
            `tray spacing is unequal: ${centers}`);
        check(centers[1] - centers[0] >= cellWidth,
            'tray cells overlap');
        const [groupX] = tray._icons.get_transformed_position();
        const [groupWidth] = tray._icons.get_transformed_size();
        const [sectionX] = tray._section.get_transformed_position();
        const [sectionWidth] = tray._section.get_transformed_size();
        check(Math.abs(groupX + groupWidth / 2 - sectionX - sectionWidth / 2) <= 1,
            'compact tray group is not centered in the row');
        const quickChildren = quick.menu._grid.get_children();
        check(quickChildren.indexOf(tray._section) > quickChildren.indexOf(output),
            'tray grid order is above system volume');
        check(tray._section.get_transformed_position()[1] >
            output.get_transformed_position()[1],
        `tray allocation is above volume: ${tray._section.get_transformed_position()} / ${output.get_transformed_position()}`);
        trayApp.menu.open(); await wait();
        check(quick.menu.isOpen && trayApp.menu.isOpen, 'app menu closed Quick Settings');
        tray._sync(); await wait();
        check(trayApp.menu.isOpen, 'unchanged sync closed app menu');
        trayApp.menu.close();
        tray._openMenu(trayApp, entry); await wait();
        check(tray._context.isOpen, 'tray context menu failed'); tray._context.close();
        tray._setLocation(entry, 'panel');
        check(entry.wrapper.get_parent() === Main.panel._rightBox, 'pin failed');
        tray._setLocation(entry, 'hidden'); check(!entry.wrapper.visible, 'hide failed');
        tray._openMenu(tray._icons); await wait();
        check(tray._context.numMenuItems > 0, 'hidden icon cannot be restored');
        tray._context.close();
        tray._setLocation(entry, 'menu');
        check(entry.wrapper.visible, 'show failed');
        quick.menu.close();
        output.visible = outputVisible;
        tray.destroy(); tray = null;
        check(trayApp.container.get_parent() === Main.panel._rightBox, 'tray disable lost app');
        const updater = new Updater(metadata('infinity-updater@infinityos.org'));
        this._objects.push(updater); updater.enable();
        check(Main.panel.statusArea['infinity-updater'], 'updater indicator failed');
        const updaterTray = new UserTray();
        this._objects.push({disable: () => updaterTray.destroy()});
        updaterTray._preferences['infinity-updater'] = 'hidden';
        updaterTray._sync();
        check(updater._indicator.container.get_parent() === Main.panel._rightBox,
            'updater moved away from top bar');
        check(!updater._indicator.visible, 'updater is visible without updates');
        GLib.file_set_contents(updater._stateFile, JSON.stringify({
            checked_at: new Date().toISOString(), updates: [{kind: 'Flatpak user', name: 'smoke'}],
        }));
        updater._refresh();
        check(updater._indicator.visible && updater._badge.visible && updater._badge.text === '1',
            'pending updates do not show the indicator and badge');
        updaterTray._sync();
        check(updater._indicator.visible, 'tray preferences hid pending updates');
        GLib.file_set_contents(updater._stateFile, JSON.stringify({updates: []}));
        updater._refresh();
        check(!updater._indicator.visible && !updater._badge.visible,
            'empty update list left the indicator visible');
        const client = Gio.Subprocess.new(['python3', '-c', `
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
app = Gtk.Application(application_id='org.infinityos.Updater')
def activate(app):
    from gi.repository import Gdk
    css = Gtk.CssProvider()
    css.load_from_data(b'window { background: transparent; }')
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, 800)
    window = Gtk.ApplicationWindow(application=app, title='InfinityUpdater smoke')
    window.set_decorated(False)
    window.set_default_size(160, 100)
    window.set_child(Gtk.Label(label='Updater'))
    window.present()
app.connect('activate', activate)
app.run(None)
`], Gio.SubprocessFlags.NONE);
        this._objects.push({disable: () => client.force_exit()});
        await wait(); await wait(); await wait();
        const drawer = global.get_window_actors().find(actor => updater._isUpdater(actor.meta_window));
        check(drawer, 'updater client did not map');
        const frame = drawer.meta_window.get_frame_rect();
        const area = Main.layoutManager.getWorkAreaForMonitor(drawer.meta_window.get_monitor());
        check(frame.width === Math.min(460, area.width) && frame.height === area.height, 'updater remained at initial size');
        check(drawer.opacity === 255 && Math.abs(drawer.translation_x) < 1, 'updater did not finish its spring slide');
        const drawerBackdrop = updater._drawerBackdrop._entries.get(drawer.meta_window);
        check(drawerBackdrop?.backdrop, 'updater has no panel-matched native blur');
        check(drawerBackdrop.container.clip_to_allocation, 'updater blur includes the window shadow');
        check(drawerBackdrop.backdrop.background.width === frame.width &&
            drawerBackdrop.backdrop.background.height === frame.height, 'updater blur does not fill the drawer');
        check(drawer.get_children().indexOf(drawerBackdrop.container) === 0, 'updater blur covers GTK contents');
        this.disable();
        console.log('INFINITY_SMOKE_PASS');
    }

    disable() {
        for (const object of this._objects.reverse()) object.disable();
        this._objects = [];
    }
}



