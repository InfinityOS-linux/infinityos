import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import UserTray from '../wack-shell@rinzler69-wastaken.github.com/userTray.js';
import AppDashboard from '../wack-shell@rinzler69-wastaken.github.com/appDashboard.js';
import TerminalController from '../ghostty@infinityos.org/extension.js';
import Shell from 'gi://Shell';
import {TerminalPullHandle} from '../ghostty@infinityos.org/pull-handle.js';
import {PanelBackdrop} from '../ghostty@infinityos.org/panel-backdrop.js';
import {HardwareMonitor} from '../ghostty@infinityos.org/hardware-monitor.js';
import {widgetChoices} from '../ghostty@infinityos.org/monitor-widgets.js';
import NowPlay from '../nowplay@LalaloyXyz/extension.js';
import Raccoon from '../raccoonlauncher@shimafallah.github.io/extension.js';
import Updater from '../infinity-updater@infinityos.org/extension.js';
import {excludeFromDock} from '../dash2dock-animated@infinityos.org/dock-apps.mjs';
import {opticalMetrics} from '../dash2dock-animated@infinityos.org/optical-icons.mjs';
import {createDockBlurProxy, Dock} from '../dash2dock-animated@infinityos.org/dock.js';
import {Integrations} from '../dash2dock-animated@infinityos.org/integrations.js';
import {DashBlur} from '../blur-my-shell@aunetx/components/dash_to_dock.js';
import {Connections} from '../blur-my-shell@aunetx/conveniences/connections.js';
import {DockBackground} from '../dash2dock-animated@infinityos.org/dockItems.js';
import {PanelBlur} from '../blur-my-shell@aunetx/components/panel.js';
import {MenuManager} from '../globalmenu@ShiroOSL.github.io/menuManager.js';
import {PopupBlur} from '../blur-my-shell@aunetx/components/popup.js';
import {Settings} from '../blur-my-shell@aunetx/conveniences/settings.js';
import {KEYS} from '../blur-my-shell@aunetx/conveniences/keys.js';
import {EffectsManager} from '../blur-my-shell@aunetx/conveniences/effects_manager.js';
import BlurMyShell from '../blur-my-shell@aunetx/extension.js';
import PanelIndicators from '../wack-shell@rinzler69-wastaken.github.com/panelIndicators.js';
import {WackWorkspaceButton} from '../wack-shell@rinzler69-wastaken.github.com/panelComponents.js';
import RamdriveRestart from '../wack-shell@rinzler69-wastaken.github.com/ramdriveRestart.js';

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
        const terminalController = new TerminalController(terminal);
        const appInfo = Gio.DesktopAppInfo.new_from_filename(GLib.getenv('INFINITY_SMOKE_TERMINAL_DESKTOP'));
        check(appInfo, 'terminal desktop entry is unavailable');
        const terminalApp = new Shell.App({app_info: appInfo});
        let appRequests = 0;
        terminalController._launchFromApp = () => { appRequests++; };
        const originalAppActivate = Shell.App.prototype.activate;
        terminalController._installAppActivation();
        terminalApp.activate();
        terminalApp.activate_full(-1, global.get_current_time());
        terminalApp.open_new_window(-1);
        check(appRequests === 3, 'native Shell app activation bypassed the terminal controller');
        terminalController._removeAppActivation();
        check(Shell.App.prototype.activate === originalAppActivate, 'terminal app activation hook was not restored');

        const source = Gio.SettingsSchemaSource.new_from_directory(`${terminal.path}/schemas`, Gio.SettingsSchemaSource.get_default(), false);
        const settings = new Gio.Settings({settings_schema: source.lookup('org.infinityos.GhosTTY', true)});
        settings.set_strv('monitor-metrics', ['memory:used', ...widgetChoices.map(choice => choice.id)]);
        const monitor = new HardwareMonitor({path: terminal.path, getSettings: () => settings, openPreferences() {}}, () => {});
        this._objects.push({disable: () => monitor.destroy()});
        monitor.sync({x: 0, y: 150, width: 1280}, true);
        const wait = () => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 750, () => { resolve(); return GLib.SOURCE_REMOVE; }));
        Main.overview.hide();
        Main.welcomeDialog?.close();
        await wait();
        const modalActors = () => Main.modalActorFocusStack.map(({actor}) => actor.toString()).join(', ');
        check(Main.modalCount === 0, `startup retained modal input: ${modalActors()}`);
        const screenshot = new Shell.Screenshot();
        const edgeContrast = async (edgeX, sampleY) => {
            // Capture the full stage so the blur kernel can sample surrounding
            // pixels. A one-pixel pick_color capture clips those neighbours.
            const stream = Gio.MemoryOutputStream.new_resizable();
            await screenshot.screenshot(false, stream);
            stream.close(null);
            const loader = GdkPixbuf.PixbufLoader.new();
            loader.write(stream.steal_as_bytes().get_data()); loader.close();
            const image = loader.get_pixbuf();
            const pixels = image.get_pixels();
            const at = x => pixels[sampleY * image.rowstride + x * image.n_channels];
            const left = at(edgeX - 6), right = at(edgeX + 6);
            return {left, right, contrast: right - left};
        };
        const popupSettings = new Settings(KEYS, Gio.Settings.new('org.gnome.shell.extensions.blur-my-shell'));
        const effectSignals = new Connections();
        const popupEffects = new EffectsManager(effectSignals);
        const popups = new PopupBlur(new Connections(), popupSettings, popupEffects);
        const globalMenuExtension = new Extension(metadata('globalmenu@ShiroOSL.github.io'));
        const globalMenus = new MenuManager(globalMenuExtension.uuid, globalMenuExtension.getSettings());
        try {
            popups.enable();
            globalMenus.updateMenuForWindow(null);
            check(globalMenus._buttons.length === 7, 'expected all seven desktop panel menus');
            for (const [variant, preference, tint] of [['Dark', 'prefer-dark', 12], ['Light', 'default', 226]]) {
                const css = Gio.File.new_for_path(`${GLib.getenv('INFINITY_SMOKE_THEMES')}/Orchis-Purple-${variant}-Compact/gnome-shell/gnome-shell.css`);
                theme.load_stylesheet(css);
                try {
                    popups.interface_settings.set_string('gtk-theme', `Orchis-Purple-${variant}-Compact`);
                    popups.interface_settings.set_string('color-scheme', preference);
                    const clockBox = new St.BoxLayout({style_class: 'unlock-dialog-clock'});
                    const time = new St.Label({style_class: 'unlock-dialog-clock-time', text: '10:56 AM'});
                    const date = new St.Label({style_class: 'unlock-dialog-clock-date', text: 'Tuesday November 24'});
                    clockBox.add_child(time);
                    clockBox.add_child(date);
                    Main.uiGroup.add_child(clockBox);
                    try {
                        const face = time.get_theme_node().get_font();
                        check(face.get_family().includes('IBM Plex Sans') && face.get_weight() === 300,
                            `${variant} native clock font: ${face.to_string()}`);
                        check(date.get_theme_node().get_font().get_weight() === 400, 'clock rule changed date weight');
                    } finally { clockBox.destroy(); }
                    if (variant === 'Light') {
                        const shield = new St.Widget({style_class: 'infinity-light-unlock'});
                        const dialog = new St.BoxLayout({style_class: 'unlock-dialog'});
                        const name = new St.Label({style_class: 'user-widget-label', text: 'Test'});
                        const entry = new St.PasswordEntry({style_class: 'login-dialog-prompt-entry', hint_text: 'Password'});
                        dialog.add_child(name);
                        dialog.add_child(entry);
                        shield.add_child(dialog);
                        Main.uiGroup.add_child(shield);
                        try {
                            entry.add_style_pseudo_class('focus');
                            check(name.get_theme_node().get_foreground_color().red === 41, 'unreadable unlock username');
                            check(entry.get_theme_node().get_foreground_color().red === 41, 'unreadable password');
                            check(entry.get_theme_node().get_background_color().red === 250, 'missing light entry surface');
                        } finally { shield.destroy(); }
                    }
                    const checkOpenMenu = async menu => {
                        await wait();
                        const color = menu.box.get_theme_node().get_background_color();
                        const surface = popups.surfaces.get(menu.box);
                        check(color.red === tint && color.alpha < 240, `${variant} menu material: ${color.to_string()}`);
                        check(surface?.blur_actor?.mapped && surface.pipeline.effect.get_actor() === surface.blur_actor,
                            'menu backdrop is missing a mapped native blur effect');
                        if (variant === 'Light') {
                            check(Math.abs(surface.pipeline.effect.brightness - 1) < .001,
                                'light menus still darken their backdrop');
                            if (menu === globalMenus._buttons[2].menu) {
                                // Sample the empty right margin of the open Edit menu.
                                const [left, top] = menu.box.get_transformed_position();
                                const [width, height] = menu.box.get_transformed_size();
                                const edge = Math.round(left + width - 24);
                                const y = Math.round(top + height / 2);
                                const field = new St.Widget({width: global.stage.width, height: global.stage.height,
                                    style: 'background-color: black;'});
                                field.add_child(new St.Widget({x: edge, width: global.stage.width - edge,
                                    height: global.stage.height, style: 'background-color: white;'}));
                                surface.parent.insert_child_below(field, surface.actor);
                                try {
                                    await wait();
                                    const blurred = await edgeContrast(edge, y);
                                    surface.pipeline.effect.enabled = false;
                                    await wait();
                                    const sharp = await edgeContrast(edge, y);
                                    check(sharp.contrast > 20 && blurred.contrast + 6 < sharp.contrast,
                                        `light menu obscures the wallpaper or lacks blur: ${JSON.stringify({blurred, sharp})}`);
                                } finally {
                                    surface.pipeline.effect.enabled = true;
                                    field.destroy();
                                }
                            }
                        }
                        menu.close();
                        await wait();
                    };
                    for (const indicator of [Main.panel.statusArea.dateMenu, Main.panel.statusArea.quickSettings, ...globalMenus._buttons]) {
                        indicator.menu.open();
                        await checkOpenMenu(indicator.menu);
                    }
                    monitor._openMenu(-1);
                    await checkOpenMenu(monitor._menu);
                } finally {
                    theme.unload_stylesheet(css);
                }
            }
        } finally {
            globalMenus.destroy();
            popups.disable();
            popups.interface_settings.reset('gtk-theme');
            popups.interface_settings.reset('color-scheme');
            popupEffects.destroy_all();
            effectSignals.disconnect_all();
            popupSettings.disconnect_all_settings();
        }
        const logo = {_settings: {get_int: () => 2}};
        const clickLogo = () => WackWorkspaceButton.prototype.vfunc_event.call(
            logo, {type: () => Clutter.EventType.BUTTON_RELEASE});
        const overview = Main.overview;
        try {
            clickLogo();
            await wait();
            check(overview.visible && overview.dash.showAppsButton.checked, 'Infinity logo did not open the app grid');
            clickLogo();
            await wait();
            check(!overview.visible, 'Infinity logo did not close the app grid');
            overview.show();
            await wait();
            check(overview.visible && !overview.dash.showAppsButton.checked, 'workspace preview did not open');
            clickLogo();
            await wait();
            check(overview.visible && overview.dash.showAppsButton.checked, 'Infinity logo did not switch to the app grid');
        } finally {
            overview.hide();
            await wait();
        }
        const endDialog = Main.endSessionDialog;
        const savedEndMethods = {confirm: endDialog._confirm, state: endDialog._getUpdateState, sessions: endDialog._loadSessions};
        let restartSignals = 0, occupiedRamdrive = true, failSave = true;
        endDialog._confirm = async signal => { check(signal === 'ConfirmedReboot', 'wrong restart signal'); restartSignals++; };
        endDialog._getUpdateState = async () => 'none';
        endDialog._loadSessions = async () => {};
        const restartPrompt = new RamdriveRestart(endDialog, () => occupiedRamdrive, async action => {
            check(action === 'save', 'wrong RAMDrive action');
            if (failSave) throw new Error('fixture save failure');
            occupiedRamdrive = false;
        });
        try {
            await endDialog.OpenAsync([2, 0, 60, []], {
                return_value() {}, return_error_literal(_domain, _code, message) {throw new Error(message);},
            });
            await wait();
            check(restartPrompt.buttons.length === 2, 'RAMDrive restart choices missing');
            check(restartPrompt.buttons[0].label === 'Remove & Restart' && restartPrompt.buttons[1].label === 'Save files', 'RAMDrive button labels differ');
            check(!endDialog._timerId, 'RAMDrive restart countdown is active');
            const [promptX, promptY] = endDialog.dialogLayout._dialog.get_transformed_position();
            check(promptX > 640 && promptY < 200, `RAMDrive prompt is not at upper right: ${promptX},${promptY}`);
            await endDialog._confirm('ConfirmedReboot');
            check(restartSignals === 0, 'automatic confirmation bypassed RAMDrive choices');
            await restartPrompt.prepare('save');
            check(restartSignals === 0 && !restartPrompt.busy, 'failed save restarted or locked the dialog');
            failSave = false;
            await restartPrompt.prepare('save');
            check(restartSignals === 1, 'successful save did not resume GNOME confirmation');
        } finally {
            restartPrompt.destroy();
            // The confirmation stub does not perform GNOME's normal dialog
            // fade-out. Always release its input grab before later client tests.
            endDialog.close();
            endDialog._confirm = savedEndMethods.confirm;
            endDialog._getUpdateState = savedEndMethods.state;
            endDialog._loadSessions = savedEndMethods.sessions;
        }
        await wait();
        check(Main.modalCount === 0, `RAMDrive fixture retained modal input: ${modalActors()}`);
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
        monitor._openMenu(-1); check(monitor.menuOpen, 'monitor menu failed');
        const shield = Main.layoutManager.screenShieldGroup;
        const chrome = Main.uiGroup.get_children();
        check(chrome.indexOf(monitor.actor) < chrome.indexOf(shield), 'widget strip is stacked above the screen shield');
        check(chrome.indexOf(monitor._menu.actor) < chrome.indexOf(shield), 'widget menu is stacked above the screen shield');
        const windowActor = new St.Widget({width: 1, height: 1});
        Main.uiGroup.add_child(windowActor);
        const rect = {x: 0, y: 150, width: 1280, height: 500};
        const tracked = {minimized: false, get_compositor_private: () => windowActor,
            showing_on_its_workspace: () => true, get_frame_rect: () => rect};
        terminalController._window = tracked;
        terminalController._resizeHandle = new St.Widget();
        terminalController._hardware = monitor;
        try {
            shield.show();
            terminalController._syncResizeHandle();
            check(!monitor.actor.visible && !monitor._menu.actor.visible, 'terminal widgets visible on the screen shield');
            shield.hide();
            terminalController._syncResizeHandle();
            check(monitor.actor.visible, 'widgets did not return to the open terminal');
            tracked.minimized = true;
            terminalController._syncResizeHandle();
            check(windowActor.mapped && !monitor.actor.visible, 'mapped but minimized terminal still shows widgets');
        } finally {
            shield.hide();
            terminalController._window = null;
            terminalController._hardware = null;
            terminalController._resizeHandle.destroy();
            terminalController._resizeHandle = null;
            windowActor.destroy();
            monitor.sync(rect, true);
        }
        monitor._widgets.stopwatch.toggle(); monitor._widgets.toggleTimer('widget:timer');
        const iface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        Main.overview.hide();
        await wait();
        const terminalWindow = {minimized: true};
        const pull = new TerminalPullHandle({_findWindow: () => terminalWindow});
        this._objects.push({disable: () => pull.destroy()});
        await wait();
        const primary = Main.layoutManager.primaryMonitor;
        check(Math.abs(pull.actor.x + pull.actor.width / 2 - primary.x - primary.width / 2) < 1, 'pull handle is not centered');
        check(pull.actor.visible, 'closed terminal has no pull handle');
        check(pull.actor.get_cursor_type() === Clutter.CursorType.GRAB, 'handle has no open glove cursor');
        pull.showGrabCursor();
        check(pull.cursorSurface.get_cursor_type() === Clutter.CursorType.GRABBING,
            'drag does not keep its closed glove over Wayland windows');
        pull.clearGrabCursor();
        check(!pull.cursorSurface && pull.actor.get_cursor_type() === Clutter.CursorType.GRAB,
            'drag cursor surface survives release');
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
                corner_radius: params.unscaled_corner_radius ?? 0,
            }),
            remove: effect => effect.get_actor()?.remove_effect(effect),
        };
        const blurActors = {widgets: {panel: Main.panel, geometry_actor: Main.panel,
            panel_box: Main.panel.get_parent(), background: blurBackground,
            background_group: blurGroup}, static_blur: false, is_dtp_panel: false};
        blurController.actors_list.push(blurActors);
        blurController.enabled = true;
        const previousBlur = global.blur_my_shell;
        const redrawOwner = {_panel_blur: blurController, _settings: {HACKS_LEVEL: 1},
            _update_clipped_redraws: BlurMyShell.prototype._update_clipped_redraws,
            _disable_clipped_redraws() {
                this.fullRedraw = true;
                BlurMyShell.prototype._disable_clipped_redraws.call(this);
            },
            _reenable_clipped_redraws() {
                this.fullRedraw = false;
                BlurMyShell.prototype._reenable_clipped_redraws.call(this);
            }};
        global.blur_my_shell = redrawOwner;
        this._objects.push({disable: () => {
            global.blur_my_shell = previousBlur;
            blurController.enabled = false;
            blurGroup.destroy();
        }});
        blurController.update_size(blurActors);
        await wait();
        check(blurBackground.height > Main.panel.height, 'panel blur stops above pull handle');
        // Use the production discovery proxy and native BMS dock pipeline.
        const dockHolder = new St.Widget({width: 1280, height: 131, x: 0, y: 660,
            clip_to_allocation: true,
            offscreen_redirect: Clutter.OffscreenRedirect.ALWAYS});
        dockHolder._background = new DockBackground({x: 440, y: 57, width: 400, height: 60,
            style: 'background: rgba(18,18,23,.26); border-radius: 28px;'});
        dockHolder.add_child(dockHolder._background);
        dockHolder.extension = {computed_border_radius: 28, adaptive_background: false, panel_mode: false,
            border_thickness: 1, _getPreferredColorScheme: () => 'dark'};
        dockHolder._background._dock = dockHolder;
        dockHolder._slider = {get_child: () => dockHolder};
        const proxy = createDockBlurProxy(dockHolder);
        check(dockHolder.offscreen_redirect === 0,
            'dock parent still redirects its background blur into an isolated surface');
        Main.layoutManager.addTopChrome(dockHolder);
        redrawOwner._effects_manager = blurController.effects_manager;
        const dockConnections = new Connections();
        const dockSettings = {DEBUG: false, HACKS_LEVEL: 0,
            dash_to_dock: {STATIC_BLUR: false, SIGMA: 28, BRIGHTNESS: .9,
                CORNER_RADIUS: 28, OVERRIDE_BACKGROUND: false,
                settings: {connect: () => 0, disconnect() {}}}};
        const dockBlur = new DashBlur(dockConnections, dockSettings);
        this._objects.push({disable: () => {
            dockBlur.disable();
            Main.layoutManager.removeChrome(dockHolder); dockHolder.destroy();
        }});
        await wait();
        check(proxy.has_allocation() && proxy.width === dockHolder.width && proxy.height === dockHolder.height,
            'dock blur discovery proxy is unallocated');
        dockBlur.try_blur(dockHolder);
        await wait();
        check(dockBlur.dashes.length === 1, 'native dock blur did not attach');
        const dockInfo = dockBlur.dashes[0];
        check(dockInfo.background.width === 400 && dockInfo.background.height === 60,
            'native dock blur does not fill the visible pill');
        check(dockInfo.background.get_effects().length > 0, 'dock blur has no GPU effect');
        check(dockHolder.get_children().indexOf(dockInfo.background_group) <
            dockHolder.get_children().indexOf(dockHolder._background), 'dock blur covers its tint or icons');
        dockHolder._background.set_size(360, 56);
        await wait();
        check(dockInfo.background.width === 360 && dockInfo.background.height === 56,
            'dock blur did not follow pill resizing');
        dockHolder.hide();
        check(!dockInfo.background.is_mapped(), 'hidden dock left its blur visible');
        dockHolder.show();

        const dockTint = new St.Widget({name: 'wackPanelBackdropOverlay',
            style: 'background-color: rgba(80,60,110,.2);', reactive: false});
        Main.panel.add_child(dockTint);
        this._objects.push({disable: () => dockTint.destroy()});
        dockHolder.extension.adaptive_background = true;
        dockHolder._background.set_style('background: transparent;');
        await wait(); await wait();
        check(dockInfo.background_group._infinityPanelBackdrop, 'adaptive dock does not use the updater panel factory');
        const dockIntegration = new Integrations();
        const dockAnimator = {dock: dockHolder};
        dockHolder.animator = dockAnimator;
        dockHolder.extension.integrations = dockIntegration;
        dockInfo.background_group.hide();
        dockIntegration.bms_update_size(dockAnimator);
        Dock.prototype._updateTransparenies.call(dockHolder);
        await wait();
        check(dockInfo.background_group.visible && dockInfo.background.is_mapped(),
            'dock animator hides the working panel-matched blur');
        check(Math.abs(dockInfo.background.get_effects()[0].brightness - .64) < .001,
            'dock still uses its lighter independent blur brightness');
        check(dockInfo.background.get_effects()[0].corner_radius === 28, 'shared dock blur lost rounded corners');
        check(dockHolder._background._surfaceLayers?.some(color => color[3] > 0),
            'native dock draws only its outline without a tint surface');
        check(!redrawOwner.fullRedraw, 'dock forces full-frame GTK redraws for its entire lifetime');

        // Test actual pixels, not just the presence of a mapped GPU effect.
        // Use a sharp black/white edge behind the dock and hide only its tint.
        // Force a full-stage capture and compare against disabling the effect.
        // Screenshots repaint the scene; parent-cache behavior was separately
        // reproduced and resolved on the user's VM by disabling redirection.
        const edgeX = 620, sampleY = 745;
        const pattern = new St.Widget({x: 0, y: 600, width: 1280, height: 200,
            style: 'background-color: black;'});
        pattern.add_child(new St.Widget({x: edgeX, y: 0, width: 660, height: 200,
            style: 'background-color: white;'}));
        dockHolder.get_parent().insert_child_below(pattern, dockHolder);
        this._objects.push({disable: () => pattern.destroy()});
        dockHolder._background.opacity = 0;
        dockInfo.background.get_effects()[0].queue_repaint();
        await wait();
        const stagePixels = await edgeContrast(edgeX, sampleY);
        dockInfo.background.get_effects()[0].enabled = false;
        dockInfo.background.get_effects()[0].queue_repaint();
        await wait();
        const disabledPixels = await edgeContrast(edgeX, sampleY);
        console.log(`INFINITY_DOCK_BLUR_PIXELS ${JSON.stringify({stagePixels, disabledPixels})}`);
        check(stagePixels.left > 10 && stagePixels.right < 220 &&
            stagePixels.contrast + 60 < disabledPixels.contrast,
        'dock GPU effect does not soften the stage edge, or disabled-effect control is ineffective');
        dockInfo.background.get_effects()[0].enabled = true;
        dockHolder._background.opacity = 255;
        pattern.destroy();
        this._objects.pop();
        dockInfo.background.get_effects()[0].queue_repaint();
        await wait();
        blurController.enabled = false;
        dockInfo.background_group._infinityPanelBackdrop.destroy();
        dockInfo.update_size();
        await wait(); await wait();
        check(dockHolder._background._surfaceLayers?.every(color => color[3] === 0),
            'dock fallback is opaque when its matching blur is unavailable');
        check(dockInfo.background.get_effects().length === 0, 'dock fallback keeps an independent blur');
        dockIntegration.bms_update_size(dockAnimator);
        Dock.prototype._updateTransparenies.call(dockHolder);
        check(!dockInfo.background_group.visible, 'animation reveals an independent fallback blur');
        blurController.enabled = true; await wait(); await wait();
        check(dockInfo.background_group._infinityPanelBackdrop, 'dock did not recover its matching blur');
        dockIntegration.bms_update_size(dockAnimator);
        check(dockInfo.background_group.visible, 'animation hides the recovered blur');

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
            const glyph = new St.Icon({icon_name: 'view-grid-symbolic', style_class: 'system-status-icon'});
            app._trayGlyph = glyph;
            if (index === 1) {
                const nested = new St.BoxLayout({style_class: 'panel-status-menu-box'});
                nested.add_child(glyph);
                app.add_child(nested);
            } else app.add_child(glyph);
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
        const glyphs = [trayIcon, ...extraTrayApps.map(app => app._trayGlyph)];
        const glyphCenters = glyphs.map(glyph => glyph.get_transformed_position()[0] + glyph.get_transformed_size()[0] / 2);
        for (let index = 0; index < glyphs.length; index++)
            check(Math.abs(glyphCenters[index] - centers[index]) <= 1,
                `tray glyph is off center inside its cell: ${index}: ${glyphCenters[index]} / ${centers[index]}`);
        check(Math.abs((glyphCenters[1] - glyphCenters[0]) - (glyphCenters[2] - glyphCenters[1])) <= 1,
            'nested clipboard content causes unequal visible glyph spacing');
        extraTrayApps[0].hide(); await wait();
        check(!tray._entries.get(extraTrayApps[0]).wrapper.visible, 'hidden tray app left an empty cell');
        const compactGap = cells[2].get_transformed_position()[0] - cells[0].get_transformed_position()[0];
        check(Math.abs(compactGap - (centers[1] - centers[0])) <= 1, 'hidden tray app leaves a gap');
        extraTrayApps[0].show(); await wait();

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
        blurController.enabled = false;
        const client = Gio.Subprocess.new(['python3', this.dir.get_child('updater-client.py').get_path()],
            Gio.SubprocessFlags.NONE);
        this._objects.push({disable: () => client.force_exit()});
        await wait(); await wait(); await wait();
        const drawer = global.get_window_actors().find(actor => updater._isUpdater(actor.meta_window));
        check(drawer, 'updater client did not map');
        const readBackdrop = () => {
            const [, bytes] = GLib.file_get_contents(GLib.getenv('INFINITY_SMOKE_BACKDROP_REPORT'));
            return JSON.parse(new TextDecoder().decode(bytes));
        };
        check(!readBackdrop().transparent, 'GTK became transparent before its blur was ready');
        blurController.enabled = true;
        updater._drawerBackdrop.syncAll();
        await wait();
        check(readBackdrop().transparent, 'real updater retained its opaque GTK background over the blur');
        check(redrawOwner.fullRedraw, 'dynamic drawer blur permits clipped repaint artifacts');
        const frame = drawer.meta_window.get_frame_rect();
        const area = Main.layoutManager.getWorkAreaForMonitor(drawer.meta_window.get_monitor());
        check(frame.width === Math.min(460, area.width) && frame.height === area.height, 'updater remained at initial size');
        check(drawer.opacity === 255 && Math.abs(drawer.translation_x) < 1, 'updater did not finish its spring slide');
        const trackedDrawer = Shell.WindowTracker.get_default().get_window_app(drawer.meta_window);
        check(trackedDrawer && excludeFromDock(trackedDrawer), 'drawer appears as a running dock application');
        for (let i = 0; i < 3; i++) {
            updater._toggleDrawer(drawer.meta_window);
            await wait();
            check(drawer.meta_window.minimized, 'hidden drawer did not minimize');
            updater._toggleDrawer(drawer.meta_window);
            await wait(); await wait();
            check(!drawer.meta_window.minimized && drawer.opacity === 255 && Math.abs(drawer.translation_x) < 1,
                'restored drawer is not interactive at its visible position');
            check(excludeFromDock(trackedDrawer), 'restored drawer leaked into the running applications');
        }
        const drawerBackdrop = updater._drawerBackdrop._entries.get(drawer.meta_window);
        check(drawerBackdrop?.backdrop, 'updater has no panel-matched native blur');
        check(drawerBackdrop.container.clip_to_allocation, 'updater blur includes the window shadow');
        check(drawerBackdrop.backdrop.background.width === frame.width &&
            drawerBackdrop.backdrop.background.height === frame.height, 'updater blur does not fill the drawer');
        check(drawer.get_children().indexOf(drawerBackdrop.container) === 0, 'updater blur covers GTK contents');
        // Headless input can clamp virtual pointers to the top edge. Drive the
        // real GTK hover/focus states instead; GTK still submits its production
        // render nodes and Wayland surface damage to the native compositor.
        const inputPath = GLib.getenv('INFINITY_SMOKE_BACKDROP_REPORT').replace(/\.json$/, '.input');
        for (const mode of ['hover', 'focus']) {
            for (let index = 0; index < readBackdrop().buttons.length; index++) {
                GLib.file_set_contents(inputPath, JSON.stringify([index, mode]));
                await wait();
                check(readBackdrop().buttons[index][mode], `GTK did not apply ${mode} to action ${index}`);
                check(redrawOwner.fullRedraw, 'control damage disabled complete-frame blur repaint');
            }
        }
        GLib.file_set_contents(inputPath, JSON.stringify([-1, 'hover']));
        await wait();
        check(readBackdrop().buttons.every(button => !button.hover && !button.focus),
            'GTK retained a hover/focus state after exit');
        blurController.enabled = false; updater._drawerBackdrop.syncAll(); await wait();
        check(!readBackdrop().transparent, 'GTK did not restore its fallback when blur stopped');
        check(!redrawOwner.fullRedraw, 'blur loss left full repaint enabled');
        blurController.enabled = true; updater._drawerBackdrop.syncAll(); await wait();
        check(readBackdrop().transparent, 'GTK did not recover when blur returned');
        updater._drawerBackdrop.detach(drawer.meta_window); await wait();
        check(!readBackdrop().transparent, 'GTK remained transparent after the backdrop was detached');
        check(!redrawOwner.fullRedraw, 'detaching drawer left full repaint enabled');
        // Exercise the terminal controller against a real Wayland window actor.
        terminalController._window = drawer.meta_window;
        terminalController._hardware = monitor;
        terminalController._resizeHandle = new St.Widget();
        terminalController._drawerBackdrop = new PanelBackdrop({exportReadiness: false});
        try {
            terminalController._syncResizeHandle();
            await wait();
            const entry = terminalController._drawerBackdrop._entries.get(drawer.meta_window);
            for (const surface of [entry, entry?.stripSurface])
                check(surface?.backdrop?.background.is_mapped() && surface.backdrop.background.get_effects().length,
                    'terminal window or widget strip lacks a mapped native blur');
            check(monitor.actor.get_children()[0] === entry.stripSurface.container,
                'terminal blur covers the widget strip contents');
            check(!readBackdrop().transparent, 'terminal claimed updater backdrop readiness');
        } finally {
            terminalController._drawerBackdrop.destroy();
            terminalController._drawerBackdrop = null;
            terminalController._resizeHandle.destroy();
            terminalController._resizeHandle = null;
            terminalController._hardware = null;
            terminalController._window = null;
            monitor.hide();
        }
        updater._drawerBackdrop.attach(drawer.meta_window); await wait();
        check(readBackdrop().transparent, 'GTK did not recover after reattaching the backdrop');
        for (const [app, ready] of [['Setup', 'SetupReady'], ['Config', 'ConfigReady']]) {
            const id = `org.infinityos.${app}`;
            const report = GLib.getenv('INFINITY_SMOKE_BACKDROP_REPORT').replace(/\.json$/, `-${app}.state`);
            const surface = Gio.Subprocess.new(['python3', this.dir.get_child('app-backdrop-client.py').get_path(),
                id, ready, report], Gio.SubprocessFlags.NONE);
            this._objects.push({disable: () => surface.force_exit()});
            await wait(); await wait(); await wait();
            const found = global.get_window_actors().find(actor => actor.meta_window?.get_gtk_application_id() === id);
            check(found && updater._drawerBackdrop._entries.get(found.meta_window)?.backdrop,
                `${app} did not receive the shared GNOME Shell blur`);
            const read = () => new TextDecoder().decode(GLib.file_get_contents(report)[1]);
            check(read() === 'ready', `${app} stayed opaque after its backdrop became ready`);
            const other = ready === 'SetupReady' ? 'ConfigReady' : 'SetupReady';
            check(!updater._drawerBackdrop[other], `${app} made the other app's backdrop appear ready`);
            updater._drawerBackdrop.detach(found.meta_window); await wait();
            check(read() === 'opaque', `${app} lost its backdrop without restoring the opaque fallback`);
            surface.force_exit(); await wait();
        }
        const panelIndicators = new PanelIndicators();
        this._objects.push({disable: () => panelIndicators.destroy()});
        const powerIcon = Main.panel.statusArea.quickSettings._powerProfiles._indicator;
        powerIcon.show();
        check(!powerIcon.visible, 'power-profile icon reappeared after profile sync');
        this.disable();
        // Isolate virtual input from the geometry, menu and GTK checks above.
        // Hold the real pointer still over a Shell surface. Cursor assets can
        // contain many frames yet still appear static in the running compositor.
        const cursorSurface = new St.Widget({x: 500, y: 300, width: 160, height: 120,
            reactive: true, track_hover: true});
        Main.layoutManager.addTopChrome(cursorSurface);
        const seat = global.stage.get_context().get_backend().get_default_seat();
        const pointer = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        const tracker = global.backend.get_cursor_tracker();
        const previousCursor = global.stage.get_cursor_type();
        for (const type of [Clutter.CursorType.WAIT, Clutter.CursorType.PROGRESS]) {
            const svgCursor = new St.Cursor({backend: global.backend,
                theme_name: 'InfinityOS-Modern-Ice', size: 32, cursor_type: type});
            check(svgCursor.init(null), 'GNOME 51 SVG cursor provider rejected the theme');
        }
        // Native headless sessions have no physical pointer focus. Explicitly
        // keep the Shell cursor selected while exercising its native animation.
        seat.inhibit_unfocus();
        const cursorGrab = Main.pushModal(cursorSurface, {actionMode: Shell.ActionMode.ALL});
        try {
            for (const [name, type] of [['wait', Clutter.CursorType.WAIT], ['progress', Clutter.CursorType.PROGRESS]]) {
                cursorSurface.set_cursor_type(type);
                global.stage.set_cursor_type(type);
                pointer.notify_absolute_motion(GLib.get_monotonic_time(), 580, 350);
                await new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 60, () => {
                    resolve(); return GLib.SOURCE_REMOVE;
                }));
                let changes = 0;
                let missingSprite = 0;
                const geometry = new Set();
                const cursorChanged = tracker.connect('cursor-changed', () => {
                    const sprite = tracker.get_sprite();
                    if (!sprite) { missingSprite++; return; }
                    changes++;
                    geometry.add(JSON.stringify([sprite.get_width(), sprite.get_height(), ...tracker.get_hot()]));
                });
                try { await wait(); }
                finally { tracker.disconnect(cursorChanged); }
                console.log(`INFINITY_WAIT_CURSOR ${JSON.stringify({name, changes, missingSprite,
                    hovered: cursorSurface.has_pointer, pointer: global.get_pointer().slice(0, 2),
                    geometry: [...geometry]})}`);
                check(changes >= 15, `${name} cursor frames do not advance with a stationary pointer`);
                check(geometry.size === 1 && geometry.has('[32,32,16,20]'),
                    `${name} cursor changes size/hotspot or uses the wrong theme`);
            }
        } finally {
            global.stage.set_cursor_type(previousCursor);
            Main.popModal(cursorGrab);
            seat.uninhibit_unfocus();
            Main.layoutManager.removeChrome(cursorSurface);
            cursorSurface.destroy();
            pointer.run_dispose();
        }
        // Test the normal client path after releasing the modal Shell test.
        // Do not force the stage cursor or grab input. Headless Mutter hides
        // pointers without physical hardware; retain focus for the virtual seat
        // so GTK receives real Wayland pointer-enter and cursor-shape requests.
        seat.inhibit_unfocus();
        const cursorReport = GLib.getenv('INFINITY_SMOKE_CURSOR_REPORT');
        const cursorMode = cursorReport.replace(/\.json$/, '.mode');
        const cursorClient = Gio.Subprocess.new(['python3', this.dir.get_child('cursor-client.py').get_path()],
            Gio.SubprocessFlags.NONE);
        const clientPointer = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        try {
            await wait(); await wait();
            const clientWindow = global.get_window_actors().find(actor =>
                actor.meta_window.get_title() === 'Infinity cursor playback')?.meta_window;
            check(clientWindow, 'GTK cursor test window did not map');
            // Closing the updater fixture can reveal GNOME's overview. Use
            // normal application activation, which also dismisses that overview.
            Main.activateWindow(clientWindow);
            await wait();
            check(Main.modalCount === 0, `a Shell modal leaked into the GTK cursor test: ${modalActors()}`);
            check(clientWindow.get_client_type() === Meta.WindowClientType.WAYLAND,
                'cursor fixture is not a native Wayland client');
            const rect = clientWindow.get_frame_rect();
            const x = rect.x + rect.width / 2, y = rect.y + rect.height / 2;
            const readCursorReport = () => {
                const [, bytes] = GLib.file_get_contents(cursorReport);
                return JSON.parse(new TextDecoder().decode(bytes));
            };
            for (const name of ['wait', 'progress']) {
                GLib.file_set_contents(cursorMode, name);
                await wait();
                // Headless virtual pointers can clamp their first motion to y=0.
                clientPointer.notify_absolute_motion(GLib.get_monotonic_time(), x, y);
                seat.warp_pointer(x, y);
                global.stage.queue_redraw();
                await wait();
                clientPointer.notify_absolute_motion(GLib.get_monotonic_time(), x, y);
                seat.warp_pointer(x, y);
                global.stage.queue_redraw();
                await wait();
                const state = readCursorReport();
                console.log(`INFINITY_GTK_CURSOR_FOCUS ${JSON.stringify({state, target: [x, y],
                    pointer: global.get_pointer().slice(0, 2),
                    focus: global.display.focus_window?.get_title()})}`);
                check(state.pointer_here && state.mode === name, 'pointer did not enter the real GTK cursor surface');
                let changes = 0;
                const geometry = new Set();
                const changed = tracker.connect('cursor-changed', () => {
                    changes++;
                    const sprite = tracker.get_sprite();
                    if (sprite) geometry.add(JSON.stringify([
                        sprite.get_width(), sprite.get_height(), ...tracker.get_hot()]));
                });
                try { await wait(); }
                finally { tracker.disconnect(changed); }
                console.log(`INFINITY_GTK_WAIT_CURSOR ${JSON.stringify({name, changes, geometry: [...geometry]})}`);
                check(changes >= 15, `normal GTK ${name} cursor does not animate without a Shell grab`);
                check(geometry.size <= 1 && (!geometry.size || geometry.has('[32,32,16,20]')),
                    `GTK ${name} cursor uses the wrong theme or changes geometry`);
            }
        } finally {
            cursorClient.force_exit();
            clientPointer.run_dispose();
            seat.uninhibit_unfocus();
        }
        console.log('INFINITY_SMOKE_PASS');
    }

    disable() {
        for (const object of this._objects.reverse()) object.disable();
        this._objects = [];
    }
}
