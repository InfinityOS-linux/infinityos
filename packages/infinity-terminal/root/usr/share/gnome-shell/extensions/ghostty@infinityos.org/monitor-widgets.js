import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Stopwatch, Countdown, networkTotals, networkRate} from './monitor-model.mjs';

const pl = GLib.get_language_names()[0].startsWith('pl');
const tr = (en, polish) => pl ? polish : en;
export const widgetChoices = [
    {id: 'widget:stopwatch', label: tr('Stopwatch', 'Stoper'), icon: 'preferences-system-time-symbolic'},
    {id: 'widget:timer', label: tr('Timer', 'Minutnik'), icon: 'alarm-symbolic'},
    {id: 'widget:pomodoro', label: 'Pomodoro', icon: 'appointment-soon-symbolic'},
    {id: 'widget:network', label: tr('Network', 'Sieć'), icon: 'network-transmit-receive-symbolic'},
    {id: 'widget:battery', label: tr('Battery', 'Bateria'), icon: 'battery-symbolic'},
    {id: 'widget:clock', label: tr('World clock', 'Zegar strefowy'), icon: 'preferences-system-time-symbolic'},
    {id: 'widget:weather', label: tr('Weather', 'Pogoda'), icon: 'weather-few-clouds-symbolic'},
];

export class MonitorWidgets {
    constructor(changed, settings) {
        this.settings = settings;
        this._alive = true;
        this._cancel = new Gio.Cancellable();
        this._alarms = new Map();
        this._selected = new Set();
        this.timers = {'widget:timer': new Countdown(() => GLib.get_monotonic_time() / 1000000),
            'widget:pomodoro': new Countdown(() => GLib.get_monotonic_time() / 1000000, true)};
        this.stopwatch = new Stopwatch(() => GLib.get_monotonic_time() / 1000000);
        // Reuse Shell's client: it owns location permissions, Weather settings and network requests.
        this.weather = Main.panel.statusArea.dateMenu?._weatherItem?._weatherClient ?? null;
        this._changed = changed;
        this._weatherId = this.weather?.connect('changed', changed);
        this._lastWeatherUpdate = -Infinity;
    }

    read(id) {
        const choice = widgetChoices.find(item => item.id === id);
        if (id === 'widget:stopwatch')
            return {...choice, text: this.stopwatch.text,
                detail: this.stopwatch.running ? tr('Running', 'Działa') : tr('Paused', 'Pauza')};
        if (this.timers[id]) {
            const timer = this.timers[id];
            return {...choice, text: timer.text, detail: !timer.running ? tr('Paused', 'Pauza') :
                id === 'widget:pomodoro' ? (timer.phase === 'work' ? tr('Focus', 'Praca') : tr('Break', 'Przerwa')) : tr('Running', 'Działa')};
        }
        if (id === 'widget:clock') {
            const zone = this.settings.get_string('monitor-timezone');
            const timezone = GLib.TimeZone.new_identifier(zone);
            return {...choice, text: timezone ? GLib.DateTime.new_now(timezone).format('%H:%M:%S') : '—', detail: zone};
        }
        if (id === 'widget:network') {
            const rate = value => value >= 1048576 ? `${(value / 1048576).toFixed(1)} M` : `${(value / 1024).toFixed(0)} K`;
            return {...choice, text: this._rate ? `↓${rate(this._rate.rx)} ↑${rate(this._rate.tx)}` : '—', detail: 'B/s'};
        }
        if (id === 'widget:battery') {
            const property = name => this._battery?.get_cached_property(name)?.deepUnpack();
            const present = property('IsPresent');
            const charging = property('State') === 1;
            const seconds = property(charging ? 'TimeToFull' : 'TimeToEmpty') ?? 0;
            return {...choice, text: present ? `${Math.round(property('Percentage'))}%` : tr('No battery', 'Brak baterii'),
                icon: property('IconName') || choice.icon,
                detail: seconds > 0 ? `${Math.floor(seconds / 3600)}h ${Math.floor(seconds / 60) % 60}m` :
                    present ? (charging ? tr('Charging', 'Ładowanie') : tr('Time unavailable', 'Brak szacunku')) : tr('Unavailable', 'Niedostępna')};
        }
        const client = this.weather;
        let text = tr('Unavailable', 'Niedostępna');
        let detail = tr('GNOME Weather not installed', 'Brak GNOME Weather');
        let icon = choice.icon;
        if (client?.available) {
            detail = tr('Choose a location in Weather', 'Wybierz lokalizację w Pogodzie');
            if (client.hasLocation) {
                detail = client.info.get_location()?.get_name() ?? choice.label;
                if (client.info.is_valid()) {
                    text = client.info.get_temp();
                    icon = client.info.get_symbolic_icon_name() || icon;
                } else text = client.loading ? tr('Loading…', 'Wczytywanie…') : tr('No data', 'Brak danych');
            }
        }
        return {...choice, text, detail, icon};
    }

