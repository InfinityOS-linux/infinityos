import Adw from 'gi://Adw';
import Gdk from 'gi://Gdk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import Pango from 'gi://Pango';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {defaults, readPreferences, writePreferences} from './preferences-config.mjs';

const pl = GLib.get_language_names()[0].startsWith('pl');
const tr = (en, polish) => pl ? polish : en;

export default class TerminalPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        window.set_default_size(620, 680);
        const directory = GLib.build_filenamev([GLib.get_user_config_dir(), 'infinityos']);
        const file = Gio.File.new_for_path(`${directory}/terminal.conf`);
        let values = {...defaults};
        try {
            const [ok, contents] = file.load_contents(null);
            if (ok) {
                values = readPreferences(new TextDecoder().decode(contents));
                writePreferences(values);
            }
        } catch (error) {
            values = {...defaults};
            if (!error.matches?.(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND))
                window.add_toast(new Adw.Toast({title: tr('Could not read saved settings.', 'Nie udało się odczytać zapisanych ustawień.')}));
        }
        const page = new Adw.PreferencesPage({title: 'InfinityTerminal', icon_name: 'utilities-terminal-symbolic'});
        const group = new Adw.PreferencesGroup({title: tr('Appearance', 'Wygląd'),
            description: tr('Apply changes without closing your terminal sessions.', 'Zastosuj zmiany bez zamykania sesji terminala.')});
        page.add(group);
        window.add(page);
        const font = new Gtk.FontDialogButton({dialog: new Gtk.FontDialog(),
            font_desc: Pango.FontDescription.from_string(values['font-family']), valign: Gtk.Align.CENTER});
        const fontRow = new Adw.ActionRow({title: tr('Font', 'Czcionka')});
        fontRow.add_suffix(font); group.add(fontRow);
        const spin = (key, title, min, max, step, digits = 0) => {
            const row = new Adw.SpinRow({title, digits, adjustment: new Gtk.Adjustment({
                lower: min, upper: max, step_increment: step, page_increment: step * 5,
                value: values[key]})});
            group.add(row);
            return row;
        };
        const size = spin('font-size', tr('Font size', 'Rozmiar czcionki'), 6, 48, 1);
        const opacity = spin('background-opacity', tr('Background opacity', 'Krycie tła'), 0.2, 1, 0.05, 2);
        const padding = spin('window-padding-x', tr('Inner padding', 'Margines wewnętrzny'), 0, 40, 1);
        const custom = new Adw.SwitchRow({title: tr('Custom colors', 'Własne kolory'),
            subtitle: tr('Off: follow the system light/dark theme.', 'Wyłączone: używaj jasnego lub ciemnego motywu systemu.'),
            active: !!(values.background || values.foreground)});
        group.add(custom);
        const color = (key, title, fallback) => {
            const rgba = new Gdk.RGBA(); rgba.parse(values[key] || fallback);
            const button = new Gtk.ColorDialogButton({dialog: new Gtk.ColorDialog({with_alpha: false}),
                rgba, valign: Gtk.Align.CENTER});
            const row = new Adw.ActionRow({title, sensitive: custom.active});
            row.add_suffix(button); group.add(row);
            custom.connect('notify::active', () => { row.sensitive = custom.active; });
            return button;
        };
        const background = color('background', tr('Background', 'Tło'), '#0b0912');
        const foreground = color('foreground', tr('Text color', 'Kolor tekstu'), '#f4f0fa');
        const cursor = new Adw.ComboRow({title: tr('Cursor shape', 'Kształt kursora'),
            model: Gtk.StringList.new([tr('Block', 'Blok'), tr('Bar', 'Kreska'), tr('Underline', 'Podkreślenie')]),
            selected: ['block', 'bar', 'underline'].indexOf(values['cursor-style'])});
        group.add(cursor);
        const blink = new Adw.SwitchRow({title: tr('Blinking cursor', 'Migający kursor'), active: values['cursor-style-blink']});
        const copy = new Adw.SwitchRow({title: tr('Copy on selection', 'Kopiuj przy zaznaczaniu'), active: values['copy-on-select']});
        group.add(blink); group.add(copy);
        const behavior = new Adw.PreferencesGroup({title: tr('Window and shortcuts', 'Okno i skróty')});
        page.add(behavior);
        const settings = this.getSettings();
        const monitor = new Adw.SwitchRow({title: tr('Open on current monitor', 'Otwieraj na bieżącym monitorze'),
            subtitle: tr('Off: primary monitor. On: monitor containing the pointer.',
                'Wyłączone: monitor główny. Włączone: monitor ze wskaźnikiem.')});
        settings.bind('use-current-monitor', monitor, 'active', Gio.SettingsBindFlags.DEFAULT);
        behavior.add(monitor);
        behavior.add(new Adw.ActionRow({title: tr('Show or hide terminal', 'Pokaż lub ukryj terminal'),
            subtitle: settings.get_strv('infinity-terminal-toggle').join(', ')}));
        const hardware = new Adw.PreferencesGroup({title: tr('Hardware monitors', 'Wskaźniki sprzętowe'),
            description: tr('Right-click the strip to choose sensors, GPUs, disks and their order. Missing readings show N/A.',
                'Kliknij pasek prawym przyciskiem, aby wybrać czujniki, GPU, dyski i kolejność. Brak odczytu: N/A.')});
        page.add(hardware);
        const enabled = new Adw.SwitchRow({title: tr('Show hardware strip', 'Pokaż pasek parametrów')});
        settings.bind('monitor-enabled', enabled, 'active', Gio.SettingsBindFlags.DEFAULT);
        hardware.add(enabled);
        const tdp = new Adw.SpinRow({title: tr('CPU TDP (W), manual', 'TDP CPU (W), ręcznie'),
            subtitle: tr('From the CPU specification. 0 = unknown. Not live power consumption or a power limit.',
                'Ze specyfikacji CPU. 0 = nieznane. To nie jest bieżący pobór ani limit mocy.'),
            adjustment: new Gtk.Adjustment({lower: 0, upper: 2000, step_increment: 1, page_increment: 5})});
        settings.bind('monitor-cpu-tdp', tdp, 'value', Gio.SettingsBindFlags.DEFAULT);
        hardware.add(tdp);
        const timezone = new Adw.EntryRow({title: tr('Widget time zone (IANA)', 'Strefa widgetu (IANA)'),
            text: settings.get_string('monitor-timezone'), show_apply_button: true});
        timezone.connect('apply', () => {
            const value = timezone.text.trim();
            if (value && GLib.TimeZone.new_identifier(value)) {
                settings.set_string('monitor-timezone', value);
                timezone.remove_css_class('error');
            } else timezone.add_css_class('error');
        });
        hardware.add(timezone);
        const actions = new Adw.PreferencesGroup(); page.add(actions);
        const apply = new Gtk.Button({label: tr('Apply', 'Zastosuj'), css_classes: ['suggested-action'], halign: Gtk.Align.END});
        actions.add(apply);
        const reset = new Gtk.Button({label: tr('Restore appearance', 'Przywróć wygląd')});
        reset.connect('clicked', () => {
            font.set_font_desc(Pango.FontDescription.from_string(defaults['font-family']));
            size.value = defaults['font-size']; opacity.value = defaults['background-opacity'];
            padding.value = defaults['window-padding-x']; custom.active = false;
            cursor.selected = ['block', 'bar', 'underline'].indexOf(defaults['cursor-style']);
            blink.active = defaults['cursor-style-blink']; copy.active = defaults['copy-on-select'];
            apply.emit('clicked');
        });
        actions.add(reset);
        behavior.add(new Adw.ActionRow({title: tr('Gestures and controls', 'Gesty i sterowanie'),
            subtitle: tr('Three fingers down: open; up: hide. Pin keeps the window visible. Drag the bottom edge to resize; double-click it for full height. Use the pane controls to split the terminal.',
                'Trzy palce w dół: otwórz; w górę: ukryj. Przypięcie utrzymuje widoczność okna. Przeciągnij dolną krawędź, aby zmienić wysokość; dwuklik ustawia pełną wysokość. Użyj przycisków panelu, aby podzielić terminal.')}));
        const hex = button => {
            const rgba = button.get_rgba();
            return '#' + [rgba.red, rgba.green, rgba.blue].map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');
        };
        apply.connect('clicked', () => {
            try {
                // Re-read so applying appearance never erases concurrent manual edits.
                let previous = '';
                let etag = null;
                try {
                    const [ok, contents, currentEtag] = file.load_contents(null);
                    if (ok) {
                        previous = new TextDecoder().decode(contents);
                        etag = currentEtag;
                    }
                } catch (error) {
                    if (!error.matches?.(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND))
                        throw error;
                }
                const content = writePreferences({
                    'font-family': font.get_font_desc().get_family(), 'font-size': size.value,
                    'background-opacity': opacity.value, 'window-padding-x': padding.value,
                    background: custom.active ? hex(background) : '', foreground: custom.active ? hex(foreground) : '',
                    'cursor-style': ['block', 'bar', 'underline'][cursor.selected],
                    'cursor-style-blink': blink.active, 'copy-on-select': copy.active,
                }, previous);
                GLib.mkdir_with_parents(directory, 0o700);
                file.replace_contents(new TextEncoder().encode(content), etag, false, Gio.FileCreateFlags.PRIVATE, null);
                const process = Gio.Subprocess.new(['gapplication', 'action', 'com.infinityos.GhosTTY', 'reload-config'], Gio.SubprocessFlags.NONE);
                process.wait_check_async(null, (proc, result) => {
                    let message = tr('Settings applied.', 'Ustawienia zastosowane.');
                    try { proc.wait_check_finish(result); } catch (_error) {
                        message = tr('Saved. Reopen the terminal to apply.', 'Zapisano. Otwórz ponownie terminal, aby zastosować.');
                    }
                    window.add_toast(new Adw.Toast({title: message}));
                });
            } catch (error) {
                window.add_toast(new Adw.Toast({title: tr('Could not apply settings: ', 'Nie udało się zastosować ustawień: ') + error.message}));
            }
        });
    }
}
