// SPDX-License-Identifier: GPL-2.0-or-later

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import Pango from 'gi://Pango';
import St from 'gi://St';
import {gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {playPauseIconName, setReactive} from './transport.js';

export class QuickSettingsPlayer {
    constructor(manager) {
        this._manager = manager;
        this.actor = new St.BoxLayout({
            style_class: 'mc-quick-settings-player',
            x_expand: true,
            visible: false,
        });
        this._fallbackIcon = Gio.ThemedIcon.new('audio-x-generic-symbolic');
        this._icon = new St.Icon({icon_size: 20, y_align: Clutter.ActorAlign.CENTER});
        this._label = new St.Label({
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        this._previous = this._button('media-skip-backward-symbolic', _('Previous track'),
            () => this._manager.activePlayer?.previous());
        this._playPause = this._button('media-playback-start-symbolic', _('Play'),
            () => this._manager.activePlayer?.playPause());
        this._next = this._button('media-skip-forward-symbolic', _('Next track'),
            () => this._manager.activePlayer?.next());
        for (const actor of [this._icon, this._label, this._previous, this._playPause, this._next])
            this.actor.add_child(actor);

        const quickSettings = Main.panel.statusArea.quickSettings;
        const brightness = quickSettings._brightness?.quickSettingsItems[0] ?? null;
        quickSettings.menu.insertItemBefore(this.actor, brightness, 2);
        manager.connectObject('changed', () => this._sync(), this.actor);
        this._sync();
    }

    _button(iconName, label, onClick) {
        const button = new St.Button({
            style_class: 'message-media-control',
            accessible_name: label,
            can_focus: true,
            y_align: Clutter.ActorAlign.CENTER,
            child: new St.Icon({icon_name: iconName, icon_size: 16}),
        });
        button.connect('clicked', onClick);
        return button;
    }

    _sync() {
        const player = this._manager.activePlayer;
        this.actor.visible = !!player;
        if (!player)
            return;

        this._icon.gicon = player.appIcon ?? this._fallbackIcon;
        const title = player.displayTitle || player.displayName;
        this._label.text = player.artist ? `${title} · ${player.artist}` : title;
        this._playPause.child.icon_name = playPauseIconName(player);
        this._playPause.accessible_name = player.isPlaying ? _('Pause') : _('Play');
        setReactive(this._previous, player.canGoPrevious);
        setReactive(this._playPause, player.isPlaying ? player.canPause : player.canPlay);
        setReactive(this._next, player.canGoNext);
    }

    destroy() {
        this.actor.destroy();
    }
}