    refreshWeather() {
        const now = GLib.get_monotonic_time() / 1000000;
        if (this.weather?.available && now - this._lastWeatherUpdate >= 600) {
            this._lastWeatherUpdate = now;
            this.weather.update();
        }
    }

    select(ids) {
        this._selected = new Set(ids);
        if (!this._selected.has('widget:network')) this.pauseNetwork();
        for (const id of Object.keys(this.timers)) {
            if (!this._selected.has(id)) { this.timers[id].reset(); this._schedule(id); }
        }
        if (this._selected.has('widget:battery') && !this._batteryRequested) {
            this._batteryRequested = true;
            Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, null,
                'org.freedesktop.UPower', '/org/freedesktop/UPower/devices/DisplayDevice',
                'org.freedesktop.UPower.Device', this._cancel, (_source, result) => {
                    if (!this._alive) return;
                    try {
                        this._battery = Gio.DBusProxy.new_for_bus_finish(result);
                        this._batteryId = this._battery.connect('g-properties-changed', this._changed);
                        this._changed();
                    } catch (_) { /* Desktops and systems without UPower remain usable. */ }
                });
        }
    }

    pauseNetwork() {
        this._networkGeneration = (this._networkGeneration ?? 0) + 1;
        this._networkTotals = null;
        this._networkTime = undefined;
        this._rate = null;
    }

    refreshNetwork() {
        if (!this._selected.has('widget:network') || this._networkPending) return;
        const now = GLib.get_monotonic_time() / 1000000;
        if (this._networkTime !== undefined && now - this._networkTime < 1) return;
        this._networkPending = true;
        const generation = this._networkGeneration ?? 0;
        Gio.File.new_for_path('/proc/net/dev').load_contents_async(this._cancel, (file, result) => {
            this._networkPending = false;
            if (!this._alive || generation !== (this._networkGeneration ?? 0)) return;
            try {
                const [ok, bytes] = file.load_contents_finish(result);
                if (!ok) return;
                const totals = networkTotals(new TextDecoder().decode(bytes));
                this._rate = networkRate(this._networkTotals, totals, now - (this._networkTime ?? now));
                this._networkTotals = totals; this._networkTime = now;
                this._changed();
            } catch (_) { this._rate = null; }
        });
    }

    toggleTimer(id) { this.timers[id].toggle(); this._schedule(id); this._changed(); }
    resetTimer(id, minutes) { this.timers[id].reset(minutes); this._schedule(id); this._changed(); }

    _schedule(id) {
        if (this._alarms.has(id)) GLib.Source.remove(this._alarms.get(id));
        this._alarms.delete(id);
        const timer = this.timers[id];
        if (!timer.running) return;
        this._alarms.set(id, GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, Math.max(1, Math.ceil(timer.seconds)), () => {
            this._alarms.delete(id);
            const phase = timer.finish();
            if (phase) Main.notify(id === 'widget:pomodoro' ? 'Pomodoro' : tr('Timer', 'Minutnik'),
                phase === 'done' ? tr('Time is up.', 'Czas minął.') : phase === 'break' ? tr('Time for a break.', 'Czas na przerwę.') : tr('Time to focus.', 'Czas na pracę.'));
            this._changed(); this._schedule(id);
            return GLib.SOURCE_REMOVE;
        }));
    }

    destroy() {
        this._alive = false;
        this._cancel.cancel();
        for (const alarm of this._alarms.values()) GLib.Source.remove(alarm);
        if (this._batteryId) this._battery.disconnect(this._batteryId);
        if (this._weatherId) this.weather.disconnect(this._weatherId);
    }
}
