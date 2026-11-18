import NM from 'gi://NM';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

// Change only top-bar glyphs; keep the network and power-profile controls intact.
export default class PanelIndicators {
    constructor() {
        this._injections = new InjectionManager();
        this._devices = new Set();
        const quick = Main.panel.statusArea.quickSettings;
        this._power = quick?._powerProfiles;
        this._powerIcon = this._power?._indicator;
        this._powerIcon?.connectObject('notify::visible', () => this._powerIcon.hide(), this);
        this._powerIcon?.hide();
        this._network = quick?._network;
        if (!this._network) return;
        const owner = this;
        this._injections.overrideMethod(this._network, '_updateIcon', original => function (...args) {
            const result = original.apply(this, args);
            owner._syncNetwork();
            return result;
        });
        this._network._wirelessToggle?.connectObject('notify::icon-name',
            () => this._syncNetwork(), this);
        this._syncNetwork();
    }

    _syncNetwork() {
        const network = this._network;
        const client = network?._client;
        if (!client || this._syncing) return;
        this._syncing = true;
        try {
            if (client !== this._client) {
                this._client?.disconnectObject(this);
                this._client = client;
                client.connectObject(
                    'notify::active-connections', () => this._syncNetwork(),
                    'notify::state', () => this._syncNetwork(),
                    'device-added', () => this._syncNetwork(),
                    'device-removed', () => this._syncNetwork(), this);
            }
            const devices = new Set(client.get_devices());
            for (const device of this._devices) {
                if (!devices.has(device)) device.disconnectObject(this);
            }
            for (const device of devices) {
                if (!this._devices.has(device))
                    device.connectObject('notify::state', () => this._syncNetwork(), this);
            }
            this._devices = devices;
            const active = [...devices].filter(device => device.state === NM.DeviceState.ACTIVATED);
            const wifi = active.some(device => device.device_type === NM.DeviceType.WIFI);
            const wired = active.some(device => device.device_type === NM.DeviceType.ETHERNET);
            network._primaryIndicatorBinding.source = wifi ? network._wirelessToggle : null;
            network._primaryIndicator.icon_name = wifi
                ? network._wirelessToggle.icon_name : 'network-offline-symbolic';
            network._primaryIndicator.visible = wifi || !wired;
        } finally {
            this._syncing = false;
        }
    }

    destroy() {
        this._injections.clear();
        this._client?.disconnectObject(this);
        for (const device of this._devices) device.disconnectObject(this);
        this._devices.clear();
        this._network?._wirelessToggle?.disconnectObject(this);
        if (this._network?._client) this._network._updateIcon();
        this._powerIcon?.disconnectObject(this);
        if (this._powerIcon)
            this._powerIcon.visible = !!this._power._powerProfilesToggle.checked;
    }
}
