import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/panelIndicators.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class', 'class');
const NM = {DeviceType: {WIFI: 2, ETHERNET: 1}, DeviceState: {ACTIVATED: 100, DISCONNECTED: 30}};

function fixture(late = false) {
    class ObjectWithSignals {
        constructor(props = {}) {Object.assign(this, props); this.handlers = [];}
        connectObject(...args) {
            const owner = args.pop();
            for (let i = 0; i < args.length; i += 2)
                this.handlers.push({name: args[i], callback: args[i + 1], owner});
        }
        disconnectObject(owner) {this.handlers = this.handlers.filter(handler => handler.owner !== owner);}
        emit(name) {for (const handler of [...this.handlers]) if (handler.name === name) handler.callback(this);}
        set visible(value) {
            if (value === this._visible) return;
            this._visible = value;
            this.emit('notify::visible');
        }
        get visible() {return this._visible;}
        hide() {this.visible = false;}
    }
    const powerIcon = new ObjectWithSignals(); powerIcon.visible = true;
    const powerToggle = {checked: true};
    const wifi = new ObjectWithSignals({device_type: 2, state: 30});
    const wired = new ObjectWithSignals({device_type: 1, state: 30});
    const client = new ObjectWithSignals({devices: [wifi, wired], get_devices() {return this.devices;}});
    const wireless = new ObjectWithSignals({icon_name: 'network-wireless-signal-good-symbolic'});
    const vpnIcon = {visible: true};
    const network = {_client: late ? null : client, _primaryIndicator: {visible: true},
        _vpnIndicator: vpnIcon, _primaryIndicatorBinding: {source: 'native'},
        _wirelessToggle: wireless, quickSettingsItems: [wireless],
        _updateIcon() {
            this._primaryIndicatorBinding.source = 'native';
            this._primaryIndicator.icon_name = 'network-wired-symbolic';
            this._primaryIndicator.visible = true;
            return 42;
        }};
    const original = network._updateIcon;
    class InjectionManager {
        constructor() {this.restore = [];}
        overrideMethod(object, name, factory) {
            const previous = object[name]; this.restore.push(() => {object[name] = previous;});
            object[name] = factory(previous);
        }
        clear() {this.restore.reverse().forEach(restore => restore());}
    }
    const Controller = vm.runInNewContext(source + '\nPanelIndicators', {
        NM, InjectionManager, Main: {panel: {statusArea: {quickSettings: {
            _network: network, _powerProfiles: {_indicator: powerIcon, _powerProfilesToggle: powerToggle},
        }}}},
    });
    return {controller: new Controller(), network, original, client, wifi, wired, powerIcon, powerToggle, wireless, vpnIcon};
}

test('show Wi-Fi for wireless and combined links, hide active LAN, show disconnected when neither is active', () => {
    const f = fixture();
    for (const [wifi, wired, visible, wireless] of [
        [false, false, true, false], [false, true, false, false],
        [true, false, true, true], [true, true, true, true],
        [false, true, false, false], [false, false, true, false],
    ]) {
        f.wifi.state = wifi ? 100 : 30;
        f.wired.state = wired ? 100 : 30;
        f.client.emit('notify::active-connections');
        assert.equal(f.network._primaryIndicator.visible, visible);
        assert.equal(f.network._primaryIndicatorBinding.source, wireless ? f.wireless : null);
        assert.equal(f.network._primaryIndicator.icon_name,
            wireless ? f.wireless.icon_name : 'network-offline-symbolic');
    }
    assert.equal(f.vpnIcon.visible, true);
    assert.deepEqual(f.network.quickSettingsItems, [f.wireless]);
    f.controller.destroy();
});

test('profile updates cannot restore the top-bar glyph and cleanup restores native behavior', () => {
    const f = fixture();
    assert.equal(f.powerIcon.visible, false);
    f.powerIcon.visible = true;
    assert.equal(f.powerIcon.visible, false);
    assert.equal(f.powerToggle.checked, true);
    f.wired.state = 100;
    assert.equal(f.network._updateIcon(), 42);
    assert.equal(f.network._primaryIndicator.visible, false);
    f.controller.destroy();
    assert.equal(f.network._updateIcon, f.original);
    assert.equal(f.network._primaryIndicatorBinding.source, 'native');
    assert.equal(f.powerIcon.visible, true);
    for (const object of [f.client, f.wifi, f.wired, f.wireless, f.powerIcon])
        assert.equal(object.handlers.length, 0);
});

test('late NetworkManager startup, signal strength changes, and device removal resync without polling', () => {
    const f = fixture(true);
    f.network._client = f.client;
    f.wifi.state = 100;
    f.network._updateIcon();
    f.wireless.icon_name = 'network-wireless-signal-excellent-symbolic';
    f.wireless.emit('notify::icon-name');
    assert.equal(f.network._primaryIndicator.icon_name, f.wireless.icon_name);
    f.client.devices = [f.wired];
    f.client.emit('device-removed');
    assert.equal(f.wifi.handlers.length, 0);
    assert.equal(f.network._primaryIndicator.icon_name, 'network-offline-symbolic');
    f.controller.destroy();
});
