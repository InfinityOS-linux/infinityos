// Parse both variants with the GTK version that renders the desktop menus.
import Gtk from 'gi://Gtk?version=4.0';
import GLib from 'gi://GLib';

Gtk.init();
for (const scheme of [Gtk.InterfaceColorScheme.DARK, Gtk.InterfaceColorScheme.LIGHT]) {
    const css = new Gtk.CssProvider({prefers_color_scheme: scheme});
    const errors = [];
    css.connect('parsing-error', (_provider, _section, error) => {
        if (error.domain === GLib.quark_from_string('gtk-css-parser-error-quark'))
            errors.push(error.message);
    });
    css.load_from_path(ARGV[0]);
    if (errors.length || !css.to_string().includes('backdrop-filter: blur(28px)'))
        throw new Error(`Desktop menu blur failed to load: ${errors.join(', ')}`);
}
