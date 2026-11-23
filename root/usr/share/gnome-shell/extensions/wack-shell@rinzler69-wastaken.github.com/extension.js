import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as OverviewControls from 'resource:///org/gnome/shell/ui/overviewControls.js';

import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

import {
    WackLogoButton,
    WackAppMenuButton,
    WackWorkspaceButton,
    QuickSettingsPowerManager
} from './panelComponents.js';
import VibrancyManager from './vibrancyManager.js';
import InstallerDim from './installerDim.js';
import AppDashboard from './appDashboard.js';
import UserTray from './userTray.js';
import PanelIndicators from './panelIndicators.js';
import RamdriveRestart from './ramdriveRestart.js';
import { createWarpButton } from './warpButton.js';
import { APP_GRID_WORKSPACE_RATIO, APP_GRID_WORKSPACE_FADE_RANGE, APP_GRID_WORKSPACE_FADE_SNAP } from './constants.js';

export default class WackShellExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._limitDashIconSize();


        // Hide native activities button and suppress it from showing up
        const activities = Main.panel.statusArea['activities'];
        if (activities?.container) {
            activities.container.hide();
            activities.container.connectObject('show', () => {
                activities.container.hide();
            }, this);
        }
        this._activities = activities;

        this._logoButton = null;
        this._workspaceButton = null;
        this._appMenuButton = null;

        this._warpButton = createWarpButton(this.path);
        Main.panel.addToStatusArea('infinity-warp', this._warpButton, 1, 'right');


        this._sessionModeOwner = {};
        Main.sessionMode.connectObject('updated', () => this._syncSessionModeUI(), this._sessionModeOwner);

