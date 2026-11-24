// Parse both variants with the GTK version that renders the desktop menus.
import Gdk from 'gi://Gdk?version=4.0';
import Gio from 'gi://Gio';
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

// Map a DING-style popover in the native Shell test. The runner checks its
// Wayland traffic for a nonempty compositor blur request in each color scheme.
if (ARGV[1]) {
    const css = new Gtk.CssProvider({prefers_color_scheme: Gtk.InterfaceColorScheme[ARGV[1]]});
    css.load_from_path(ARGV[0]);
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
    const model = new Gio.Menu();
    model.append('New Folder', 'desktop.new-folder');
    const popup = Gtk.PopoverMenu.new_from_model_full(model, Gtk.PopoverMenuFlags.NESTED);
    popup.add_css_class('desktopmenu');
    const button = new Gtk.MenuButton({popover: popup, label: 'Desktop'});
    const window = new Gtk.Window({child: button, default_width: 480, default_height: 320});
    const waitForFrame = () => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
        resolve();
        return GLib.SOURCE_REMOVE;
    }));
    window.present();
    await waitForFrame();
    button.popup();
    await waitForFrame();
    if (!popup.get_mapped())
        throw new Error('Desktop menu did not open');
    window.destroy();
}