this._settings.connectObject(
    'changed::show-logo-menu', () => this._syncLogoMenu(),
    'changed::show-workspace-widget', () => this._syncWorkspaceWidget(),
    'changed::show-app-menu', () => this._syncAppMenu(),
    'changed::show-app-menu-icon', () => this._appMenuButton?._updateAppMenuVisibility(),
    'changed::show-app-menu-label', () => this._appMenuButton?._updateAppMenuVisibility(),
    this
);

        this._syncLogoMenu();
        this._syncWorkspaceWidget();
        this._syncAppMenu();
        this._initProximity();

        // Initialize and enable VibrancyManager
        this._vibrancyManager = new VibrancyManager(this, this._settings);
        this._vibrancyManager.enable();
        try {
            this._installerDim = new InstallerDim();
        } catch (error) {
            console.warn(`[WACK Shell] installer dim unavailable: ${error}`);
        }

        // Initialize QuickSettings power controls manager
        this._qsPowerManager = new QuickSettingsPowerManager(this);
        this._userTray = new UserTray();
        this._panelIndicators = new PanelIndicators();
        this._ramdriveRestart = new RamdriveRestart();
        this._qsPowerManager.sync();

        this._initWorkspacesAppGrid();
        this._appDashboard = new AppDashboard();
        if (!global.infinityosPanelEntrancePlayed && Main.sessionMode.currentMode === 'user') {
            global.infinityosPanelEntrancePlayed = true;
            const animations = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'})
                .get_boolean('enable-animations');
            if (animations) {
                this._entranceActive = true;
                Main.panel.translation_y = -50;
                Main.panel.opacity = 0;
                const revealPanel = () => {
                    this._entranceSourceId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1110, () => {
                        this._entranceSourceId = 0;
                        Main.panel.ease({translation_y: 0, opacity: 255, duration: 420,
                            mode: Clutter.AnimationMode.EASE_OUT_CUBIC,
                            onComplete: () => { this._entranceActive = false; }});
                        return GLib.SOURCE_REMOVE;
                    });
                };
                if (Main.layoutManager._startingUp) {
                    this._entranceStartupId = Main.layoutManager.connect('startup-complete', () => {
                        Main.layoutManager.disconnect(this._entranceStartupId);
                        this._entranceStartupId = 0;
                        revealPanel();
                    });
                } else {
                    revealPanel();
                }
            }
        }
    }

    disable() {
        this._ramdriveRestart?.destroy();
        this._ramdriveRestart = null;
        this._panelIndicators?.destroy();
        this._panelIndicators = null;
        this._userTray?.destroy();
        this._userTray = null;
        this._installerDim?.destroy();
        this._installerDim = null;
        if (this._entranceStartupId) {
            Main.layoutManager.disconnect(this._entranceStartupId);
            this._entranceStartupId = 0;
        }
        if (this._entranceSourceId) {
            GLib.source_remove(this._entranceSourceId);
            this._entranceSourceId = 0;
        }
        if (this._entranceActive) {
            this._entranceActive = false;
            Main.panel.remove_all_transitions();
            Main.panel.translation_y = 0;
            Main.panel.opacity = 255;
        }
        this._restoreDashIconSize();
        const currentMode = Main.sessionMode.currentMode;
        const isLockscreen = currentMode === 'unlock-dialog' || currentMode === 'greeter' ||
            currentMode === 'gdm' || Main.screenShield?.active || Main.screenShield?.locked;

        this._activities?.container?.disconnectObject(this);
        this._activities = null;

        if (this._sessionModeOwner) {
            Main.sessionMode.disconnectObject(this._sessionModeOwner);
            this._sessionModeOwner = null;
        }

        if (this._proximityWriteCancellable) {
            this._proximityWriteCancellable.cancel();
            this._proximityWriteCancellable = null;
        }

        this._destroyProximityTracking();
        this._unloadProximityStylesheet();
        this._clearPanelStyle();

        if (this._queuedUpdateId) {
            GLib.source_remove(this._queuedUpdateId);
            this._queuedUpdateId = null;
        }

        // Disable VibrancyManager
        if (this._vibrancyManager) {
            this._vibrancyManager.disable();
            this._vibrancyManager = null;
        }

        if (this._qsPowerManager) {
            this._qsPowerManager.destroy();
            this._qsPowerManager = null;
        }

        if (this._activeSelection) {
            this._activeSelection.destroy();
            this._activeSelection = null;
        }

        // Clear gradient and contrast styling
        Main.panel.set_style(null);
        Main.panel.remove_style_class_name('light-contrast');

        this._settings.disconnectObject(this);
        this._settings = null;

        this._desktopSettings?.disconnectObject(this);
        this._desktopSettings = null;



        if (this._logoButton) {
            this._logoButton.destroy();
            this._logoButton = null;
        }

        if (this._workspaceButton) {
            this._workspaceButton.destroy();
            this._workspaceButton = null;
        }

        if (this._appMenuButton) {
            this._appMenuButton.destroy();
            this._appMenuButton = null;
        }

        this._warpButton?.destroy();
        this._warpButton = null;

        // Restore native activities button (if not locked)
        if (!isLockscreen) {
            Main.panel.statusArea['activities']?.container.show();
        }
        this._appDashboard?.destroy();
        this._appDashboard = null;
        this._destroyWorkspacesAppGrid();
    }

    _limitDashIconSize() {
        // The animated dock owns its icon sizing; resampling its actor blurs icons.
        if (new Gio.Settings({schema_id: 'org.gnome.shell'})
            .get_strv('enabled-extensions').includes('dash2dock-animated@infinityos.org'))
            return;
        const dash = Main.overview?.dash;
        if (!dash || this._originalDashSetMaxSize)
            return;
        this._dash = dash;
        this._originalDashSetMaxSize = dash.setMaxSize;
        dash.setMaxSize = (width, height) => {
            this._lastDashSize = [width, height];
            this._originalDashSetMaxSize.call(dash, width, Math.min(height, 78));
        };
        if (dash._maxWidth > 0 && dash._maxHeight > 0)
            dash.setMaxSize(dash._maxWidth, dash._maxHeight);
    }

    _restoreDashIconSize() {
        if (!this._dash || !this._originalDashSetMaxSize)
            return;
        this._dash.setMaxSize = this._originalDashSetMaxSize;
        if (this._lastDashSize)
            this._dash.setMaxSize(...this._lastDashSize);
        this._dash = null;
        this._originalDashSetMaxSize = null;
        this._lastDashSize = null;
    }

    _syncLogoMenu() {
        const show = this._settings.get_boolean('show-logo-menu');

        if (show) {
            if (!this._logoButton) {
                this._logoButton = new WackLogoButton(this);
                Main.panel.addToStatusArea('wack-logo-menu', this._logoButton, 0, 'left');
            }
        } else {
            if (this._logoButton) {
                this._logoButton.destroy();
                this._logoButton = null;
            }
        }
        this._syncSessionModeUI();
    }

    _syncWorkspaceWidget() {
        const show = this._settings.get_boolean('show-workspace-widget');

        if (show) {
            if (!this._workspaceButton) {
                this._workspaceButton = new WackWorkspaceButton(this);
                // Position workspace widget next to logo (index 1)
                Main.panel.addToStatusArea('wack-workspace-button', this._workspaceButton, 1, 'left');
            }
        } else {
            if (this._workspaceButton) {
                this._workspaceButton.destroy();
                this._workspaceButton = null;
            }
        }
        this._syncSessionModeUI();
    }

    _syncAppMenu() {
        const show = this._settings.get_boolean('show-app-menu');

        if (show) {
            if (!this._appMenuButton) {
                this._appMenuButton = new WackAppMenuButton(this);
                // Position appmenu-indicator next to workspace button (index 2)
                Main.panel.addToStatusArea('wack-app-menu', this._appMenuButton, 2, 'left');
            }
        } else {
            if (this._appMenuButton) {
                this._appMenuButton.destroy();
                this._appMenuButton = null;
            }
        }
        this._syncSessionModeUI();
    }

    _syncSessionModeUI() {
        const hasWindows = Main.sessionMode.hasWindows;
        const isLocked = !hasWindows;
        const opacity = isLocked ? 0 : 255;
        const visible = !isLocked;
        if (this._warpButton) {
            this._warpButton.visible = visible;
            this._warpButton.reactive = visible;
            this._warpButton.can_focus = visible;
        }

        if (this._logoButton) {
            this._logoButton.opacity = opacity;
            this._logoButton.reactive = visible;
            this._logoButton.can_focus = visible;
            if (visible) {
                this._logoButton.show();
            } else {
                this._logoButton.hide();
            }

            if (this._logoButton.container) {
                this._logoButton.container.opacity = opacity;
                this._logoButton.container.reactive = visible;
                this._logoButton.container.can_focus = visible;
                if (visible) {
                    this._logoButton.container.show();
                } else {
                    this._logoButton.container.hide();
                }
            }
        }
        if (this._workspaceButton) {
            this._workspaceButton.opacity = opacity;
            this._workspaceButton.reactive = visible;
            this._workspaceButton.can_focus = visible;
            if (visible) {
                this._workspaceButton.show();
            } else {
                this._workspaceButton.hide();
            }

            if (this._workspaceButton.container) {
                this._workspaceButton.container.opacity = opacity;
                this._workspaceButton.container.reactive = visible;
                this._workspaceButton.container.can_focus = visible;
                if (visible) {
                    this._workspaceButton.container.show();
                } else {
                    this._workspaceButton.container.hide();
                }
            }
        }
        if (this._appMenuButton) {
            this._appMenuButton._sync(true);
        }

        this._qsPowerManager?.sync();
    }

    _initWorkspacesAppGrid() {
        // V-Shell owns the overview layout when enabled. Do not wrap the same
        // GNOME Shell methods twice; its workspace transitions then stay intact.
        if (new Gio.Settings({schema_id: 'org.gnome.shell'})
            .get_strv('enabled-extensions').includes('vertical-workspaces@G-dH.github.com'))
            return;
        const hasDisableKey = this._settings.settings_schema.has_key('disable-workspaces-in-app-grid');
        const key = hasDisableKey ? 'disable-workspaces-in-app-grid' : 'workspaces-in-app-grid';

        const getVal = () => {
            const val = this._settings.get_boolean(key);
            return hasDisableKey ? val : !val;
        };

        this._disableWorkspacesInAppGrid = getVal();

        this._settings.connectObject(
            `changed::${key}`, () => {
                this._disableWorkspacesInAppGrid = getVal();
                const controls = Main.overview._overview?._controls;
                if (controls && controls.layout_manager) {
                    controls.layout_manager.layout_changed();
                    controls._update();
                }
            },
            this
        );

        const controls = Main.overview._overview?._controls;
        if (!controls || !controls.layout_manager) {
            return;
        }

        this._origComputeWorkspacesBoxForState = controls.layout_manager._computeWorkspacesBoxForState;
        this._origGetAppDisplayBoxForState = controls.layout_manager._getAppDisplayBoxForState;
        this._origUpdate = controls._update;
        this._origOnSearchChanged = controls._onSearchChanged;

        const self = this;

        // Reduce the reserved workspace area in App Grid state from GNOME's
        // default 15% to APP_GRID_WORKSPACE_RATIO — but ONLY when the workspace
        // view is disabled. When it's visible the user sees the real thumbnail,
        // so GNOME's native ratio is left untouched.
        controls.layout_manager._computeWorkspacesBoxForState = function (state, box, searchHeight, dashHeight, thumbnailsHeight, spacing) {
            const workspaceBox = self._origComputeWorkspacesBoxForState.call(
                this, state, box, searchHeight, dashHeight, thumbnailsHeight, spacing);
            if (state === OverviewControls.ControlsState.APP_GRID && self._disableWorkspacesInAppGrid) {
                const [width] = workspaceBox.get_size();
                const [, boxHeight] = box.get_size();
                workspaceBox.set_size(width, Math.round(boxHeight * APP_GRID_WORKSPACE_RATIO));
            }
            return workspaceBox;
        };

        // Instead of collapsing the workspace to height=0 (which corrupts
        // WorkspaceLayout._windowSlots and causes the slide-in blip), we keep
        // the workspace at its real allocation and only hide it via opacity.
        //
        // The emptyBox trick is applied to ALL states (not just APP_GRID) so
        // that the app grid has identical sizing at both ends of the
        // WINDOW_PICKER→APP_GRID transition. Without this, GNOME interpolates
        // between a smaller initial-state size and a larger final-state size,
        // causing the app grid icons to reflow mid-animation ("two faces").
        controls.layout_manager._getAppDisplayBoxForState = function (state, box, searchHeight, dashHeight, workspacesBox, spacing) {
            if (self._disableWorkspacesInAppGrid) {
                const emptyBox = workspacesBox.copy();
                emptyBox.set_size(emptyBox.get_width(), 0);
                return self._origGetAppDisplayBoxForState.call(this, state, box, searchHeight, dashHeight, emptyBox, spacing);
            }
            return self._origGetAppDisplayBoxForState.call(this, state, box, searchHeight, dashHeight, workspacesBox, spacing);
        };

        controls._update = function () {
            self._origUpdate.call(this);
            self._updateWorkspacesOpacity(this);
        };

        controls._onSearchChanged = function () {
            const oldEase = this._workspacesDisplay.ease;
            this._workspacesDisplay.ease = function (props) {
                if (props && props.opacity === 255) {
                    props.opacity = self._getWorkspacesTargetOpacity(this);
                }
                return oldEase.call(this, props);
            };
            try {
                self._origOnSearchChanged.call(this);
            } finally {
                this._workspacesDisplay.ease = oldEase;
            }
        };

        controls.layout_manager.layout_changed();
        controls._update();
    }

    _getWorkspacesTargetOpacity(controls) {
        if (!this._disableWorkspacesInAppGrid)
            return 255;

        const adjustment = controls._stateAdjustment;
        if (!adjustment)
            return 255;

        const v = adjustment.value;
        if (v <= 1.0)
            return 255;

        const progress = Math.min(1.0, v - 1.0);

        if (progress < APP_GRID_WORKSPACE_FADE_SNAP) {
            // Phase 1: virtual-range linear lerp.
            // Starts immediately at progress=0 and is always proportional,
            // so mid-gesture reversal tracks opacity smoothly with no snap.
            //   t = progress / FADE_RANGE  →  opacity = 255 * (1 - t)
            const t = progress / APP_GRID_WORKSPACE_FADE_RANGE;
            return Math.max(0, Math.round(255 * (1.0 - t)));
        }

        // Phase 2: ease-out-quad finishing curve.
        // Picks up at the exact opacity the linear phase left off at SNAP,
        // then drives it to 0 using (1 - q)² — fast initial drop that
        // decelerates as it approaches transparent (ease-out on the fade-out).
        //   q = (progress - SNAP) / (1 - SNAP)  [0 → 1]
        //   opacity = opacityAtSnap * (1 - q)²
        const opacityAtSnap = 255 * (1.0 - APP_GRID_WORKSPACE_FADE_SNAP / APP_GRID_WORKSPACE_FADE_RANGE);
        const q = (progress - APP_GRID_WORKSPACE_FADE_SNAP) / (1.0 - APP_GRID_WORKSPACE_FADE_SNAP);
        return Math.max(0, Math.round(opacityAtSnap * (1.0 - q) * (1.0 - q)));
    }

    _updateWorkspacesOpacity(controls) {
        if (controls._searchController.searchActive) {
            controls._workspacesDisplay.opacity = 0;
        } else {
            controls._workspacesDisplay.opacity = this._getWorkspacesTargetOpacity(controls);
        }
    }

    _destroyWorkspacesAppGrid() {
        const controls = Main.overview._overview?._controls;
        if (controls) {
            if (this._origComputeWorkspacesBoxForState && controls.layout_manager) {
                controls.layout_manager._computeWorkspacesBoxForState = this._origComputeWorkspacesBoxForState;
                this._origComputeWorkspacesBoxForState = null;
            }
            if (this._origGetAppDisplayBoxForState && controls.layout_manager) {
                controls.layout_manager._getAppDisplayBoxForState = this._origGetAppDisplayBoxForState;
                this._origGetAppDisplayBoxForState = null;
            }
            if (this._origUpdate) {
                controls._update = this._origUpdate;
                this._origUpdate = null;
            }
            if (this._origOnSearchChanged) {
                controls._onSearchChanged = this._origOnSearchChanged;
                this._origOnSearchChanged = null;
            }

            controls._workspacesDisplay.opacity = 255;
            if (controls.layout_manager) {
                controls.layout_manager.layout_changed();
                controls._update();
            }
        }
    }

    _initProximity() {
        this._proximityWindowSignals = new Map();
        this._themeContext = St.ThemeContext.get_for_stage(global.stage);
        const cacheDir = GLib.get_user_cache_dir();
        this._customCssPath = GLib.build_filenamev([cacheDir, 'wack-shell-custom.css']);
        this._customCssFile = Gio.File.new_for_path(this._customCssPath);
        this._desktopSettings = new Gio.Settings({ schema: "org.gnome.desktop.interface" });
        this._proximityRequestToken = 0;
        this._proximityWriteCancellable = null;

        this._settings.connectObject(
            'changed::enable-panel-proximity', () => this._syncProximity(),
            'changed::dark-bg-color', () => this._updateProximityStylesheet(),
            'changed::dark-fg-color', () => this._updateProximityStylesheet(),
            'changed::light-bg-color', () => this._updateProximityStylesheet(),
            'changed::light-fg-color', () => this._updateProximityStylesheet(),
            this
        );

        this._desktopSettings.connectObject(
            'changed::color-scheme', () => this._updateProximityStylesheet(),
            this
        );

        this._syncProximity();
    }

    _syncProximity() {
        const enabled = this._settings.get_boolean('enable-panel-proximity');

        this._destroyProximityTracking();

        if (this._queuedUpdateId) {
            GLib.source_remove(this._queuedUpdateId);
            this._queuedUpdateId = null;
        }

        if (enabled) {
            this._updateProximityStylesheet();
            this._connectProximitySignals();
        } else {
            this._unloadProximityStylesheet();
            this._clearPanelStyle();
        }
    }

    _connectProximitySignals() {
        for (const meta_window_actor of global.get_window_actors()) {
            this._onProximityWindowActorAdded(meta_window_actor.get_parent(), meta_window_actor);
        }

        global.window_group.connectObject(
            'child-added', this._onProximityWindowActorAdded.bind(this),
            'child-removed', this._onProximityWindowActorRemoved.bind(this),
            this
        );

        global.window_manager.connectObject(
            'switch-workspace', () => this._queueUpdatePanelVisibility(),
            this
        );

        Main.overview.connectObject(
            'showing', () => this._updatePanelVisibility(),
            'hiding', () => this._updatePanelVisibility(),
            'hidden', () => this._updatePanelVisibility(),
            this
        );

        Main.sessionMode.connectObject(
            'updated', () => this._updatePanelVisibility(),
            this
        );

        this._queueUpdatePanelVisibility();
    }

    _onProximityWindowActorAdded(container, meta_window_actor) {
        const signals = [
            { object: meta_window_actor, id: meta_window_actor.connect('notify::allocation', () => this._queueUpdatePanelVisibility()) },
            { object: meta_window_actor, id: meta_window_actor.connect('notify::visible', () => this._queueUpdatePanelVisibility()) }
        ];

        if (!meta_window_actor.meta_window) {
            signals.push({
                object: meta_window_actor, id: meta_window_actor.connect('notify::meta-window', () => {
                    if (meta_window_actor.meta_window) {
                        signals.push({ object: meta_window_actor.meta_window, id: meta_window_actor.meta_window.connect('notify::minimized', () => this._queueUpdatePanelVisibility()) });
                    }
                })
            });
        } else {
            signals.push({ object: meta_window_actor.meta_window, id: meta_window_actor.meta_window.connect('notify::minimized', () => this._queueUpdatePanelVisibility()) });
        }

        this._proximityWindowSignals.set(meta_window_actor, signals);
        this._queueUpdatePanelVisibility();
    }

    _onProximityWindowActorRemoved(container, meta_window_actor) {
        const signals = this._proximityWindowSignals.get(meta_window_actor);
        if (signals) {
            signals.forEach(sig => {
                try {
                    sig.object.disconnect(sig.id);
                } catch { }
            });
            this._proximityWindowSignals.delete(meta_window_actor);
        }
        this._queueUpdatePanelVisibility();
    }

    _destroyProximityTracking() {
        global.window_group.disconnectObject(this);
        global.window_manager.disconnectObject(this);
        Main.overview.disconnectObject(this);
        Main.sessionMode.disconnectObject(this);

        if (this._proximityWindowSignals) {
            for (const [, signals] of this._proximityWindowSignals) {
                signals.forEach(sig => {
                    try {
                        sig.object.disconnect(sig.id);
                    } catch { }
                });
            }
            this._proximityWindowSignals.clear();
        }
    }

    _unloadProximityStylesheet() {
        try {
            this._themeContext.get_theme().unload_stylesheet(this._customCssFile);
        } catch { }
        this._themeId = false;
    }

    _isProximityDarkMode() {
        return this._desktopSettings.get_string('color-scheme') === 'prefer-dark';
    }

    _updateProximityStylesheet() {
        if (this._proximityWriteCancellable) {
            this._proximityWriteCancellable.cancel();
            this._proximityWriteCancellable = null;
        }

        this._unloadProximityStylesheet();

        if (!this._settings.get_boolean('enable-panel-proximity')) {
            return;
        }

        const isDark = this._isProximityDarkMode();
        const fg = this._settings.get_string(isDark ? 'dark-fg-color' : 'light-fg-color');
        const fgCss = fg.replace(/'/g, '');

        const cssString = `
#panel.panel-proximity {
    background-color: transparent !important;
}

#panel.panel-proximity,
#panel.panel-proximity *,
#panel.panel-proximity .panel-button,
#panel.panel-proximity .panel-button * {
    color: ${fgCss} !important;
}

#panel.panel-proximity .system-status-icon,
#panel.panel-proximity .app-menu-icon,
#panel.panel-proximity .popup-menu-arrow {
    color: ${fgCss} !important;
}

#panel.panel-proximity .workspace-dot {
    border-radius: 999px;
    background-color: ${fgCss} !important;
}
`;
        const bytes = new TextEncoder().encode(cssString);

        const cancellable = new Gio.Cancellable();
        this._proximityWriteCancellable = cancellable;
        const requestToken = ++this._proximityRequestToken;

        this._customCssFile.replace_contents_async(
            bytes,
            null,
            false,
            Gio.FileCreateFlags.NONE,
            cancellable,
            (file, res) => {
                try {
                    file.replace_contents_finish(res);
                } catch {
                    return;
                }

                if (requestToken !== this._proximityRequestToken) return;
                if (this._proximityWriteCancellable === cancellable)
                    this._proximityWriteCancellable = null;
                if (!this._settings) return;

                this._themeContext.get_theme().load_stylesheet(this._customCssFile);
                this._themeId = true;
                this._queueUpdatePanelVisibility();
            }
        );
    }

    _queueUpdatePanelVisibility() {
        if (this._queuedUpdateId)
            return;

        this._queuedUpdateId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            this._queuedUpdateId = null;
            this._updatePanelVisibility();
            return GLib.SOURCE_REMOVE;
        });
    }

    _updatePanelVisibility() {
        if (Main.overview.visibleTarget) {
            this._clearPanelStyle();
            return;
        }

        const isLockscreen = Main.sessionMode.currentMode === 'unlock-dialog' && !Main.sessionMode.hasWindows;
        if (isLockscreen) {
            this._clearPanelStyle();
            return;
        }

        if (!this._settings.get_boolean('enable-panel-proximity')) {
            this._clearPanelStyle();
            return;
        }

        if (!Main.layoutManager.primaryMonitor) return;

        const workspace = global.workspace_manager.get_active_workspace();
        const windows = workspace.list_windows().filter(meta_window =>
            meta_window.showing_on_its_workspace() &&
            !meta_window.is_hidden() &&
            meta_window.get_window_type() !== Meta.WindowType.DESKTOP &&
            meta_window.get_gtk_application_id() !== "com.rastersoft.ding" &&
            meta_window.get_gtk_application_id() !== "com.desktop.ding"
        );

        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        const panel = Main.panel;
        const panelTop = panel.get_transformed_position()[1];
        const panelBottom = panelTop + panel.get_height();

        let windowNearPanel = false;
        windows.forEach(meta_window => {
            const windowMonitorIndex = meta_window.get_monitor();
            const sameMonitor = Main.layoutManager.primaryMonitor.index === windowMonitorIndex;

            const windowVerticalPos = meta_window.get_frame_rect().y;
            const windowVerticalBottom = windowVerticalPos + meta_window.get_frame_rect().height;

            if (sameMonitor &&
                ((panelTop === 0 && windowVerticalPos < panelBottom + 5 * scale) ||
                    (panelTop > 0 && windowVerticalBottom > panelTop - 5 * scale))
            ) {
                windowNearPanel = true;
            }
        });

        if (windowNearPanel) {
            this._applyPanelStyle();
        } else {
            this._clearPanelStyle();
        }
    }

    _applyPanelStyle() {
        Main.panel.add_style_class_name('panel-proximity');
        Main.panel.remove_style_class_name('light-contrast');

        for (const cls of ['panel-ventura-light', 'panel-bigsur']) {
            Main.panel.remove_style_class_name(cls);
        }

        Main.panel.set_style(null);

        if (this._vibrancyManager) {
            const isDark = this._isProximityDarkMode();
            const bg = this._settings.get_string(isDark ? 'dark-bg-color' : 'light-bg-color').replace(/'/g, '');
            const fg = this._settings.get_string(isDark ? 'dark-fg-color' : 'light-fg-color').replace(/'/g, '');
            this._vibrancyManager.setPanelProximity(true, bg, fg);
        }
    }

    _clearPanelStyle() {
        Main.panel.remove_style_class_name('panel-proximity');

        if (this._vibrancyManager) {
            this._vibrancyManager.setPanelProximity(false);
        }

        if (this._vibrancyManager && this._vibrancyManager.vibrancyActive) {
            this._vibrancyManager.applyVibrancyStyle();
        }
    }
}


